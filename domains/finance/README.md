# domains/finance（进行中）

第一个 vertical：金融年报/公告。

已迁移：

- `retrieval.py`：旧 `bm25` 的 ratio/restatement 查询扩展 + 报表页 +18 加分；
- 检索 profile 通过 `BM25Index(profile=FinanceRetrievalProfile())` 注入，不污染 core。

计划从旧项目迁移：

- `FinancialFact` / `MetricResult`
- CSV store
- 三个财务指标计算
- 财务同义词表（完整 `lexicon.py`）
- 财务事实 CSV
- 年报 corpus（确认许可）
- 32 道种子题

原则：

- 财务数字继续用 `Decimal` + 确定性工具；
- PDF/原文用于解释和证据；
- 不在 core 里写财务规则。
