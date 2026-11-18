# eval（待建）

Benchmark runner 与基准数据。

第一版目标：

- 10 文档 / 10 题起步；
- 100 文档 / 100 题为目标；
- 题目字段：`type`、`gold_evidence`、`expected`、`split`；
- 指标：
  - Hit@4 / Recall@4 / MRR
  - citation precision / recall
  - faithfulness
  - abstention recall / false-answer rate
  - tokens / latency / cost

真实 LLM 评测必须显式 `--live`；CI 只跑离线/fake baseline。
