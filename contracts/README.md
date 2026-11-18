# contracts（待建）

这里放跨服务契约，不依赖任何实现：

- OpenAPI：Gateway / Agent / Retrieval
- JSON Schema：Document / Chunk / SearchHit / Answer / Citation / EvalCase
- protobuf（可选）：Go ↔ Python 高频调用

第一版先定义：

1. `Document`
2. `Chunk`
3. `SearchRequest` / `SearchHit`
4. `Answer` / `Citation`
5. `EvalCase` / `EvalResult`

契约评审通过后，再写服务代码。
