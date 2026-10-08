# GitHub 发布说明

本地开源候选包已经选择 MIT，用 `Qicetong contributors` 作为贡献者集合声明，未假定个人或学校名称。实际发布者须确认自己及团队有权公开这些原创内容；若学校或团队有署名约定，先据实调整版权行。上游 Huawei/Nexent 的声明保持原样。

## 本地审阅与打包

```powershell
.\.venv\Scripts\python.exe scripts\check_release.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\build_public_release.py
```

输出：`artifacts/releases/qicetong-beijing-source.zip`、`release-manifest.json`，以及 `企策通-个人开源上传包.zip`。上传包内含 `qicetong-beijing/` 源码目录、`上传说明.txt` 和 `文件清单.json`；它不含 `.git` 历史，可用浏览器上传或初始化本地仓库。清单记录每个源码文件的大小、SHA-256 与源码 ZIP 哈希。输出目录本身不进入 Git，避免重复打包。该操作不创建远程仓库、不提交、不推送。

## 首次公开发布

1. 检查 `LICENSE`、`THIRD_PARTY_NOTICES.md`、`docs/data-publication.md` 和发布清单。
2. 在自己的 GitHub 账号创建或使用已有的 `qicetong-beijing` 仓库。
3. 解压个人开源上传包，进入 `qicetong-beijing/`。上传其中的文件和目录，让 `README.md` 位于仓库顶层；不要只上传 ZIP，也不要再套一层同名目录。
4. 浏览器上传可按包内说明分两批拖入目录，并分别提交。外层上传说明和文件清单留在本地即可。
5. 使用 Git 客户端时，先初始化源码目录、添加文件并提交，再连接已有远程仓库并推送；核对 `git diff --cached --stat` 和扫描结果。已有跟踪文件也必须扫描，不能只看 `.gitignore`。
6. 可在 GitHub Release 附源码 ZIP 与清单，注明实际验证日期。保留模拟数据、历史汇总和真实授权案例为 0 的说明。

## 推荐仓库描述

> 企策通：基于 Nexent、MCP 与 Skill 的北京企业政策材料预审原型。提供确定性规则计算、证据追溯、政策变化候选与人工核对流程，使用明确标注的合成示例。

公开源码不等于在线部署。其他人需要安装依赖、配置 Nexent/模型后才能复现智能体；无模型服务时仍可运行本地规则工作台。MIT 允许复用和商用，原创代码和第三方资料的许可范围见根目录声明。
