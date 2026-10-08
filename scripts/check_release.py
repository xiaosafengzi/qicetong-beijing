"""Inspect the prospective Git payload without printing any secret values."""
from __future__ import annotations

import io
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SUSPICIOUS = re.compile(
    rb"(?i)(?:api[_-]?key|password|secret|access[_-]?token)['\"]?\s*[:=]\s*['\"](?!\$|\{|<|your|example|placeholder|none|null|ollama)([A-Za-z0-9_./+=-]{16,})"
)
TOKEN = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|eyJ[A-Za-z0-9_-]{12,}\.eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})")
MAX_MEMBER_BYTES = 16_000_000
LOCAL_ONLY = {"data/public_candidate_seed_2026.json", "data/public_case_records_2026.jsonl", "artifacts/public-notice-results.json", "data/sources/manifest.json"}
TEXT_SUFFIXES = {".py", ".js", ".cjs", ".mjs", ".json", ".jsonl", ".md", ".txt", ".ps1", ".html", ".yaml", ".yml", ".toml", ".example", ".cmd"}


def candidate_paths(root: Path = ROOT) -> list[Path]:
    """Include tracked files too: .gitignore cannot hide an already tracked secret."""
    raw = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root)
    names = sorted({part.decode("utf-8") for part in raw.split(b"\0") if part})
    return [root / name for name in names if (root / name).exists() or (root / name).is_symlink()]


def forbidden_path(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    parts = {part.lower() for part in path.parts}
    filename = path.name.lower()
    return (path.is_absolute() or (path.parts and path.parts[0].endswith(":")) or ".." in path.parts or bool(parts & {"runtime", "external", ".git", ".venv", ".venv312", "node_modules", "__pycache__"})
            or (filename.startswith(".env") and filename != ".env.example")
            or path.as_posix() in LOCAL_ONLY
            or path.suffix.lower() in {".onnx", ".gguf", ".safetensors", ".sqlite3", ".docx", ".xlsx"}
            or path.as_posix().startswith("artifacts/releases/"))


def inspect_payload(paths: list[Path], root: Path = ROOT) -> dict:
    findings = []
    archive_count = 0
    member_count = 0
    public_names = []
    public_seed = root / "data/public_candidate_seed_2026.json"
    if public_seed.is_file():
        seed = json.loads(public_seed.read_text(encoding="utf-8"))
        public_names = [row["company_name"].encode("utf-8") for row in seed["candidates"]]

    def inspect_bytes(label: str, content: bytes):
        if SUSPICIOUS.search(content) or TOKEN.search(content):
            findings.append((label, "possible_literal_secret"))
        if any(name in content for name in public_names):
            findings.append((label, "local_only_company_name"))

    def inspect_zip(label: str, content: bytes, depth: int = 0):
        nonlocal archive_count, member_count
        if depth >= 5:
            findings.append((label, "archive_nesting_limit"))
            return
        archive_count += 1
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    member_count += 1
                    member_label = label + "::" + member.filename
                    if forbidden_path(member.filename):
                        findings.append((member_label, "forbidden_archive_path"))
                    if member.file_size > MAX_MEMBER_BYTES:
                        findings.append((member_label, "oversized_archive_member"))
                        continue
                    nested = archive.read(member)
                    if member.filename.lower().endswith(".zip"):
                        inspect_zip(member_label, nested, depth + 1)
                    else:
                        inspect_bytes(member_label, nested)
        except (zipfile.BadZipFile, RuntimeError):
            findings.append((label, "unreadable_archive"))

    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            findings.append((relative, "symlink_or_external_path"))
            continue
        if forbidden_path(relative):
            findings.append((relative, "local_only_path_in_payload"))
            continue
        if path.stat().st_size > MAX_MEMBER_BYTES:
            findings.append((relative, "oversized_file_review_required"))
            continue
        content = path.read_bytes()
        if path.suffix.lower() == ".zip":
            inspect_zip(relative, content)
        elif path.suffix.lower() in TEXT_SUFFIXES or path.name in {"LICENSE", ".gitignore", ".dockerignore"}:
            inspect_bytes(relative, content)
    return {"candidate_files": len(paths), "zip_archives_checked": archive_count,
            "archive_members_checked": member_count, "finding_count": len(findings), "findings": findings}


def main():
    result = inspect_payload(candidate_paths())
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(1 if result["findings"] else 0)


if __name__ == "__main__":
    main()
