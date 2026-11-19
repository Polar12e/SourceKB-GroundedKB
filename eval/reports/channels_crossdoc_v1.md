# 跨文档四通路 A/B 评估报告

> 日期：2026-11-19  
> 数据集：`eval/datasets/finance_crossdoc_v1.json`（40 题，29 dev / 11 holdout）  
> Corpus：7 份高质文档，1532 页（不含 Xiaomi 3 份）  
> Top-k：4  
> 过滤：每题带 company / year / doc_type，filter correctness 全部 OK

## 命令

```bash
make eval-crossdoc
# 等价于：
python -m eval.run_crossdoc --cases eval/datasets/finance_crossdoc_v1.json \
  --corpus data/private/corpus/pages.jsonl
```

## Overall

| 通道 | 构建耗时 | Hit@4 | Recall@4 | MRR | precision@4 |
|---|---:|---:|---:|---:|---:|
| `bm25` | 0.81s | 0.650 | 0.650 | 0.490 | 0.175 |
| `expanded` | 0.80s | 0.650 | 0.644 | 0.512 | 0.200 |
| `dense`（LSA） | 13.53s | 0.600 | 0.571 | 0.435 | 0.150 |
| `hybrid` | 13.36s | **0.725** | **0.713** | **0.560** | **0.212** |

## 分 company 的 Hit@4

| 通道 | Midea 000333.SZ | 腾讯 00700.HK | 中芯 HK 00981.HK | 中芯 A 688981.SH |
|---|---:|---:|---:|---:|
| `bm25` | 0.500 | 0.667 | **0.700** | **0.800** |
| `expanded` | **1.000** | **0.667** | 0.500 | 0.200 |
| `dense` | 0.600 | 0.467 | 0.600 | **1.000** |
| `hybrid` | **1.000** | 0.533 | **0.700** | **0.800** |

## 分 split 的 Hit@4

| 通道 | dev (29) | holdout (11) |
|---|---:|---:|
| `bm25` | 0.621 | 0.727 |
| `expanded` | 0.690 | 0.545 |
| `dense` | 0.586 | 0.636 |
| `hybrid` | **0.724** | **0.727** |

## 结论

**没有任何通道满足“整体提升且各 company 不下降 >2pp”的默认切换门槛。**

1. `hybrid` 总体最高（+7.5pp vs expanded），但腾讯从 0.667 降到 0.533（-13.3pp），不能直接默认。
2. `expanded` 对 Midea 有效（1.000），但中芯 A 股只有 0.200；相比 bm25 下降 60pp，说明当前 `builtin` 参数对 A 股文档不通用。
3. `dense` 总体 0.600，LSA 仍弱；中芯 A 股 1.000 是局部现象，不足以作为默认依据。
4. `bm25` 最均衡（三家 0.667/0.700/0.800），但 Midea 只有 0.500，说明 profile 参数确实有价值，只是需要按文档/company 适配。
5. 所有通路的 filters 都正确，问题不在权限过滤。

## 决策建议

- **暂不修改 `default_channel`**，保持 `expanded`，因为当前没有通道通过门槛。
- 下一步应先做 **profile 分片/参数化**：
  - 对 A 股（688981.SH）关闭或调整报表页加分/内置扩展；
  - 对腾讯保持 `builtin`；
  - 再测 hybrid 权重 0.25 / 0.5 / 0.75。
- 40 题是草案，仍需人工复核 Gold Evidence；尤其 SMIC A 股 5 题样本太小，不能据此得出最终结论。

## 复现边界

- 只使用 7 份高质文档；Xiaomi 3 份未纳入。
- 题目和页码已提交，PDF/全文不提交。
- 本结果不等价于生产环境：LSA 不是预训练 embedding，query 分布也有限。
