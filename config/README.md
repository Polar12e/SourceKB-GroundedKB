# config（检索参数）

`retrieval.yaml` 是四通路检索的唯一参数入口。逻辑在 `workers/retrieval/`，domain 只提供数据配置（如财务名词表）。

## 参数

| 段 | 参数 | 说明 |
|---|---|---|
| 顶层 | `default_channel` | `bm25` / `expanded` / `dense` / `hybrid` |
| `bm25` | `k1`, `b` | BM25 参数 |
| `window` | `radius`, `max_chars` | hit window 行数与截断 |
| `rrf` | `k`, `depth` | RRF 融合常数与候选深度 |
| `profiles.<name>` | `mode` | `none` / `builtin` / `lexicon` / `auto` |
| | `term_table` | 名词表 JSON 路径 |
| | `expansion_weight` | 扩展词权重（< 1） |
| | `oov_threshold` | `auto` 模式的 coverage 阈值 |
| | `builtin_expansions` | 固定 query 词到扩展词映射 |
| | `statement_titles` | 报表页标题（页面加分） |
| | `notes_markers` | 出现这些词时关闭页面加分 |
| | `statement_bonus` | 报表页加分 |
| `channels.<name>` | `profile` | expanded 使用的 profile |
| | `provider`, `dim` | dense 的 provider/维度 |
| | `channels` | hybrid 的子通道及权重 |

## 切换

- 默认通道：改 `default_channel`；
- 运行时覆盖：`RETRIEVAL_CHANNEL=hybrid`；
- 配置路径覆盖：`RETRIEVAL_CONFIG=/path/to/retrieval.yaml`；
- 财务参数：直接改 `profiles.finance` 或替换 `domains/finance/terms.json`。

BM25 / expanded / dense / hybrid 四种通道的构建逻辑完全通用；`profiles.finance` 只是当前 vertical 的参数。

## 校验

`load_config()` 启动时用 Pydantic 校验：

- `default_channel` 必须存在；
- 未知通道、未知 hybrid 子通道、非法权重/阈值直接报错；
- `expanded.profile` 必须存在；
- `term_table` 路径必须存在；
- `dense.dim` 必须为正；
- 未知顶层字段拒绝。

配置错误在启动阶段失败，不会静默回退。

## 当前评估

```bash
make eval-ab
```

报告：[eval/reports/channels_midea_v1.md](../eval/reports/channels_midea_v1.md)。当前默认保持 `expanded`；LSA dense 与 hybrid 尚未证明优于 expanded。

