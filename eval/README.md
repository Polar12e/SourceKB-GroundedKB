# eval（进行中）

Retrieval benchmark 与评测入口。

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

默认对比 `bm25` / `expanded` / `dense` / `hybrid`，报告见 [reports/channels_midea_v1.md](reports/channels_midea_v1.md)。当前结论：默认 `expanded`；LSA dense 不优于纯 BM25，hybrid 暂不默认。

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
