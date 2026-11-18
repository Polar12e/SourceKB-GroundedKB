# workers/retrieval（骨架）

Python retrieval worker，负责 BM25 / dense / RRF / hit window。当前只实现：

- `GET /healthz`：`{"status":"ok","service":"retrieval"}`
- `POST /search`：返回 **501**，等待从旧项目迁移检索算法（T1.2）

## 本地运行

```bash
source scripts/goenv.sh   # 仅 Go 需要；Python 用仓库根 .venv
make py-install
make py-test
make py-run-retrieval
# 另一个终端
curl http://127.0.0.1:8081/healthz
```

## 约定

- 响应字段以 `contracts/schemas/search-*.schema.json` 为准；
- 迁移完成后，`/search` 返回 `SearchResponse`，每个 hit 带 `chunk_id` 与 page/line locator；
- 真实检索算法未就绪前，不返回伪造的命中。
