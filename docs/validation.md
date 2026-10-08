# 实测记录

2026-10-08：完整 Python 测试 67 项通过（1 条上游弃用警告）；源码 ZIP 独立解压后，在本机已安装依赖环境中也通过 67 项。发布扫描发现 0 项。浏览器、OCR 与 Nexent 的实测日期为下表的 2026-09-26。

记录日期：2026-09-26（Asia/Shanghai）。评测方法与数据类型见 `docs/evaluation.md`、`docs/public-data-evaluation.md` 和 `docs/manufacturing-transfer.md`。

| 验证项 | 实测结果 | 证据 |
| --- | --- | --- |
| Python 业务与接口 | 62 项通过，0 失败 | `python -m pytest -q` |
| 浏览器主流程 | 15 个流程通过，控制台 0 错误 | `artifacts/browser-results.json`、`artifacts/screenshots/` |
| 浏览器图片流程 | 模拟图片上传、本地 OCR、原图核对与勾选确认流程通过 | `tests/browser_ocr.cjs`、`artifacts/ocr-smoke-results.json` |
| 本地 OCR 引擎 | 模拟人员记录图识别出 1 行并提出 `employees` 候选，保持未核验 | `scripts/smoke_ocr.py`、`artifacts/ocr-smoke-results.json` |
| MCP stdio / SSE | 9 个工具发现与调用通过；SSE 客户端可读政策目录 | `tests/test_mcp.py`、`artifacts/mcp-sse-results.json` |
| 官方来源缓存 | 5 个页面保存抓取时间、最终地址与 SHA-256 | `data/sources/manifest.json` |
| Nexent | 本机 v2.6.0 中已绑定 9 个工具和 5 个 Skills，并从实例导出 Agent 包 | `runtime/nexent/integration-results.json`、`artifacts/nexent-agent/qicetong-beijing-agent.zip` |
| Agent 调用轨迹 | 预审、评测、政策变化预览，以及同一次代码动作中的“检索→预审”均有实际工具轨迹 | `runtime/nexent/smoke-agent-*-results.json` |
| 模拟困难案例 | 规则引擎 15/15，Qwen3 8B 单模型 10/15；待补字段 7/7 对 2/7 | `artifacts/evaluation-results.json` |
| 公开公示记录 | 50/50 在缺少申报材料时返回待补证；覆盖 16 个区 | 公开汇总 `artifacts/public-notice-summary.json`；本机逐条结果 `artifacts/public-notice-results.json` |
| 第二行业合成模板 | 3/3 合成批次符合预设的通过、不通过、待补证状态 | `artifacts/manufacturing-transfer-results.json`、`tests/test_transfer.py` |

主浏览器测试使用独立 `QCT_RUNTIME` 保存测试数据。该次实测的 `/api/health` 版本为 `0.3.0`，Nexent 连通性使用实时探测，历史联调日期保存在 `nexent_last_verified`。本地 Nexent 页面 `http://localhost:3000/zh` 返回 HTTP 200。

验证数据包括 15 个合成困难案例、3 个制造业合成批次及 50 条公开公示记录。公示记录缺少企业申报材料和授权；OCR 使用清晰模拟图片验证功能链路。真实扫描件准确率与完整企业资格效果需另行评测，人工复核事项见架构说明。

2026-09-26 的 62 项测试通过，记录了 1 条 Starlette/FastAPI `TestClient` 上游弃用警告；更新依赖后重跑测试。
