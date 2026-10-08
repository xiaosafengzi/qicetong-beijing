"""Cache official public policy pages, preserving exact bytes, hashes and retrieval provenance."""
from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sources"
OUT.mkdir(exist_ok=True)


def fetch(source):
    record = dict(source)
    try:
        response = httpx.get(source["url"], timeout=35, follow_redirects=True, headers={"User-Agent": "Qicetong-Research/0.1"})
        response.raise_for_status()
        body = response.content
        soup = BeautifulSoup(body, "html.parser")
        for el in soup(["script", "style", "nav", "footer"]):
            el.decompose()
        article = soup.select_one(".TRS_Editor, .trs_editor_view, .view.TRS_UEDITOR, .article-content, #zoom") or soup
        text = article.get_text("\n", strip=True)
        if len(text) < 100:
            raise ValueError("页面正文过短，可能未成功抓取")
        (OUT / f"{source['id']}.html").write_bytes(body)
        (OUT / f"{source['id']}.txt").write_text(text, encoding="utf-8")
        record.update(status="cached", retrieved_at=datetime.now(timezone.utc).isoformat(),
                      sha256=hashlib.sha256(body).hexdigest(), text_chars=len(text), final_url=str(response.url))
    except Exception as exc:
        record.update(status="fetch_failed", error=str(exc))
    return record


if __name__ == "__main__":
    sources = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    records = list(ThreadPoolExecutor(max_workers=3).map(fetch, sources))
    (OUT / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in records:
        print(item["id"], item["status"], item.get("text_chars", item.get("error")))
