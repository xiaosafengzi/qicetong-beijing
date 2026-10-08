"""Exercise actual local OCR on a clearly synthetic image in an isolated runtime."""
import io
import json
import os
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
os.sys.path.insert(0, str(ROOT))

from qicetong import documents, ocr, store


def main():
    with tempfile.TemporaryDirectory(prefix="qicetong-ocr-") as temporary:
        os.environ["QCT_RUNTIME"] = temporary
        store.initialize()
        image = Image.new("RGB", (1400, 220), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 64)
        draw.text((30, 55), "职工总数: 80, 人, 2025", font=font, fill="black")
        stream = io.BytesIO()
        image.save(stream, "PNG")
        asset = documents.ingest("模拟人员记录.png", stream.getvalue(), "company")
        draft = ocr.recognize_asset(asset["id"])
        result = {
            "sample": "synthetic_image",
            "status": draft["status"],
            "line_count": len(draft["chunks"]),
            "recognized_lines": [chunk["text"] for chunk in draft["chunks"]],
            "proposal_fields": [proposal.get("field") for proposal in draft["proposals"]],
            "visual_verified": draft["ocr"]["verified"],
        }
        output = ROOT / "artifacts" / "ocr-smoke-results.json"
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
