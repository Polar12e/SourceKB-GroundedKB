# 四通路检索评估报告（Midea v1）

> 日期：2026-11-19  
> 数据集：`eval/datasets/finance_midea_v1.json`（10 题）  
> Corpus：`data/private/corpus/midea-2024.jsonl`（452 页）  
> 配置：`config/retrieval.yaml`  
> Top-k：4

## 命令

```bash
make eval-ab
# 等价于：
python -m eval.run_ab --channel bm25,expanded,dense,hybrid
```

## 结果

| 通道 | 构建耗时 | Hit@4 | Recall@4 | MRR | precision@4 |
|---|---:|---:|---:|---:|---:|
| `bm25` | 0.21s | 0.600 | 0.550 | 0.475 | 0.200 |
| `expanded` | **0.19s** | **1.000** | **0.975** | **1.000** | **0.400** |
| `dense`（LSA） | 4.83s | 0.600 | 0.600 | 0.533 | 0.200 |
| `hybrid`（expanded + dense） | 4.16s | 1.000 | 0.950 | 0.883 | 0.375 |

## 解读

1. **默认保持 `expanded`**：它同时取得最高 Hit@4/Recall@4/MRR，构建最快。
2. **纯 BM25 只有 0.600**：说明这批财务题需要 profile 参数（内置扩展/报表页加分），不是“BM25 本身不行”。
3. **LSA dense 仍弱**：0.600，和纯 BM25 同档；旧项目结论一致——离线 LSA 不能替代预训练 embedding。
4. **hybrid 没有超过 expanded**：RRF 把 dense 的低质量候选带进来，Recall 略降、MRR 下降；在接入真实 embedding 前不应默认。
5. **参数价值可测**：同一批题，仅因 `profiles.finance` 参数不同，Hit@4 从 0.600 到 1.000。

## 决策

- `config/retrieval.yaml` 的 `default_channel` 保持 `expanded`。
- `dense` / `hybrid` 保留为可切换通路，等真实 embedding provider 接入后重新评估。
- 该报告只覆盖 Midea 10 题；跨文档题（腾讯/中芯/小米）尚需单独评估。

## 复现边界

- PDF/全文不提交；本报告只引用指标，不引用原文。
- LSA 的结果受语料和维度影响，不能外推到 API embedding。
- `expanded` 当前 `mode=builtin`；`auto/lexicon` 的 A/B 尚未跑。
