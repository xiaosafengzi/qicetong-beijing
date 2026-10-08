# Nexent 本机部署与企策通接入

Nexent 源码版本为 v2.6.0，位置在 `external/nexent-develop`。功能演示使用北京公开政策与模拟企业数据。

## 已完成

- Docker Desktop、WSL2、Nexent 基础服务和网页已启动，Docker 虚拟磁盘位于 `D:\DockerDesktopData`，Nexent 数据位于 `D:\NexentData`。
- Nexent 网页 `http://localhost:3000` 和配置 API `http://127.0.0.1:5010/health/ready` 已通过本机访问检查。
- 已通过 Nexent API 注册企策通 MCP，发现并启用 9 个工具；5 个自定义 Skills 已上传并绑定到 Agent `企策通·北京企业政策预审`。8B 本地模型负责工具编排，确定性 MCP 工具执行核心预审和数值规则。接入结果记录在 `runtime/nexent/integration-results.json`。
- 已建立独立的 `企策通演示租户` 和租户管理员，并将 Agent 发布为可用版本。登录后从左侧 `开始问答` 进入，即可在智能体列表中选择 `企策通·北京企业政策预审`。
- Windows 版 Ollama 0.34.3 已安装到 D 盘，模型 `qwen3:8b` 已下载并注册为 Nexent Agent 模型；模型连通性和 Agent 可用性检查均通过。
- 官方 Nexent v2.6.0 后端上叠加了本地兼容镜像 `qicetong/nexent:v2.6.0-local`，启用结构化 CodeAgent 输出并处理小模型漏写最终交付语句的情况。`START-NEXENT.cmd` 会自动重建该镜像。
- 端到端冒烟测试已通过：预审、系统评测、检索后预审和上传政策变化预览均有 Agent 工具轨迹。检索后预审在一次代码动作内先调用 `search_policy_evidence` 再调用 `review_enterprise`。
- 本项目测试运行 `python -m pytest -q`，结果以 `docs/validation.md` 的最近一次记录为准。
- 15 个模拟困难案例评测已完成：确定性引擎状态判断 15/15，本地 Qwen3 8B 单模型 10/15；方法与结果见 `docs/evaluation.md`。

## 地址与数据

- Nexent：`http://localhost:3000`
- 企策通工作台：`http://127.0.0.1:8765`
- 企策通 MCP：主机 `http://127.0.0.1:8767/mcp`；Docker 容器 `http://host.docker.internal:8767/mcp`。`8766/sse` 仅保留兼容测试。
- 本地模型 OpenAI 兼容接口：主机 `http://127.0.0.1:11434/v1`；Docker 容器 `http://host.docker.internal:11434/v1`
- 企策通演示租户的登录信息存放在 `runtime/nexent/demo-access.txt`；Nexent 超级管理员信息存放在 `runtime/nexent/local-access.txt`。两者都请勿公开或提交到仓库。

## 重启与检查

1. 启动 Docker Desktop，等待 Docker 引擎就绪。
2. 双击根目录 `START.cmd` 启动企策通工作台和 MCP。
3. 双击根目录 `START-NEXENT.cmd` 启动并检查 Nexent。首次运行会下载镜像；日志在 `runtime/nexent/deploy.log` 和 `deploy.err.log`。
4. 双击根目录 `START-LOCAL-MODEL.cmd` 启动 Ollama；模型文件存放在 `D:\NexentData\ollama\models`，权重下载可断点续传。
5. 打开 Nexent 网页，用 `runtime/nexent/demo-access.txt` 中的账户登录。点击左侧 `开始问答`，选择 `企策通·北京企业政策预审`。若出现“尚未配置向量模型”，直接关闭提示即可；当前预审流程不依赖记忆检索。

若需要在全新数据库中重新部署，依次运行：

1. `.venv\Scripts\python.exe nexent\setup_demo_tenant.py`，建立演示租户与租户管理员；
2. `.venv\Scripts\python.exe nexent\connect_qicetong.py`，注册 MCP、九个工具、五个 Skills 和 Agent；
3. `.venv\Scripts\python.exe nexent\configure_local_model.py`，注册并绑定本地模型，同时发布 Agent。

三段脚本都会检查已有记录，可重复执行而不会重复创建同名资源。

端到端预审复验运行 `.venv\Scripts\python.exe nexent\smoke_agent.py`；检索后预审使用 `--mode search_review`，变化预览使用 `--mode policy_change`。需要提交平台原生配置时，运行 `.venv\Scripts\python.exe nexent\export_agent.py`。

`STOP-NEXENT.cmd` 停止 Nexent 容器但保留数据。`nexent/Repair-DockerSockets.ps1` 只用于 Docker Desktop 因遗留 Unix socket 报错而无法启动的情况。

## 运行范围

当前部署启用 infrastructure、application、supabase，Docker sandbox 使用 lightweight 模式。data-process、terminal、monitoring 及其他可选镜像按需配置。政策审查由 MCP 工具计算规则、证据和报告，模型选择工具并组织解释。
