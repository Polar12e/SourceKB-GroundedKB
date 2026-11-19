# 系统测试集（黑盒）

测试当前本地三服务：retrieval / agent / gateway。

- Fixture：2 文档、3 页合成语料，不依赖 `data/private/`。
- 用例：`cases.json`（14 条），覆盖健康检查、检索字段、metadata filter、OOV、错误形态、`/ask` citation/拒答、直连与 gateway 代理。
- Runner：`run_system.py`；启动器：`scripts/run_system_tests.sh`。
- 运行：

```bash
make test-system
```

报告写入 `tests/e2e/report.md`。测试失败时脚本返回非零。

这不是检索质量 benchmark；质量评测在 `eval/`。
