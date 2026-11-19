# 策略评估：架构/检索/答案/拒答/评测改进建议

> 评估对象：外部提交的《评估策略改进》建议书（下称"建议书"）
> 评估方式：逐条对照 `main@c396d24` 代码 + 本机语料实测（2201 页 / 6269 chunk）；§3/§4 数字为 P0 实施前基线，实施状态见上
> 基线：`pytest` 84 passed；`go test ./...` 全绿
> 结论：**方向正确、优先级错位、诊断不全**。采信约 70%，需重排 P0 顺序并补 5 个盲区。
>
> **实施状态（2026-11-19 17:45）**：P0.1 证据级评测、P0.2 chunk 级候选/融合、P0.5 anchor 引用已落地；P0.3 采用尺度无关 prior（α=0.3）；P0.4 有 verbatim/unverified 基线，数值/拒答阈值仍未完成。当前 expanded 页面/chunk Hit@4 均 0.875，hybrid 0.850；默认仍为 expanded。

---

## 1. 结论摘要

| 建议书判断 | 核验结果 | 处置 |
|---|---|---|
| 启动时构建索引（`app.py:53`） | ✅ 属实，且 `app = create_app()` 在 import 期执行 | 保留，P1 |
| ingest 应负责状态/解析/chunk/发布 | ✅ 属实（`services/ingest/main.go` 15 行空壳） | 保留，P1 |
| Postgres/Redis 暂不必引入 | ✅ 属实，且 compose 已先引入（见 §4.1） | 保留，立即 |
| 页面级 ranking 丢失同页多 chunk | ✅ 属实，**且比建议书更严重**（三层折叠，见 §2.2） | 升级为 P0 |
| `answer.go:157` 取第一条结果 | ✅ 属实，**且比建议书更严重**（答案带行号前缀，见 §2.3） | 升级为 P0 |
| 拒答仅由"无结果"触发 | ✅ 属实（`answer.go:147`） | 保留，P0 |
| RRF 只做候选融合 | ⚠️ 方向对，但融合不在服务路径上（默认 `expanded`） | 降级为 P1 |
| BM25+finance profile 是最有价值资产 | ⚠️ 部分成立，其收益含调参假象（见 §3.1） | 修正认知 |
| 增加 query router 为 P0 | ❌ 数据不支持（38/40 是 lookup，见 §3.2） | 降为 P2 |
| Dense 承担召回 | ⚠️ 真实 embedding 未接入前缺乏依据 | 保留为可切换 |
| 答案级评测 | ✅ 属实且**比建议书更急**（现评测掩盖了融合收益） | 升为 P0 第一位 |

---

## 2. 诊断核实（建议书对的部分）

### 2.1 索引生命周期确实没有版本概念

`workers/retrieval/app.py:53-64`：启动即 `load_pages_jsonl` + `build_channel`，模块级
`app = create_app()`（`app.py:100`）使构建发生在 import 期。无 index id、无指纹、无原子切换、
无失败保留旧版本。`/healthz` 不反映索引可用性。

补充两点建议书未提：

- 当前规模下构建成本并不高（expanded 0.79s；LSA dense 14.9s；hybrid 9.3s），
  所以 P1 的动机不是"启动慢"，而是**ingest 无处落地**与**重建即不可用**；
- `chunk_id = "{doc}:p{page}:c{index}"`（`chunking.py:83-86`）中的 `index` 依赖
  `size/overlap`，因此 index version 必须包含 **chunker 参数 + 语料 hash + embedding 模型 + config hash**，
  只写"生成不可变版本"不足以支撑原子切换。

### 2.2 页面折叠发生在三层，不是两层

建议书只点了 `index.py` 和 `dense.py`，实际有第三处，且最致命：

| 层 | 位置 | 行为 |
|---|---|---|
| BM25 | `index.py:205-224` | 每页只保留最高分 chunk 作锚点 |
| Dense | `dense.py:117-134` | 同上 |
| **融合** | `fusion.py:70` | `key = (document_id, page)`，再次按页去重 |

`fusion.py:83-84` 还用 `replace()` 覆盖 `channel` 字段，**丢弃了"几个通道同时命中"这一最强 rerank 特征**。
即使把 BM25/Dense 改成 chunk 级，只要融合仍按页聚合，收益立刻被打回。

### 2.3 答案层问题比"取第一条"更严重

`answer.go:157-178` 的 `quote` 直接取 `hit.Text`，而 `hit.Text` 是
`windows.py:57-58` 渲染的 **带行号前缀的窗口**：

```
1: 美的集团股份有限公司
2: 2024年度财务报表附注
4: - 197 -
7: 财政部分别于 2023年和 2024年发布了《企业会计准则解释第 17号》...
```

后果：

1. `/ask` 返回的 `answer` 是带行号的摘录，含页眉页脚噪声，不是可读答案；
2. `citation.quote` 是**渲染文本**而非原文 verbatim 片段——严格 evidence verifier 会判 100% 引用不成立；
3. `SearchHit` 只暴露窗口区间（`index.py:229-236`），**匹配到的 chunk 行区间被丢弃**，
   verifier 无法区分"这段就是证据"与"这段只是相邻上下文"。契约里也没有这个字段（`search-hit.schema.json`）。

### 2.4 拒答与评测

- 拒答：`answer.go:147`（无 hit）、`answer.go:159`（quote 空）两个分支，无阈值、无 margin、无实体校验；
- 评测：`eval/run_retrieval.py:42-66` 全部按 `(document_id, page)` 计分。gold 自带
  `line_start/line_end`（`eval/datasets/*.json` 全部有），但**从未被使用**；
- 因此 `precision@4` 实际上限是 1/4（多数 case 只有 1 个 gold page），跨通道比较意义有限。

### 2.5 拒答与答案的契约

`contracts/schemas/answer.schema.json` 的 `status` 只有 `ok / insufficient_evidence / error`。
建议书要求"校验失败即 insufficient_evidence"，这会把**三种不同失败**压成一个状态：
无证据 / 有证据但与答案矛盾 / 证据存在但未覆盖claim。合并后拒答 precision/recall 无法分别评估。
建议书通篇未提契约，但本仓库是 contract-first（13 个 schema），新增 rerank 分数、evidence set、
verifier 结论都必须改 schema，否则服务会漂移。

---

## 3. 需要修正的判断

### 3.1 "BM25+profile 是最有价值资产"——收益有一部分是调参假象

已发布 40 题数字（`eval-results/crossdoc_ab.md`）：expanded 相对 bm25 的 Hit@4 +0.125，
但 Recall@4 反而 -0.006（0.644 vs 0.650），hard negative 命中 **9 → 18**（翻倍）。

原因之一是 `config/retrieval.yaml:37` 的 `statement_bonus: 18.0`：这是个**平坦加分**，
加在 BM25 分数之后（`index.py:209-212`）。实测该加分只覆盖 **15/2201 页（0.7%）**，
而 BM25 原始 top1 分数区间是 18–68、中位数约 2.3–3.4——18 分相当于"再给一个 top1"。

消融（expanded，chunk 级命中 / dev / holdout / hard_neg）：

| statement_bonus | chunk-hit (all) | dev | holdout | hard_neg hits |
|---|---:|---:|---:|---:|
| **18.0（现状）** | 0.650 | 0.690 | 0.545 | 18 |
| 8.0 | **0.725** | 0.759 | 0.636 | 14 |
| 5.0 | 0.725 | 0.759 | 0.636 | 14 |
| 0（关闭） | 0.675 | 0.690 | 0.636 | 10 |

5–8 之间结果完全一致（同样的页面被加分，只有与非加分页面的相对序改变），说明该参数存在
平台区、调整稳健。结论：**保留 profile（术语扩展有效），但 18.0 是 mistuned，约高出 2–3 倍**。
更稳的做法是把 prior 改成尺度无关形式：`score *= (1 + α·prior)` 或对 top1 原始分归一化后乘以 α≈0.3，
而不是加固定常数——固定常数在语料规模变化后会失效。

### 3.2 "query router 是 P0"——没有标签可路由，也没有指标可验收

`eval/datasets/finance_crossdoc_v1.json` 类型分布：**lookup 38 / explain 2**；
`finance_midea_v1.json`：lookup 8 / explain 2。建议书要求区分 7 类问题，
但现有数据对其中 5 类（同比环比、跨年度、跨公司、会计政策、表格定位）**样本为 0**。

在零样本类型上建 router，只能靠拍脑袋规则，且无法证明它比"统一 profile"更好。
router 应排在**数据集补类型之后**，并被当作规则抽取（从 eval 的 `type` 字段回归）而不是新服务。

### 3.3 "RRF 保留为候选融合"——当前不在服务路径上

`config/retrieval.yaml:1` `default_channel: expanded`，`app.py:55` 只读这一个通道，
`/search` 从不融合。hybrid 只存在于 eval 与手动 A/B。因此"融合后的 rerank"目前无对象可改，
必须先做 §4.2 的候选层与默认通道决策。

### 3.4 "hybrid 与 expanded 持平，默认保持 expanded"——该结论是页面折叠的产物

这是本次实测最重要的发现（见 §4.2）：换成 chunk 级口径后，hybrid **明显优于** expanded
（0.750 vs 0.650）。也就是说，**现在的页面级指标掩盖了融合收益**，并直接导致了
"默认保持 expanded"这个（在该指标下正确、在证据口径下错误的）决策。

### 3.5 优先级排序问题

建议书 P0 有 6 项、把 router 与 rerank 并列最前，但真正的阻塞点是：
候选层还是页面级 → 证据级指标不存在 → 任何 rerank/router 的收益都**测不出来**。
先建指标，再动排序，否则就是在无反馈的情况下调参。修订顺序见 §5。

---

## 4. 建议书的盲区

### 4.1 compose 已经把未来的复杂度付了账

`deploy/compose.yaml` 已定义 postgres + redis，且 `ingest` 服务 `depends_on` 两者健康检查，
而 `services/ingest/main.go` 只有 15 行。建议书说"暂时不必引入"，正确，但应改成行动：
**在 ingest 实现前，从 compose 移除 pg/redis 依赖**，否则 `docker compose up` 会拉起
两个无人使用的有状态服务，并让"ingest 可用"看起来像已完成。

### 4.2 证据粒度缺口（实测）

同一批 40 题、top_k=4，页面级 vs chunk 行级（锚点 chunk 与 gold 行区间有交集）：

| 通道 | 页面级 Hit@4 | chunk 行级 Hit@4 | "页对但 chunk 错" |
|---|---:|---:|---:|
| expanded | 0.850 | 0.650 | 8 例 |
| hybrid | 0.875 | 0.750 | 5 例 |

expanded 有 **20% 的"命中"落在正确页面、错误 chunk 上**（tencent-2025-03、smic-2025-01 等 8 例）。
这意味着：现有 Hit@4=0.875 高估了证据可用性约 10–20 个百分点，且这些 case 正是
"多页/长页表格"——恰是建议书想用 rerank 解决的问题，而 rerank 无法修复"选错 chunk"。

### 4.3 报告不可复现

`eval-results/crossdoc_ab.md` 只记录语料**路径**，不记录 hash；而
`data/private/corpus/pages.jsonl` 今日 17:18 已重新生成、`data/manifests/documents.json`
被改为 `text_quality: ocr`（未提交）。我用当前语料复跑 expanded，页面级 Hit@4 = 0.850，
与报告里的 0.875 已不一致。**没有语料/配置指纹，所有 before/after 比较都不成立**。

### 4.4 "表格整体切分"是 parser 能力，不是 chunker 参数

`workers/parser/extract_pdf.py` 只产出页级纯文本（`extract_pages`），没有表格结构、没有
section path。`chunking.py` 是页内按行切分（`chunk_page_spans`），`Chunk` 无 `section`/`parent_id`
字段（`chunk.schema.json` 也没有）。所以建议书的"表格整体 / 表头 / 指标行 / 父级章节关联"
必须先补 parser 与契约，属于 P1-P2 的解析重做，不能当成配置项。

### 4.5 trace 没有跨服务传播

`answer.go:146` 自造 `trace_${UnixNano}`；gateway 是裸 `httputil.ReverseProxy`，
不注入/不回传 request id；retrieval 无 trace 字段。建议书要求"trace 记录候选、分数、延迟、成本"，
前提是先有 trace 传播链——这比加日志字段更基础。

---

## 5. 修订后的路线图

### P0（先建可见性，再动算法；1–2 周）

1. **评测 v2：证据粒度 + 答案级指标**
   - 行级 hit/recall、nDCG@10、hard-negative contamination、按 type/split/company 分组；
   - 报告写入 `corpus_sha256 + config_sha256 + terms_sha256 + git rev`；
   - 冻结 regression 集（当前 40 题里 29 dev / 11 holdout，holdout 只用于最终比较）。
   - 验收：`make eval` 重跑两次数字一致；报告可凭指纹复现；页面级与 chunk 级指标同时输出。
2. **候选层改为 chunk 级 + 页面/文档分组后置**
   - `SearchHit` 增加 `anchor` 行区间与 `channels`（多通道票数）；融合按 `chunk_id` 聚合，
     `replace()` 不再覆盖 channel 而是累积；
   - 分组成 evidence set 放在响应组装阶段，而非检索阶段。
   - 验收：chunk 级 Hit@4 不低于 0.75，hard-negative 命中不升；多通道票数字段可用于 rerank。
3. **规则型 rerank（在候选层之后）**
   - 特征：实体/年份匹配、指标词、单位、表标题、通道票数、top1-top2 margin；
   - prior 改为尺度无关加分（`α·prior`，α≈0.3），替换固定 18.0。
   - 验收：dev nDCG@10 提升 ≥5%，holdout 不退化，hard-negative 下降。
4. **evidence verifier v0 + 拒答阈值**
   - 校验：quote 是原文 verbatim 子串、citation 的 doc/page/line 存在、答案主体/年份出现在证据里、
     数值与单位可在证据中查出；
   - 状态扩展为 `ok / insufficient_evidence / unverified / conflicting_evidence`（改 `answer.schema.json`）；
   - 阈值：top1 分数、top1-top2 margin、query token coverage、entity/year match。
   - 验收：单独一份 abstention 子集上给出 precision/recall；20 题人工审计 unsupported claim = 0。
5. **移除 `hits[0]` 占位实现**
   - 输出改为"证据集合 + 抽取片段"，quote 用原文行区间而非带行号渲染（渲染放在展示层）。

### P1（可运维性）

6. 离线/异步构建 + 不可变 index version + 原子切换 + 失败保留旧版本；
   `index_id = hash(corpus, chunker_params, embedder, config)`；ingest 负责发布，retrieval 只读 active。
   验收：服务中重建 0 个 5xx；回滚可恢复到旧版本。
7. trace 传播：gateway 生成 `request_id` → agent → retrieval，全链路记录 route/候选/分数/延迟/token。
8. 增量重建（按 document sha256）+ embedding cache 键含 `index_id`。
9. parser/chunker v2：表格抽取、section path、页眉页脚清理、parent-child（含契约变更）。

### P2（需要新数据或新依赖）

10. query router：先补每类 ≥10 题（同比/跨年/跨公司/会计政策/表格定位），再从 eval `type` 回归规则。
11. 真实中文金融 embedding、cross-encoder A/B、按类型动态 top_k。
12. Agent 多跳工具链、Web 证据面板、向量库（>10 万 chunk 或延迟不达标时再评估）。

---

## 6. 明确不做（现在）

- 不加新服务（gateway/agent/retrieval 三进程足够）；
- 不引入向量库、不进 Postgres/Redis（并先从 compose 摘掉 ingest 的 pg/redis 依赖）；
- 不做 LLM 生成（`model-gateway` 仍是空壳，verifier 未建立前生成只会放大幻觉）；
- 不做 cross-encoder（无证据级标签时无法判断收益，且 CPU 上会显著拖慢 p95）；
- 不做 query router（无标签）。

---

## 附录：复现

```bash
# 页面级 vs chunk 行级 Hit@4（本文 §4.2）
.venv/bin/python /tmp/line_eval.py

# statement_bonus 消融（本文 §3.1），含 dev/holdout 拆分
.venv/bin/python /tmp/ablate_split.py
```

两脚本依赖 `data/private/corpus/pages.jsonl` 与 `data/manifests/documents.json`；
若要转正，应并入 `eval/run_retrieval.py` 并写入报告指纹。
