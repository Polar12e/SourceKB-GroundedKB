# contracts（v0 草案）

跨服务契约，不依赖任何实现。当前为 **v0 草案**，评审通过后冻结；冻结后修改需要版本升级或 ADR。

## 目录

```text
contracts/
├─ openapi.yaml              # Gateway / Retrieval / Agent 端点
├─ schemas/                  # JSON Schema 2020-12
│  ├─ document.schema.json
│  ├─ chunk.schema.json
│  ├─ locator.schema.json
│  ├─ search-request.schema.json
│  ├─ search-hit.schema.json
│  ├─ search-response.schema.json
│  ├─ evidence.schema.json
│  ├─ citation.schema.json
│  ├─ answer.schema.json
│  ├─ eval-case.schema.json
│  ├─ eval-result.schema.json
│  ├─ health.schema.json
│  └─ error.schema.json
└─ examples/                 # 每个 schema 的最小合法样例
```

## 约定

- JSON Schema 使用 **Draft 2020-12**；`$id` 指向仓库路径。
- `additionalProperties: false`：v0 先严格，新增字段需要评审。
- `locator` 的 `page` 从 1 开始；`line_end >= line_start` 由实现/测试保证（JSON Schema 不做跨字段比较）。
- `Answer.status = insufficient_evidence` 时，`citations` 可以为空；无证据不得硬答。
- `SearchHit` 必须带 `chunk_id` 和 `locator`，保证页面/行号可回链。
- `EvalCase.gold_evidence` 至少一条；`EvalResult.metrics` 的取值范围为 0–1。

## 端点（v0）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/healthz` | 所有服务的存活检查 |
| POST | `/documents` | 上传文档并排队 ingest（202） |
| POST | `/search` | 检索 chunk，返回 page/line locator |
| POST | `/ask` | 回答 + citations，或 `insufficient_evidence` |

认证、限流、分页和错误码细节不在 v0 范围内；实现前补契约。

## 校验

```bash
source .venv/bin/activate   # 或使用 make contracts
python scripts/check_contracts.py
```

校验内容：

1. 所有 `schemas/*.schema.json` 是合法 Draft 2020-12 schema；
2. `examples/*.json` 能通过对应 schema；
3. `openapi.yaml` 可解析，版本为 3.1.0，包含四个 v0 端点，外部 `$ref` 文件存在。

## 待评审问题

1. `/documents` 用 multipart 还是先上传对象存储再提交 metadata；
2. `Document.sha256` 是否允许客户端提供，还是服务端计算后返回；
3. `SearchHit.text` 是否包含行号前缀（旧项目格式）；
4. `Citation.quote` 与 locator 的精确匹配规则；
5. 错误模型是否统一为 `{"error": {"code", "message"}}`。

## SearchHit 证据字段

- `anchor`：命中 chunk 的行区间（与展示 window 区分）；
- `anchor_text`：chunk 原文，用于 verbatim citation；
- `channels`：参与投票的通道列表。

`Answer.status` 增加 `unverified` / `conflicting_evidence`。

## 错误响应

`/search` 的 400 已统一为 `{"error":{"code","message"}}`；系统测试 `tests/e2e` 会校验该 envelope。
