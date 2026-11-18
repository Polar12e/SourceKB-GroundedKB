# workers/parser（骨架）

PDF → 页级 JSONL + manifest 的解析入口。

## 用法

```bash
python -m workers.parser.extract_pdf \
  --pdf data/private/pdfs/tencent-2025-ar.pdf \
  --document-id tencent-2025 \
  --out data/private/corpus/tencent-2025.jsonl \
  --manifest data/manifests/documents.json \
  --title "腾讯控股 2025 年年度报告" \
  --company 00700.HK \
  --year 2025 \
  --doc-type annual_report \
  --language zh-Hant \
  --text-quality high
```

输出：

- JSONL：`{"document_id", "page", "text"}`，page 从 1 开始；
- manifest：标题、公司、年份、类型、SHA256、页数、字符数、文本质量、许可说明。

## 质量标记

`--text-quality low` 用于字体编码损坏/扫描件。当前小米 3 份 PDF 的中文文本层为乱码，已标记 `low`；需要 OCR 后再重新抽取。

## OCR（可选）

字体编码损坏时使用：

```bash
pip install -r workers/parser/requirements-ocr.txt
python -m workers.parser.ocr_pdf \
  --pdf data/private/pdfs/xiaomi-2025-ar.pdf \
  --document-id xiaomi-2025 \
  --out data/private/corpus/ocr/xiaomi-2025.jsonl \
  --dpi 150
```

`ocr_pdf` 支持断点续跑（按已写入页码跳过），输出同样的 `document_id/page/text` JSONL。

