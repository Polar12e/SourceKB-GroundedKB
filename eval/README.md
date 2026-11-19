# eval（进行中）

Retrieval benchmark 与评测入口。


## 合法答案页判定

- **canonical `gold_evidence`**：首选证据页，必须包含完整事实（主体、期间、数值/单位/结论），用于 Recall。
- **`acceptable_evidence`**：同一事实在其他页面的合法披露（摘要/正文/报表重复），用于 Hit/MRR/precision。
- **`hard_negatives`**：与 query 高相似但不含答案，或期间/主体不匹配的页面；不参与命中，但用于检查引用是否被噪声页污染。

原则：**相似度 ≠ 合法性**。术语表、董事会报告、审计报告等即使词重叠很高，也不能标为答案页。

## 当前数据集

| 文件 | 内容 |
|---|---|
| `datasets/finance_midea_v1.json` | 10 条 Midea 2024 EvalCase（q01–q10），page/line Gold Evidence |

## 运行

```bash
make py-test                 # 含 eval metrics 测试
source .venv/bin/activate
python -m eval.run_retrieval
```

默认使用 `data/private/corpus/midea-2024.jsonl`（与旧项目 baseline 同 corpus），输出：

- `eval-results/retrieval_midea_v1.md`
- `eval-results/retrieval_midea_v1.json`

这些输出在 `.gitignore` 中，不提交。

## 四通路 A/B

```bash
make eval-ab
```

默认对比 `bm25` / `expanded` / `dense` / `hybrid`，Midea 报告见 [reports/channels_midea_v1.md](reports/channels_midea_v1.md)。

## 跨文档 A/B

```bash
make eval-crossdoc
```

40 题、7 份高质文档、按 company/split 分组；报告见 [reports/channels_crossdoc_v1.md](reports/channels_crossdoc_v1.md)。当前没有通道通过默认切换门槛，默认保持 `expanded`。

## 指标

- Hit@4：top-4 是否命中任一 gold page
- Recall@4：gold pages 被 top-4 覆盖的比例
- MRR：第一个 gold page 的倒数排名
- precision@4：top-4 中 gold page 的比例

## Baseline（2026-11-19）

`finance_midea_v1` / Midea corpus：

| 指标 | 旧项目 `bm25` | 新服务（finance profile） |
|---|---:|---:|
| Hit@4 | 1.000 | **1.000** |
| Recall@4 | 0.975 | **0.975** |
| MRR | 1.000 | **1.000** |

新服务与旧 baseline 一致；输出在 `eval-results/`（不提交）。

## 后续

- 补腾讯/中芯/小米的跨文档题（M1 10 文档）；
- 对照旧项目 baseline 记录；
- 接 citation/faithfulness/abstention。
