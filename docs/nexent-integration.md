# Nexent 接入与验收

已完成 Nexent v2.6.0、企策通 MCP、本地 Qwen3 8B 和 Agent 的端到端联调。本机配置与调用记录位于 `runtime/nexent/`。

## 来源

- 官方源码：https://github.com/ModelEngine-Group/nexent
- MCP 接入：https://modelengine-group.github.io/nexent/zh/integration/integration-in/mcp.html
- Skill 接入：https://modelengine-group.github.io/nexent/zh/integration/integration-in/skills.html
- Agent 导出：https://modelengine-group.github.io/nexent/zh/integration/integration-out/agents-export.html

## 连接步骤

1. 运行根目录 `START.cmd`，启动工作台、SSE 兼容端点和 Streamable HTTP MCP。Nexent 使用 `http://host.docker.internal:8767/mcp`。
2. 运行 `START-LOCAL-MODEL.cmd`，启动位于 D 盘的 Ollama 与 `qwen3:8b`。
3. 运行 `START-NEXENT.cmd`。脚本会构建本地兼容镜像并启动 infrastructure、application、supabase 组件。
4. 运行 `.venv\Scripts\python.exe nexent\setup_demo_tenant.py`，建立 `企策通演示租户` 和租户管理员。登录信息只保存在 `runtime/nexent/demo-access.txt`。
5. 运行 `.venv\Scripts\python.exe scripts\package_skills.py` 和 `.venv\Scripts\python.exe nexent\connect_qicetong.py`，幂等注册九个工具、五个 Skills 和 Agent。
6. 运行 `.venv\Scripts\python.exe nexent\configure_local_model.py`，注册本地模型、绑定 Agent 并发布可用版本。
7. 当前 Agent 同时绑定九个 MCP 工具和五个 Skills。核心预审由 `review_enterprise` 完成；检索后预审可在一次代码动作内顺序调用 `search_policy_evidence` 与 `review_enterprise`。Skill 保留分层流程、输入输出约束和跨模型迁移能力。
8. 运行 `.venv\Scripts\python.exe nexent\smoke_agent.py`，检查预审工具轨迹。
9. 分别运行 `smoke_agent.py --mode evaluation`、`--mode search_review` 和 `--mode policy_change`，验证评测、检索后预审和上传政策变化预览的工具调用。变化预览使用演示假设“职工总数不超过50人”。
10. 运行 `.venv\Scripts\python.exe nexent\export_agent.py`，从当前平台导出 Agent 与 Skills 包。

浏览器验收路径为：使用 `runtime/nexent/demo-access.txt` 登录 `http://localhost:3000`，点击左侧 `开始问答`，选择 `企策通·北京企业政策预审`。页面应显示欢迎语、`规划/执行` 模式、`Qwen3 8B 本地` 和消息输入框。

`nexent/connection.example.json` 用于人工配置参考；平台导入使用 `export_agent.py` 生成的 Agent ZIP，并核对 Nexent 版本兼容性。

## 验收请求

- “以 2026-09-22 为核查日，预审北京星河智研模拟企业的高企认定材料，给出研发比例计算与来源。”
- “青芽数据还缺什么？补齐 2024 年研发费用后重新核查，保留之前的报告。”
- “为什么科技型中小企业的数量指标满足，仍不能说今天可申报？”
- “比较北京科技型中小企业 2025 和 2026 申报季，哪些企业资料需更新？”
- “导出刚才的报告，并标明这是模拟材料。”

## 联调记录

排查问题时可保存 Nexent 版本、模型名称、Agent 配置、MCP 工具清单与轨迹、技能包和政策来源清单。自动记录包括 `integration-results.json`、`model-results.json`、四组 `smoke-agent` 结果及事件轨迹。公开结果包括 `artifacts/evaluation-results.json` 和 Agent 导出包，运行记录保留在本机 `runtime/`。
