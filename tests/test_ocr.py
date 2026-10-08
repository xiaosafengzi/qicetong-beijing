"""OCR text remains a draft until someone compares it with the original image."""
import io
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from qicetong import ocr
from qicetong.app import app


def test_local_ocr_requires_visual_verification_before_fact_acceptance(isolated_store, monkeypatch):
    image_lib = pytest.importorskip("PIL.Image")
    image = image_lib.new("RGB", (400, 80), "white")
    raw = io.BytesIO()
    image.save(raw, format="PNG")

    class FakeEngine:
        def __call__(self, path):
            return SimpleNamespace(txts=("职工总数:80,人,2025",), scores=(0.98,),
                                   boxes=[[(1, 1), (390, 1), (390, 50), (1, 50)]])

    monkeypatch.setattr(ocr, "_engine", lambda: FakeEngine())
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("人员.png", raw.getvalue(), "image/png")},
                            data={"purpose": "company"}).json()
        assert asset["status"] == "pending_ocr"
        draft = client.post(f"/api/assets/{asset['id']}/ocr").json()
        assert draft["status"] == "ocr_draft" and draft["ocr"]["verified"] is False
        assert draft["chunks"][0]["ocr_score"] == 0.98
        assert draft["proposals"][0]["field"] == "employees"
        route = f"/api/assets/{asset['id']}/proposals/{draft['proposals'][0]['id']}/accept"
        assert client.post(route, json={"company_id": "demo-01"}).status_code == 400
        assert client.post(route, json={"company_id": "demo-01", "visual_verified": True}).status_code == 200


def test_invalid_image_cannot_be_ocr_draft(isolated_store):
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("broken.png", b"not an image", "image/png")},
                            data={"purpose": "company"}).json()
        assert client.post(f"/api/assets/{asset['id']}/ocr").status_code == 400
