# workers/embedding

Embedding provider，供 dense 通道使用。

## 已迁移

- `Embedder` 协议（`name` / `dim` / `encode`）；
- `LsaEmbedder`：语料自拟合的 TF-IDF + randomized SVD，离线、确定性、numpy-only；
- `OpenAICompatibleEmbedder`：`POST {base_url}/embeddings`，支持超时/重试/batch；
- `EmbeddingCache`：按内容指纹 + provider + 维度缓存 `.npz`；
- `embed_documents`：拟合、缓存、维度校验。

## 当前策略

旧项目实测离线 LSA 的 dense 通道弱于 BM25，因此 **API 默认仍用 BM25**。dense 已通过 `workers/retrieval/dense.py` 接入 `HybridIndex`，等真实预训练 embedding 模型（bge-m3 / API）接入后再切换默认。

## 测试

```bash
make py-test
```

`workers/embedding/tests` 覆盖归一化、LSA、缓存、OpenAI 兼容 transport 假实现。
