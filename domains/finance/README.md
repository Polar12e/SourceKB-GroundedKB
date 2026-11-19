# domains/finance（进行中）

第一个 vertical：金融年报/公告。

## 当前配置

- [`terms.json`](terms.json)：**财务名词配置**（同组名词视为同义/近义；权重由 `config/retrieval.yaml` 提供）；
- [`config/retrieval.yaml`](../../config/retrieval.yaml) 的 `profiles.finance`：查询模式、内置扩展、报表页标题/加分等参数；
- 名词表转换逻辑在 [`core/retrieval/terms.py`](../../core/retrieval/terms.py)，profile 在 [`workers/retrieval/profile.py`](../../workers/retrieval/profile.py)，四通路构建在 [`workers/retrieval/pipeline.py`](../../workers/retrieval/pipeline.py)。

`domains/finance` 不再包含检索算法代码，只提供 finance 数据配置。

## 名词表转换逻辑

配置在 `terms.json`：

```json
{
  "groups": [
    ["存货", "库存", "库存商品", "仓库", "备货", "积压", "压货", "卖不掉"],
    ["营业收入", "营收", "收入", "销售额"]
  ]
}
```

查询 `"仓库里压了多少货"` 的转换过程：

1. **归一化**：小写、繁體→简体（`zhconv`）、去掉千分位逗号、合并被换行拆开的中文标签。
2. **切 token**：中文按字符 bigram 切分（`仓库`、`库里`、`里压`…），ASCII/数字单独保留。
3. **名词表匹配**：对每个组，只要 query 的 bigram 与任一成员有交集，就命中该组。
   - 不是子串匹配：`技术上要投多少钱` 不含 `技术投入`，但共享 `技术`，因此命中 `研发投入` 组。
4. **候选扩展**：取该组中未在 query 字面出现的同组名词，去重并保持组顺序。
5. **加权**：候选名词切成 token，以 `0.45` 权重加入查询；原 query token 保持 `1.0`。
   - 扩展只能补召回，不能盖过用户原词；**不替换原 query**。
6. **模式控制**（配置于 `profiles.finance.mode`）：
   - `none`：不扩展；
   - `builtin`：只用 ratio/restatement 内置词（默认）；
   - `lexicon`：总是使用名词表；
   - `auto`：仅当 query coverage < 0.5 时使用名词表，避免精确查询被同义词稀释。

配置校验：每组至少两个名词、禁止单字名词、权重必须在 `(0, 1)` 之间；加载失败会直接报错，不静默降级。

## 计划迁移

- `FinancialFact` / `MetricResult`
- CSV store
- 三个财务指标计算
- 财务事实 CSV
- 年报 corpus（确认许可）
- 32 道种子题

## 原则

- 财务数字继续用 `Decimal` + 确定性工具；
- PDF/原文用于解释和证据；
- 不在 core 里写财务规则。
