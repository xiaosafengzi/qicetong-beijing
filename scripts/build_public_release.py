"""Build a checked source ZIP and manifest; does not commit or publish anything."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from check_release import ROOT, candidate_paths, inspect_payload


def main():
    paths = candidate_paths()
    report = inspect_payload(paths)
    if report["findings"]:
        raise ValueError("发布扫描未通过；运行 scripts/check_release.py 查看文件级问题")
    required = {"LICENSE", "README.md", "THIRD_PARTY_NOTICES.md", "docs/data-publication.md"}
    names = {path.relative_to(ROOT).as_posix() for path in paths}
    if not required <= names:
        raise ValueError("缺少发布声明文件")
    files = [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
              "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]
    output = ROOT / "artifacts/releases"
    output.mkdir(parents=True, exist_ok=True)
    archive_path = output / "qicetong-beijing-source.zip"
    temporary = output / "qicetong-beijing-source.zip.tmp"
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, "qicetong-beijing/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(temporary) as archive:
        for entry in files:
            actual = archive.read("qicetong-beijing/" + entry["path"])
            if hashlib.sha256(actual).hexdigest() != entry["sha256"]:
                raise ValueError("归档内容与清单不一致")
    temporary.replace(archive_path)
    manifest = {"generated_at": datetime.now(timezone.utc).isoformat(), "published": False,
                "license": "MIT (project-authored portions; third-party exclusions apply)",
                "audit": report, "files": files,
                "archive": {"filename": archive_path.name, "bytes": archive_path.stat().st_size,
                            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest()}}
    (output / "release-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    first_groups = {"qicetong", "web", "data", "scripts", "tests"}
    first_count = sum("/" not in entry["path"] or entry["path"].split("/")[0] in first_groups for entry in files)
    second_count = len(files) - first_count
    instructions = f"""企策通个人开源项目 · GitHub 上传说明

本包包含：
  qicetong-beijing/   应提交到 GitHub 的完整源码目录
  文件清单.json      文件大小、SHA-256 与发布扫描结果
  上传说明.txt       本说明

1. 将本 ZIP 解压到一个新的文件夹。
2. qicetong-beijing 是仓库根目录；README.md、LICENSE、qicetong、web 等应位于 GitHub 仓库顶层。
3. 已有空仓库时，在其页面点击 uploading an existing file。
4. 第一批拖入：源码目录顶层的文件，以及 qicetong、web、data、scripts、tests 文件夹（共 {first_count} 个文件）。填写提交说明并点击 Commit changes。
5. 第二批：点击 Add file → Upload files，拖入 artifacts、docs、nexent 文件夹（共 {second_count} 个文件），再次提交。
6. 发布后检查首页 README、LICENSE、THIRD_PARTY_NOTICES.md 和子目录是否完整。也可按 docs/github-release.md 使用 Git 客户端。

应提交源码目录里的文件及其目录结构；不要只把整个 ZIP 当成一个文件上传到仓库。
外层的本说明与文件清单可留在本地供核查，不必放入源码仓库。

公开范围：自研代码、原创文档、MCP、Skill、模拟数据与无企业名的历史汇总。
没有包含：密钥、运行数据库、上传原件、企业逐条名册、采集台账、Office 文件、政策全文缓存和模型权重。
个人版还排除了参赛评分、赛题对照、答辩稿、企业招募流程和 Office 制作脚本；原文件仍保留在本机。
这是一份源码包；尚未推送到 GitHub，也未包含本机依赖环境。
"""
    upload_path = output / "企策通-个人开源上传包.zip"
    upload_temporary = output / "github-upload.zip.tmp"
    with zipfile.ZipFile(archive_path) as source, zipfile.ZipFile(upload_temporary, "w", zipfile.ZIP_DEFLATED) as upload:
        for name in source.namelist():
            upload.writestr(name, source.read(name))
        upload.writestr("上传说明.txt", instructions)
        upload.writestr("文件清单.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    with zipfile.ZipFile(upload_temporary) as upload:
        if upload.testzip() is not None:
            raise ValueError("上传包 CRC 检查失败")
        for entry in files:
            actual = upload.read("qicetong-beijing/" + entry["path"])
            if hashlib.sha256(actual).hexdigest() != entry["sha256"]:
                raise ValueError("上传包内容与源码清单不一致")
    upload_temporary.replace(upload_path)
    print(json.dumps({"archive": str(archive_path.relative_to(ROOT)), "upload_package": str(upload_path.relative_to(ROOT)),
                      "candidate_files": len(paths), "findings": 0, "published": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
