# 跨文档四通路 A/B 评估报告（chunk 级 / prior 修正后）

> 日期：2026-11-19
> 数据集：`eval/datasets/finance_crossdoc_v1.json`（40 题，29 dev / 11 holdout）
> 标注：canonical `gold_evidence` + `acceptable_evidence` + `hard_negatives`
> 评估：page 与 chunk 双口径；chunk 命中要求 anchor 行区间与证据行区间重叠
> Corpus：2201 页（7 份高质 + 3 份 Xiaomi OCR）；Top-k：4

## 指纹

- `corpus_sha256`: `fab0dd23ba50a7aca0d1627bd69c6874b55c99912f098f1ded0d06fbce3b3b12`
- `config_sha256`: `65bfb83e8842fd1e0e04b0e8fb4212eda5ee92f3cee3e99ec1f865b768ff0744`
- `git_rev`: `6b2588a2d3ff94b2247b6edad616d9dd45dd5143`
- 复现：`make eval-crossdoc`

## Overall

| 通道 | 构建耗时 | page Hit@4 | chunk Hit@4 | page Recall@4 | chunk Recall@4 | page MRR | chunk nDCG@10 | hard_neg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `bm25` | 0.82s | 0.750 | 0.750 | 0.650 | 0.650 | 0.594 | 0.508 | 8 |
| `expanded` | 0.80s | **0.875** | **0.875** | **0.719** | **0.719** | **0.754** | **0.596** | 12 |
| `dense`（LSA） | 11.98s | 0.675 | 0.575 | 0.533 | 0.458 | 0.512 | 0.356 | 9 |
| `hybrid`（w=0.5） | 17.50s | 0.850 | 0.850 | 0.688 | 0.688 | 0.700 | 0.533 | 11 |

## 分 company 的 page Hit@4

| 通道 | Midea | 腾讯 | 中芯 HK | 中芯 A |
|---|---:|---:|---:|---:|
| `bm25` | 0.500 | 0.867 | 0.700 | 1.000 |
| `expanded` | 1.000 | 0.867 | 0.700 | 1.000 |
| `dense` | 0.500 | 0.733 | 0.600 | 1.000 |
| `hybrid` | 1.000 | 0.800 | 0.700 | 1.000 |

## 分 split 的 page Hit@4

| 通道 | dev (29) | holdout (11) |
|---|---:|---:|
| `bm25` | 0.690 | 0.909 |
| `expanded` | 0.862 | 0.909 |
| `dense` | 0.621 | 0.818 |
| `hybrid` | 0.828 | 0.909 |

## 关键变化

1. **候选层改为 chunk 级**：BM25/Dense 不再先按页折叠；`SearchHit` 增加 `anchor`、`anchor_text`、`channels`；Hybrid 按 `chunk_id` 融合并累积通道票数。
2. **页面/文档分组后置**：检索阶段保留同页多 chunk，避免“页对 chunk 错”被隐藏。
3. **`statement_bonus` 改为尺度无关 prior**：`score *= 1 + α`，α=0.3；不再用固定 +18。
4. **旧报告“hybrid 高于 expanded”不能直接复用**：那是页面级 + 旧 prior 的结果；chunk 级 + prior 修正后，expanded 0.875、hybrid 0.850。

## 结论

- 当前默认 `expanded` 仍是综合最优：page/chunk Hit@4 0.875，chunk Recall 0.719，nDCG 0.596，hard_neg 12。
- `hybrid` 没有超过 expanded，且腾讯从 0.867 降到 0.800；不切换默认。
- `dense`（LSA）chunk 口径明显低于 page 口径（0.675 → 0.575），说明其页面命中依赖上下文，不足以支撑证据级默认。
- chunk 口径下 expanded 的 page/chunk Hit 相同，说明正确页的 anchor 基本能落在证据行区间；但 dense 的 0.100 差距说明仍需 verifier。
- 规则 rerank 未启用：当前 expanded 已通过 prior 改善，缺少独立 rerank 标签；应先补答案级/证据级回归，再评估。

## 复现边界

- 指纹由 `eval/fingerprint.py` 生成，包含 corpus/config/terms/cases/git。
- Xiaomi OCR 文本未逐字校对。
- 这是离线 LSA，不代表真实 embedding。
