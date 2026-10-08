"""Install verified standalone Ollama on D: and prepare a local Qwen model."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx


ROOT = Path(r"D:\NexentData\ollama")
APP = ROOT / "app"
ARCHIVE = ROOT / "ollama-windows-amd64.zip"
PARTIAL = ARCHIVE.with_suffix(".zip.part")
PARTS = 6
ASSET = "ollama-windows-amd64.zip"
MODEL = "qwen3:8b"


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60, connect=15)) as client:
        response = client.get("https://api.github.com/repos/ollama/ollama/releases/latest")
        response.raise_for_status()
        release = response.json()
        asset = next(x for x in release["assets"] if x["name"] == ASSET)
        expected_digest = asset["digest"].split(":", 1)[1]
        expected_size = asset["size"]
        print(f"Ollama release: {release['tag_name']}; archive: {expected_size / 1e9:.2f} GB", flush=True)
        if not ARCHIVE.is_file() or ARCHIVE.stat().st_size != expected_size:
            segment_size = (expected_size + PARTS - 1) // PARTS
            if PARTIAL.exists() and not (ROOT / f"{ASSET}.part.0").exists():
                PARTIAL.replace(ROOT / f"{ASSET}.part.0")

            def fetch_segment(index: int):
                start = index * segment_size
                end = min(expected_size, start + segment_size) - 1
                path = ROOT / f"{ASSET}.part.{index}"
                have = path.stat().st_size if path.exists() else 0
                if have == end - start + 1:
                    return path
                print(f"Ollama segment {index + 1}/{PARTS} requesting bytes {start + have}-{end}", flush=True)
                with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(45, connect=15)) as segment_client:
                    with segment_client.stream("GET", asset["browser_download_url"], headers={"Range": f"bytes={start + have}-{end}"}) as stream:
                        stream.raise_for_status()
                        expected_range = f"bytes {start + have}-{end}/{expected_size}"
                        if stream.status_code != 206 or stream.headers.get("content-range") != expected_range:
                            raise RuntimeError(f"Unexpected HTTP range response for segment {index}")
                        print(f"Ollama segment {index + 1}/{PARTS} connected", flush=True)
                        last_report = have
                        with path.open("ab") as output:
                            for chunk in stream.iter_bytes(chunk_size=64 * 1024):
                                output.write(chunk)
                                have += len(chunk)
                                if have - last_report >= 16 * 1024 * 1024:
                                    print(f"Ollama segment {index + 1}/{PARTS}: {have / 1e6:.0f} MB", flush=True)
                                    last_report = have
                if path.stat().st_size != end - start + 1:
                    raise RuntimeError(f"Incomplete Ollama segment {index}")
                print(f"Ollama segment {index + 1}/{PARTS} complete", flush=True)
                return path

            with ThreadPoolExecutor(max_workers=PARTS) as pool:
                segments = list(pool.map(fetch_segment, range(PARTS)))
            with PARTIAL.open("wb") as output:
                for path in segments:
                    with path.open("rb") as source:
                        shutil.copyfileobj(source, output, length=1024 * 1024)
            if PARTIAL.stat().st_size != expected_size:
                raise RuntimeError("Assembled Ollama archive has unexpected size")
            PARTIAL.replace(ARCHIVE)
    with ARCHIVE.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    if digest != expected_digest:
        raise RuntimeError("Ollama archive SHA-256 mismatch; refusing extraction")
    print("Ollama archive SHA-256 verified.", flush=True)
    APP.mkdir(exist_ok=True)
    if not (APP / "ollama.exe").is_file():
        with zipfile.ZipFile(ARCHIVE) as z:
            for info in z.infolist():
                target = (APP / info.filename).resolve()
                if not target.is_relative_to(APP.resolve()):
                    raise RuntimeError(f"Unsafe archive path: {info.filename}")
            z.extractall(APP)
    exe = next(APP.rglob("ollama.exe"), None)
    if exe is None:
        raise RuntimeError("Ollama binary missing after extraction")
    print("Ollama binary:", exe, flush=True)
    metadata = {"version": release["tag_name"], "asset_sha256": digest, "executable": str(exe), "model": MODEL}
    (ROOT / "installation.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
