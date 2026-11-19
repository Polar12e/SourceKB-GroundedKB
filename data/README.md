# data

数据目录只提交 **manifest 与说明**，不提交 PDF 或全文。

| 路径 | 是否提交 | 内容 |
|---|---|---|
| `manifests/documents.json` | 是 | 文档元数据、SHA256、页数、文本质量、许可说明 |
| `private/pdfs/` | 否 | 用户提供的原始 PDF |
| `private/corpus/` | 否 | 页级 JSONL（`document_id/page/text`） |
| `private/corpus/ocr/` | 否 | OCR 结果（小米 3 份） |
| `private/ocr-logs/` | 否 | OCR 日志 |

当前 10 份文档：美的 2024、腾讯 2025/2025H1/2026H1、中芯国际 2023/2024/2025、小米 2025/2025H1/2026H1。

> 小米 3 份已完成 OCR（415/127/127 页），并合入 `pages.jsonl`；manifest 标记 `text_quality=ocr`。原低质量输出备份在 `private/corpus/pre-ocr/`，不提交。

## 重建

```bash
# 单份 PDF → 页级 JSONL + manifest
python -m workers.parser.extract_pdf \
  --pdf data/private/pdfs/tencent-2025-ar.pdf \
  --document-id tencent-2025 \
  --out data/private/corpus/tencent-2025.jsonl \
  --manifest data/manifests/documents.json \
  --title "腾讯控股 2025 年年度报告" \
  --company 00700.HK --year 2025 --doc-type annual_report \
  --language zh-Hant --text-quality high

# 字体编码损坏的 PDF → OCR
python -m workers.parser.ocr_pdf \
  --pdf data/private/pdfs/xiaomi-2025-ar.pdf \
  --document-id xiaomi-2025 \
  --out data/private/corpus/ocr/xiaomi-2025.jsonl

# 合并为检索 corpus
python - <<'PY'
import json
from pathlib import Path
corpus = Path('data/private/corpus')
with (corpus / 'pages.jsonl').open('w', encoding='utf-8') as out:
    for path in sorted(corpus.glob('*.jsonl')):
        if path.name == 'pages.jsonl':
            continue
        out.write(path.read_text(encoding='utf-8'))
PY
```

`manifest` 只保存元数据；PDF/全文是否可再分发由提供者确认。
