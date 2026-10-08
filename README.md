# 企策通 · 北京企业政策预审

个人开源项目：面向北京企业的政策材料预审工作台。把“政策条款 → 企业事实 → 原始材料 → 核查结果”串通，支持 Nexent 智能体通过 MCP 和 Skill 调用。可先独立运行本地规则工作台，再按需接入模型与 Nexent。

## 本版实际能力

- 北京科技型中小企业评价、高新技术企业认定两个事项；2025 / 2026 科技型中小企业申报季快照。
- 5 个明确标注的模拟企业：完整、缺失、规模不满足、冲突、新成立。
- 带材料引用的确定性规则计算；单位归一、资料期间校验、直通车与基础条件分别核查。
- 申报条件与受理窗口分开输出。模型不能修改数值判定。
- PDF 文字层、DOCX、XLSX、CSV、TXT 导入、SHA-256 标识、原文定位、人工确认候选。PNG/JPG 可选用本地 OCR 生成待核对草稿。
- 可选兼容 Chat Completions 接口的文字/图片提取；提取结果仅为候选，不会自动改变企业事实。
- 政策版本差异及企业复核、证据依赖图、Markdown 报告、操作日志。
- 真实 MCP SDK 的 Streamable HTTP / SSE / stdio 服务、9 个工具与 5 个 Nexent Skill ZIP。
- 15 个困难案例和本地 Qwen3 8B 单模型消融；评测中心展示状态准确率、待补字段准确率和耗时。
- 上传政策文本中的明确数值上限/比例候选、现行规则对齐与逐企业假设影响预览；候选不自动生效。
- 50 条官方公开拟入库记录的资料不足拒判评测，与模拟困难案例及授权企业案例分开报告。
- 制造业来料抽检的第二行业模拟模板，复用同一证据规则引擎验证通过/不通过/待补证三种状态；不代表真实行业效果。

本机已完成 Nexent v2.6.0、企策通 MCP、5 个 Skills 和本地 Qwen3 8B 的实际联调。自动冒烟轨迹验证了 Agent 调用 `review_enterprise`、`get_system_evaluation`、`preview_uploaded_policy_change`，以及一次代码动作内先 `search_policy_evidence` 再 `review_enterprise`。15 个模拟困难案例中，确定性引擎状态判断为 15/15，Qwen3 8B 单模型基线为 10/15；这只证明随仓库案例上的可复现性。另有 50 条官方公开记录的资料不足拒判结果，不能算真实企业资格准确率。知识库检索仍采用本地词项匹配；概念候选基于种子术语，规则变化候选只识别明确上限和部分比例。预审仅覆盖已实现指标，最终资格认定仍有未自动化的业务条件。

## 在当前电脑启动

双击 `START.cmd`，或运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Qicetong.ps1
```

- 工作台：http://127.0.0.1:8765
- REST API 文档：http://127.0.0.1:8765/docs
- MCP Streamable HTTP：http://127.0.0.1:8767/mcp
- MCP SSE（兼容测试）：http://127.0.0.1:8766/sse
- 数据库、上传原件、运行日志：`runtime/`，不进入版本控制。

若启动失败，查看 `runtime/web.err.log` 与 `runtime/mcp.err.log`。

## 在其他机器安装

实测环境为 Windows / Python 3.14，2026-10-08 已通过 67 项 Python 测试；独立解压的源码包也通过同样的 67 项测试。启动脚本会检查虚拟环境及核心依赖是否可用。

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn qicetong.app:app --host 127.0.0.1 --port 8765
# 第二个终端
.\.venv\Scripts\python.exe -m qicetong.mcp_server
```

`requirements.lock.txt` 固定了本机 Windows/Python 3.14 实测版本；其他 Python 版本或系统先使用 `requirements.txt`。浏览器页面不依赖 npm 构建或外部 CDN。

需要离线图片识别时，再运行 `.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt`。上传 PNG/JPG 后，在材料详情点击“本地 OCR 识别”；候选只有在用户打开原图逐项核对并勾选确认后才可采纳。已用模拟图片实测识别与浏览器确认流程。扫描 PDF 仍须先逐页转为图片；本版不批量 OCR PDF。

Docker 方案：`docker compose up --build -d`。Nexent 的完整本机部署使用 `START-NEXENT.cmd`，详见 `nexent/NEXENT-SETUP.md`。

## 可选模型提取

将 `.env.example` 复制为 `.env`，在本机填写兼容接口的基础地址（通常包含 `/v1`）、文本模型、密钥，及可选视觉模型。不要提交 `.env`。刷新页面后，在企业材料详情点击“使用模型提取候选”。点击会把该份材料发送到配置的服务商；不自动发送其他材料。

只对能在原文中找到连续引用的文本候选提供确认入口；模型图像识别和本地 OCR 的结果都作为未核验草稿。无文字层的 PDF 需先转换为图片，原型不自动批量 OCR。未配置模型时仍可使用本地 OCR、规则和结构化补证流程。

## 一个五分钟演示

1. 工作台选择“星河智研”，对 2026 高企事项执行预审，日期设为 `2026-09-22`。
2. 展开“三年研发费用比例”，查看按金额合计的计算及逐年度材料。
3. 改选“青芽数据”，看到 2024 年研发费用缺失。
4. 在“政策与材料”下载补证示例并上传，将候选确认到“青芽数据”。
5. 回到预审重新执行，查看该项变为已核对满足。旧报告仍保留。
6. 切换科技型中小企业评价，看到“条件满足”与“填报已截止”同时成立。
7. 查看版本演进、证据图并导出报告。

演示日期为固定回放日期；默认界面使用机器当前日期。不得把历史回放截图当作实时申报信息。

## 检查与资料

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\fetch_sources.py
.\.venv\Scripts\python.exe scripts\package_skills.py
.\.venv\Scripts\python.exe scripts\evaluate_system.py --with-llm
.\.venv\Scripts\python.exe scripts\evaluate_transfer.py
.\.venv\Scripts\python.exe scripts\smoke_ocr.py
```

公开资料评测仅附历史汇总。要重跑 `scripts/evaluate_public_notice.py`，须先准备未随仓库分发的本地逐条资料，见 `docs/public-data-evaluation.md`。

浏览器端到端测试使用 Playwright + 本机 Edge。`npm install` 后启动一套独立测试服务（`QCT_RUNTIME` 指向临时目录，例如端口 8879），设置 `QCT_TEST_URL` 并运行 `node tests/browser.cjs`；安装可选 OCR 后再运行 `node tests/browser_ocr.cjs`。不要让补证测试改变正式案例。

- `docs/architecture.md`：架构、数据流、算法边界。
- `docs/nexent-integration.md`：Nexent 接入说明和联调验收。
- `docs/evaluation.md`：困难案例、单模型消融方法、结果与适用边界。
- `docs/policy-change-preview.md`：上传政策的待核验规则候选、企业影响预览与安全边界。
- `docs/manufacturing-transfer.md`：第二行业模拟模板的复用测试及边界。
- `docs/release-audit.md`：待公开文件扫描结果、上游许可与仍需人工确认的发布事项。
- `docs/data-publication.md`：公开源码、合成数据、历史汇总和本地材料的范围。
- `docs/github-release.md`：源码打包与 GitHub 发布步骤。
- `artifacts/nexent-agent/qicetong-beijing-agent.zip`：从当前 Nexent 实例真实导出的 Agent 与 Skills 包。
- `data/sources.json`：政策来源清单。
- `data/sources/manifest.json`：本机生成的抓取状态、时间和文件哈希，不随公开包分发；新环境获取来源后再生成。
- `nexent/agent-instructions.md`：智能体系统指令。
- `artifacts/nexent-skills/`：可上传技能包。
- `docs/public-data-evaluation.md` 与 `artifacts/public-notice-summary.json`：历史 50 条公示记录的汇总及可验证任务，不计入已授权企业案例。逐条名册与带名结果仅保留在本机；公开版评测中心显示历史汇总。
- `data/authorized_case_schema.json` 与 `scripts/validate_authorized_case.py`：脱敏结构化案例格式与机器校验；签署真实性仍须人工核验。

本地原型默认仅监听回环地址，无多用户身份认证。部署为团队服务时需要先补充访问控制。公开源码与公开企业原始材料是两件事，真实数据须按授权范围处理。

## 许可证与公开范围

企策通自研代码、原创文档、合成示例与原创 Skill 使用 [MIT](LICENSE)。许可证使用 `Qicetong contributors` 作为贡献者集合署名。`package.json` 的 `private: true` 仅防止误发布到 npm，不妨碍 GitHub 源码公开。

`nexent/runtime-overlay/agents/` 基于 Nexent v2.6.0 作兼容适配，保留上游 MIT 许可和 NOTICE；第三方依赖、模型权重、政府原文、企业资料与商标不自动适用本项目 MIT。详情见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。首版公开包排除了企业逐条名单、采集台账、Office 文件、网页全文缓存、密钥、运行原件与模型权重；本机原件没有删除。

运行 `python scripts/build_public_release.py` 可生成通过扫描的个人开源源码 ZIP 与哈希清单。它只打包本地文件，不自动提交或推送。参赛评分、答辩、招募材料和 Office 制作脚本不进入此仓库；本机原文件仍保留。
