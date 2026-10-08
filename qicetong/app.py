from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import date
from uuid import uuid4

import httpx

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import documents, evaluation, model, ocr, policy_change, services, store
from .engine import dependency_graph, field_label, markdown_report, window_status
from .models import Company, Evidence, Fact, FactUpdate, ReviewRequest


@asynccontextmanager
async def lifespan(app):
    store.initialize()
    yield


app = FastAPI(title="企策通 · 北京", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def protect_local_mutations(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        expected = f"{request.url.scheme}://{request.headers.get('host')}"
        if origin != expected:
            return JSONResponse({"detail": "不接受跨站写入"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(KeyError)
async def not_found(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


@app.get("/api/health")
def health():
    integration = store.ROOT / "runtime/nexent/integration-results.json"
    model_result = store.ROOT / "runtime/nexent/model-results.json"
    nexent_last_verified = False
    if integration.is_file() and model_result.is_file():
        try:
            nexent_last_verified = (
                json.loads(integration.read_text(encoding="utf-8")).get("login") == "ok"
                and json.loads(model_result.read_text(encoding="utf-8")).get("state") == "ready"
            )
        except (OSError, json.JSONDecodeError):
            pass
    try:
        with httpx.Client(timeout=0.8, trust_env=False) as client:
            nexent_connected = client.get("http://127.0.0.1:5010/health/ready").json().get("status") == "ready"
    except (httpx.HTTPError, ValueError):
        nexent_connected = False
    return {"status": "ok", "version": "0.3.0", "region": "北京市", "today": str(date.today()), "mode": "local_evidence_review", "nexent_connected": nexent_connected,
            "nexent_last_verified": nexent_last_verified,
            "model_configured": model.configured()}


@app.get("/api/dashboard")
def dashboard():
    policies = store.all_items("policy")
    manifest = store.DATA / "sources" / "manifest.json"
    sources = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else json.loads((store.DATA / "sources.json").read_text(encoding="utf-8"))
    return {"companies": store.all_items("company"), "policies": [{**p, "window": window_status(p, date.today())} for p in policies],
            "assets": [{k: v for k, v in a.items() if k != "chunks"} for a in store.all_items("asset")],
            "reports": [{k: v for k, v in r.items() if k != "checks"} for r in store.all_items("report")][-30:][::-1],
            "ontology": store.all_items("ontology"), "sources": sources, "health": health()}


@app.get("/api/companies/{company_id}")
def get_company(company_id: str):
    return store.get("company", company_id)


@app.post("/api/companies")
def save_company(company: Company):
    # Import as a new snapshot instead of overwriting an existing enterprise accidentally.
    try:
        store.get("company", company.id)
        raise HTTPException(409, "企业 ID 已存在，请修改导入文件中的 id")
    except KeyError:
        pass
    store.put("company", company.model_dump())
    store.event("company_import", company.id, {"is_demo": company.is_demo})
    return company


@app.patch("/api/companies/{company_id}/facts/{field}")
def update_fact(company_id: str, field: str, body: FactUpdate):
    company = Company.model_validate(store.get("company", company_id))
    evidence = Evidence(id="manual-" + uuid4().hex, title="人工核对记录", locator=field_label(field),
                        text=f"{body.note}\n核对值：{body.value} {body.unit}；期间：{body.period}")
    company.evidence.append(evidence)
    company.facts[field] = Fact(value=body.value, unit=body.unit, period=body.period, evidence=[evidence.id], status="confirmed" if body.confirmed else "unverified")
    validated = Company.model_validate(company.model_dump())
    store.put("company", validated.model_dump())
    store.event("fact_update", company_id, {"field": field, "confirmed": body.confirmed, "evidence_id": evidence.id})
    return validated


@app.post("/api/reviews")
def create_review(body: ReviewRequest):
    return services.run_review(body.company_id, body.policy_id, str(body.as_of))


@app.get("/api/reviews/{report_id}")
def get_review(report_id: str):
    return store.get("report", report_id)


@app.get("/api/reviews/{report_id}/graph")
def graph(report_id: str):
    return dependency_graph(store.get("report", report_id))


@app.get("/api/reviews/{report_id}/report.md")
def download_report(report_id: str):
    return PlainTextResponse(markdown_report(store.get("report", report_id)), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="review-{report_id[:12]}.md"'})


@app.get("/api/compare")
def compare(old: str = "sme-bj-2025", new: str = "sme-bj-2026", as_of: date | None = None):
    return services.compare_versions(old, new, str(as_of) if as_of else None)


@app.get("/api/policy-change-preview")
def policy_change_preview(asset_id: str, policy_id: str, as_of: date | None = None):
    asset = store.get("asset", asset_id)
    if asset["purpose"] != "policy":
        raise HTTPException(400, "只有政策材料可以进行规则变化预览")
    policy = store.get("policy", policy_id)
    return policy_change.preview_policy_impact(asset, policy, store.all_items("company"), as_of or date.today())


@app.post("/api/assets")
async def upload_asset(file: UploadFile = File(...), purpose: str = Form("company")):
    if purpose not in ("company", "policy"):
        raise HTTPException(400, "无效资料用途")
    raw = await file.read(documents.MAX_BYTES + 1)
    await file.close()
    return documents.ingest(file.filename or "upload.txt", raw, purpose)


@app.get("/api/assets/{asset_id}")
def asset(asset_id: str):
    return store.get("asset", asset_id)


@app.post("/api/assets/{asset_id}/ocr")
def local_ocr(asset_id: str):
    return ocr.recognize_asset(asset_id)


@app.post("/api/assets/{asset_id}/model-extract")
async def model_extract(asset_id: str):
    try:
        return await model.extract_asset(asset_id)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "模型服务暂时无法连接，请检查网络和配置后重试") from exc


@app.get("/api/assets/{asset_id}/file")
def original_asset(asset_id: str):
    a = store.get("asset", asset_id)
    return FileResponse(store.runtime_dir() / "uploads" / f"{a['id']}{a['suffix']}", filename=a["filename"], media_type="application/octet-stream")


class AcceptBody(BaseModel):
    company_id: str | None = None
    visual_verified: bool = False


@app.post("/api/assets/{asset_id}/proposals/{proposal_id}/accept")
def accept(asset_id: str, proposal_id: str, body: AcceptBody):
    return services.accept_proposal(asset_id, proposal_id, body.company_id, body.visual_verified)


@app.get("/api/search")
def search(q: str = "", limit: int = 10):
    return {"query": q, "method": "local_lexical", "results": documents.search(q[:500], min(max(limit, 1), 30))}


@app.get("/api/events")
def events():
    return store.events()


@app.get("/api/evaluation")
def evaluation_results():
    return evaluation.latest_summary()


@app.get("/api/evaluation/public-notice")
def public_notice_evaluation_results():
    return evaluation.latest_public_notice_summary()


@app.get("/api/template/company.json")
def template():
    return FileResponse(store.DATA / "company-template.json", filename="company-template.json", media_type="application/json")


@app.get("/api/template/financial.csv")
def csv_template():
    return PlainTextResponse("\ufeff字段,数值,单位,期间\nrd_2024,220,万元,2024\n", media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="financial-template.csv"'})


@app.get("/api/sources/{source_id}")
def source_text(source_id: str):
    sources = json.loads((store.DATA / "sources.json").read_text(encoding="utf-8"))
    if source_id not in {s["id"] for s in sources}:
        raise HTTPException(404, "来源不存在")
    path = store.DATA / "sources" / f"{source_id}.txt"
    if not path.exists():
        raise HTTPException(404, "尚未缓存该来源，请查看官方原文")
    return PlainTextResponse(path.read_text(encoding="utf-8"))


app.mount("/", StaticFiles(directory=store.ROOT / "web", html=True), name="web")
