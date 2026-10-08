# 个人开源包核查记录

核查日期：2026-10-08。项目自研部分采用 MIT，根目录 `LICENSE` 使用 `Qicetong contributors` 署名；第三方归属见 `THIRD_PARTY_NOTICES.md`。

公开范围包括源码、原创 Markdown 文档、合成示例、测试、Skill ZIP、Agent 导出包与无企业名的历史汇总。本地资料由 `.gitignore` 和发布扫描排除，完整范围见 `docs/data-publication.md`。

`scripts/check_release.py` 扫描已跟踪文件、未跟踪候选和嵌套 ZIP，检查疑似明文密钥、归档路径、禁止分发文件和本地企业名。本次扫描发现 0 项；Nexent 上游 MIT 和 NOTICE 完整保留。

完整 Python 测试在 2026-10-08 通过 67 项（1 条上游弃用警告）。数据处理测试使用合成记录，支持公开源码独立验证。

源码 ZIP 独立解压后，使用本机已安装依赖再次通过 67 项测试。验证环境为 Windows / Python 3.14，依赖版本见 `requirements.lock.txt`。

`scripts/build_public_release.py` 生成 `artifacts/releases/qicetong-beijing-source.zip` 和 `release-manifest.json`，清单记录文件数量、逐文件 SHA-256、ZIP 哈希与扫描结果。

2026-10-08 已核对首版 [GitHub 公开仓库](https://github.com/xiaosafengzi/qicetong-beijing)：120 个文件与当时的源码包逐一一致。后续更新按 `docs/github-release.md` 的流程上传。
