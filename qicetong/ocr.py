"""Optional local OCR. Recognition is a draft; source-image verification is mandatory."""
from __future__ import annotations

from functools import lru_cache

from . import documents, store


@lru_cache(maxsize=1)
def _engine():
    try:
        from rapidocr import RapidOCR
    except ImportError as exc:
        raise ValueError("本地 OCR 尚未安装，请安装 requirements-ocr.txt") from exc
    return RapidOCR()


def recognize_asset(asset_id: str) -> dict:
    asset = store.get("asset", asset_id)
    if asset["suffix"] not in (".png", ".jpg", ".jpeg"):
        raise ValueError("本地 OCR 当前只处理 PNG/JPG；扫描 PDF 请先逐页转成图片")
    if asset["status"] == "ocr_draft":
        return asset
    path = store.runtime_dir() / "uploads" / f"{asset['id']}{asset['suffix']}"
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise ValueError("本地 OCR 尚未安装，请安装 requirements-ocr.txt") from exc
    try:
        with Image.open(path) as image:
            width, height = image.size
            if width * height > 24_000_000 or width > 8000 or height > 8000:
                raise ValueError("图片分辨率过大，请裁剪或缩小后重新上传")
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("图片文件无法解码") from exc

    result = _engine()(str(path))
    texts = result.txts or ()
    boxes = result.boxes if result.boxes is not None else ()
    scores = result.scores if result.scores is not None else ()
    chunks = []
    for index, raw_text in enumerate(texts[:500], 1):
        recognized = str(raw_text).strip()
        if not recognized:
            continue
        box = boxes[index - 1] if index - 1 < len(boxes) else None
        if box is not None:
            xs = [int(point[0]) for point in box]
            ys = [int(point[1]) for point in box]
            locator = f"图片第{index}行，框({min(xs)},{min(ys)})-({max(xs)},{max(ys)})"
        else:
            locator = f"图片第{index}行"
        score = float(scores[index - 1]) if index - 1 < len(scores) else None
        chunks.append({"locator": locator, "text": recognized, "ocr_score": score})
    if not chunks:
        raise ValueError("未识别到文字；请检查图片清晰度，原件仍保留")
    proposals = documents.field_proposals(chunks) if asset["purpose"] == "company" else documents.ontology_proposals(chunks)
    for proposal in proposals:
        proposal["method"] = "local_ocr_unverified"
    asset["chunks"] = chunks
    asset["proposals"] = [{"id": f"{asset_id}-ocr-{i}", **proposal} for i, proposal in enumerate(proposals)]
    asset["status"] = "ocr_draft"
    asset["ocr"] = {"engine": "RapidOCR", "at": store.now(), "line_count": len(chunks),
                    "candidate_count": len(proposals), "verified": False}
    store.put("asset", asset)
    store.event("local_ocr", asset_id, {"line_count": len(chunks), "candidate_count": len(proposals), "verified": False})
    return asset
