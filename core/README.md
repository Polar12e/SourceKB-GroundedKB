# core（部分落地）

跨 domain 的算法与协议：

- `text.py`：数字归一化、中文 bigram 分词、行切分（已迁移）；
- `retrieval/terms.py`：通用名词表加载、bigram 匹配、扩展词生成；
- chunking：行感知切块、表格块（当前在 `workers/retrieval/chunking.py`，后续可抽回 core）；
- retrieval：BM25 / RRF / hit window（当前在 `workers/retrieval/`）；
- citation：page/line/quote locator（契约已定，实现待建）；
- evaluation：Hit@k / Recall / MRR / citation / abstention（待建）；
- security：endpoint / truncation / audit（待建）。

domain 专用参数不要写进 core；finance 的名词表在 `domains/finance/terms.json`，四通路参数在 `config/retrieval.yaml`。
