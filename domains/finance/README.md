# domains/finance（待建）

第一个 vertical：金融年报/公告。

计划从旧项目迁移：

- `FinancialFact` / `MetricResult`
- CSV store
- 三个财务指标计算
- 财务同义词表
- 财务事实 CSV
- 年报 corpus
- 32 道种子题

原则：

- 财务数字继续用 `Decimal` + 确定性工具；
- PDF/原文用于解释和证据；
- 不在 core 里写财务规则。
