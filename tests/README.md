# tests

分层：

- `unit`：chunking、BM25、RRF、citation、config；
- `contract`：Go/Python 契约一致性；
- `e2e/`：黑盒系统测试（retrieval + agent + gateway）；
- `eval/`：检索质量 benchmark（见仓库根 `eval/`）。

系统测试：

```bash
make test-system
```

使用合成 fixture，不依赖私有语料；报告在 `tests/e2e/report.md`。

真实 LLM 不进默认 CI；使用 fake client 或 `--live` 手动触发。
