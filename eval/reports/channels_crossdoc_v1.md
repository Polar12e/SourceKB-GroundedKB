# 跨文档四通路 A/B 评估报告（修正版）

> 日期：2026-11-19  
> 数据集：`eval/datasets/finance_crossdoc_v1.json`（40 题）  
> 标注模型：canonical `gold_evidence` + `acceptable_evidence` + `hard_negatives`  
> 指标：Hit/MRR 用可接受集合；Recall 用 canonical；precision 用可接受集合  
> Corpus：7 份高质文档，1532 页；Top-k：4

## 标注修正

首版只标了 canonical 页，导致“同一事实在多个页面披露”被误判为失败。修正后：

- 15 题补了 `acceptable_evidence`；
- 9 题补了 `hard_negatives`；
- 代表性重复页：腾讯 p5/p11 盈利、p9/p10 收入、p7/p214 股息；中芯 p11 摘要/p29 成本表/p127 利润表。

## Overall

| 通道 | 构建耗时 | Hit@4 | Recall@4 | MRR | precision@4 | hard_neg |
|---|---:|---:|---:|---:|---:|---:|
| `bm25` | 0.86s | 0.750 | 0.650 | 0.648 | 0.256 | 9 |
| `expanded` | 0.79s | 0.875 | 0.644 | 0.713 | 0.287 | 18 |
| `dense`（LSA） | 14.91s | 0.675 | 0.571 | 0.492 | 0.212 | 8 |
| `hybrid`（w=0.5） | 9.30s | 0.875 | 0.713 | **0.758** | **0.306** | 13 |

## 分 company 的 Hit@4

| 通道 | Midea | 腾讯 | 中芯 HK | 中芯 A |
|---|---:|---:|---:|---:|
| `bm25` | 0.500 | 0.867 | 0.700 | 1.000 |
| `expanded` | 1.000 | 0.867 | 0.700 | 1.000 |
| `dense` | 0.600 | 0.667 | 0.600 | 1.000 |
| `hybrid` | 1.000 | 0.867 | 0.700 | 1.000 |

## 分 split 的 Hit@4

| 通道 | dev (29) | holdout (11) |
|---|---:|---:|
| `bm25` | 0.690 | 0.909 |
| `expanded` | 0.862 | 0.909 |
| `dense` | 0.655 | 0.727 |
| `hybrid` | 0.862 | 0.909 |

## Dense 权重扫描（expanded=1.0）

| dense w | Hit@4 | MRR | 腾讯 Hit@4 | 中芯 A Hit@4 |
|---:|---:|---:|---:|---:|
| 0.00 | 0.875 | 0.713 | 0.867 | 1.000 |
| 0.10 | 0.875 | 0.733 | 0.867 | 1.000 |
| 0.25 | 0.875 | 0.750 | 0.867 | 1.000 |
| 0.50 | 0.875 | 0.758 | 0.867 | 1.000 |
| 0.75 | **0.900** | 0.744 | **0.933** | 1.000 |

## 结论

1. **首版“hybrid 腾讯回退”主要是 Gold 标注问题**。补上重复合法页后，hybrid 与 expanded 在腾讯上都是 0.867，没有回退。
2. **hybrid 与 expanded 的 Hit@4 持平（0.875）**，但 MRR（0.758 vs 0.713）和 precision（0.306 vs 0.287）更高。
3. `dense` 本身仍弱（0.675），LSA 只能证明通路可用，不足以证明默认收益。
4. `w=0.75` 把 Hit@4 提到 **0.900**，相对 expanded **+2.5pp**，低于 3pp 门槛；且 MRR 略降，故**不改默认**。
5. `expanded` 对 Midea/中芯 A 的收益来自 profile 参数，不是“多通道”。

## 决策

- **保持 `default_channel=expanded`**。
- hybrid 继续作为候选；下一步应先扩大/复核 40 题标注，再考虑 w=0.75 或 dense gating。
- 不调 RRF 权重、不改默认，直到 holdout 复核通过。

## 复现边界

- 只使用 7 份高质文档，Xiaomi 3 份未纳入；
- `acceptable_evidence` 与 `hard_negatives` 是人工初筛，仍需复核；
- LSA 结果不能外推到真实 embedding。
