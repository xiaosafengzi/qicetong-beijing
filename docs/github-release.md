# GitHub 发布说明

项目采用 MIT，贡献者署名为 `Qicetong contributors`，并保留上游 Huawei/Nexent 声明。新增内容按实际权利归属确认许可和署名。

## 本地审阅与打包

```powershell
.\.venv\Scripts\python.exe scripts\check_release.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\build_public_release.py
```

输出：`artifacts/releases/qicetong-beijing-source.zip`、`release-manifest.json` 和 `企策通-个人开源上传包.zip`。上传包包含 `qicetong-beijing/` 源码目录、上传说明与文件清单，适合浏览器上传或初始化本地仓库。清单记录文件大小、SHA-256 与源码 ZIP 哈希；输出目录由 Git 忽略，远程上传另行操作。

## 首次公开发布

1. 检查 `LICENSE`、`THIRD_PARTY_NOTICES.md`、`docs/data-publication.md` 和发布清单。
2. 在自己的 GitHub 账号创建或使用已有的 `qicetong-beijing` 仓库。
3. 解压个人开源上传包，进入 `qicetong-beijing/`，上传其中的文件和目录，让 `README.md` 位于仓库顶层。
4. 浏览器上传分两批进行，每批少于 100 个文件。以点开头的配置文件若被拖拽上传拦截，可通过 `Add file → Create new file` 按原名称和内容创建。外层上传说明和清单留在本地。
5. 使用 Git 客户端时，初始化源码目录、添加文件并提交，再连接已有远程仓库并推送；核对 `git diff --cached --stat` 和发布扫描结果。
6. 在 GitHub Release 附源码 ZIP 与清单，注明验证日期、数据类型和评测结果。

## 推荐仓库描述

> 企策通：基于 Nexent、MCP 与 Skill 的北京企业政策材料预审工作台，提供规则计算、证据追溯、政策变化预览与人工核对流程。

克隆仓库并安装依赖后，即可运行本地规则工作台；接入 Nexent 和模型服务后可使用智能体编排。MIT 允许复用和商用，原创代码与第三方组件的许可见根目录声明。
