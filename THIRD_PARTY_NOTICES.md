# 第三方组件与数据来源

企策通自研代码、原创文档、合成示例与原创 Skill 使用根目录的 MIT 许可证。第三方代码、政府政策原文、企业公示数据、模型权重及商标不因本项目的 MIT 许可而改变权利归属。

## 随仓库分发的 Nexent 兼容代码

`nexent/runtime-overlay/agents/core_agent.py` 和 `nexent/runtime-overlay/agents/nexent_agent.py` 基于 Nexent v2.6.0 修改，用于本地兼容适配。原著作权：Huawei Technologies Co., Ltd.，2025。来源：[Nexent](https://github.com/ModelEngine-Group/nexent)，许可证：[MIT](nexent/runtime-overlay/NEXENT_LICENSE)。上游声明完整保存在 [NEXENT_NOTICE](nexent/runtime-overlay/NEXENT_NOTICE)，不可删除或替换为本项目声明。修改详情见 [Nexent 接入说明](docs/nexent-integration.md)。

## 通过包管理器安装的直接依赖

以下依据本机已安装包元数据核对于 2026-10-08。仓库分发依赖声明，不包含这些库的安装副本；各组件仍适用其自己的许可证。此表不是完整传递依赖清单，安装版本变化或将依赖打包分发时须检查对应版本的许可文件。

| 组件 | 本机版本 | 包元数据中的许可证 | 官方来源 |
| --- | --- | --- | --- |
| FastAPI | 0.141.1 | MIT | https://github.com/fastapi/fastapi |
| Uvicorn | 0.54.0 | BSD-3-Clause | https://github.com/Kludex/uvicorn |
| MCP Python SDK | 1.30.0 | MIT | https://github.com/modelcontextprotocol/python-sdk |
| pypdf | 6.19.0 | BSD-3-Clause | https://github.com/py-pdf/pypdf |
| python-multipart | 0.0.32 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| openpyxl | 3.1.5 | MIT | https://openpyxl.readthedocs.io/ |
| HTTPX | 0.28.1 | BSD-3-Clause | https://github.com/encode/httpx |
| Beautiful Soup | 4.15.0 | MIT | https://www.crummy.com/software/BeautifulSoup/ |
| pytest | 9.1.1 | MIT | https://github.com/pytest-dev/pytest |
| python-dotenv | 1.2.3 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| RapidOCR（可选） | 3.9.2 | Apache-2.0 | https://github.com/RapidAI/RapidOCR |
| ONNX Runtime（可选） | 1.30.0 | MIT | https://github.com/microsoft/onnxruntime |
| Playwright（开发依赖） | 1.63.0（package-lock） | Apache-2.0 | https://github.com/microsoft/playwright |

## 模型与 OCR 权重

仓库不分发 Ollama、Qwen3 或 OCR 模型权重。安装脚本只是配置或下载入口；使用者须遵守实际下载的模型版本、服务和权重许可证。RapidOCR 库代码的许可证不自动替代所有模型权重的许可证。

## 政策与公示资料

政府政策和公示来源见 [data/sources.json](data/sources.json) 及 [公开数据说明](docs/data-publication.md)。本项目保留来源和必要的核查条款，但不将外部原文授权为 MIT；网页全文缓存、50 家企业逐条名单、采集台账及带企业名的评测输出暂不分发。公开包只提供不含企业名的历史评测汇总。不得把公示名单解释为企业授权、最终入库或真实申请材料。

## 名称与标识

Huawei、Nexent、Qwen 和其他名称仍属于相应权利人。本项目是个人开源原型，不表示这些权利人或政策发布机构的认可或背书。
