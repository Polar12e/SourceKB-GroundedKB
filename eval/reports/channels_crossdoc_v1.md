# 跨文档四通路 A/B 评估报告

> 日期：2026-11-19（OCR 合入后复跑）  
> 数据集：`eval/datasets/finance_crossdoc_v1.json`（40 题）  
> 标注模型：canonical `gold_evidence` + `acceptable_evidence` + `hard_negatives`  
> 指标：Hit/MRR 用可接受集合；Recall 用 canonical；precision 用可接受集合  
> Corpus：7 份高质文档 + 3 份 Xiaomi OCR，共 2201 页；Top-k：4

## 语料变化

Xiaomi 3 份 OCR 已完成并合入 `pages.jsonl`：

- 415 / 127 / 127 页，共 669 页；
- manifest `text_quality=ocr`；
- 原低质量页备份在 `data/private/corpus/pre-ocr/`。

ocr 文本仍有识别噪声（例如金额/单位粘连），但已可用于中文检索。

## Overall

| 通道 | 构建耗时 | Hit@4 | Recall@4 | MRR | precision@4 | hard_neg |
|---|---:|---:|---:|---:|---:|---:|
| `bm25` | 0.95s | 0.750 | 0.650 | 0.594 | 0.256 | 9 |
| `expanded` | 0.92s | 0.850 | 0.644 | 0.696 | 0.281 | 18 |
| `dense`（LSA） | 19.29s | 0.700 | 0.546 | 0.521 | 0.206 | 9 |
| `hybrid`（w=0.5） | 16.69s | **0.875** | **0.750** | **0.754** | **0.306** | 12 |

## 分 company 的 Hit@4

| 通道 | Midea | 腾讯 | 中芯 HK | 中芯 A |
|---|---:|---:|---:|---:|
| `bm25` | 0.500 | 0.867 | 0.700 | 1.000 |
| `expanded` | 1.000 | 0.867 | 0.700 | 0.800 |
| `dense` | 0.600 | 0.733 | 0.600 | 1.000 |
| `hybrid` | 1.000 | 0.867 | 0.700 | 1.000 |

## 分 split 的 Hit@4

| 通道 | dev (29) | holdout (11) |
|---|---:|---:|
| `bm25` | 0.690 | 0.909 |
| `expanded` | 0.862 | 0.818 |
| `dense` | 0.655 | 0.818 |
| `hybrid` | 0.862 | 0.909 |

## Dense 权重扫描（expanded=1.0）

| dense w | Hit@4 | Recall@4 | MRR |
|---:|---:|---:|---:|
| 0.50 | 0.875 | 0.750 | **0.754** |
| 0.75 | 0.875 | **0.775** | 0.735 |

## 结论

1. OCR 合入后 IDF 变化，`expanded` 从 0.875 降到 0.850；`hybrid` 保持 0.875，因此 hybrid 相对 expanded 为 **+2.5pp**。
2. 各 company 没有下降：hybrid 与 expanded 在 Midea/腾讯/中芯 HK 持平，中芯 A 由 0.800 升到 1.000。
3. 但 +2.5pp 仍低于 3pp 默认切换门槛；`hybrid` 暂不设为默认。
4. `w=0.75` 没提高 Hit@4，MRR 反而下降；当前 w=0.5 更稳。
5. `expanded` 的 Midea 收益仍来自 profile；Xiaomi 暂无独立题集，不能据此判断 Xiaomi 检索质量。

## 决策

- **保持 `default_channel=expanded`**。
- 下一步：补 Xiaomi 题集/人工检查 OCR 噪声，再决定 hybrid 或 dense gating。
- 40 题标注仍需人工复核；OCR 文本不做逐字校对。

## 复现边界

- Xiaomi OCR 由 RapidOCR 150 DPI 生成，未做人工逐字校对；
- 只提交 manifest，不提交 OCR 全文；
- LSA 结果不能外推到真实 embedding。
