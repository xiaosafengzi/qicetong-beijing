from __future__ import annotations

from datetime import date
from uuid import uuid4

from . import store
from .engine import compare_policies, dependency_graph, review
from .models import Company, Evidence, Fact


def run_review(company_id: str, policy_id: str, as_of: str | None = None) -> dict:
    report = review(store.get("company", company_id), store.get("policy", policy_id), date.fromisoformat(as_of) if as_of else date.today())
    store.put("report", report)
    store.event("review", report["id"], {"company_id": company_id, "policy_id": policy_id, "fingerprint": report["fingerprint"], "status": report["status"]})
    return report


def compare_versions(old_id="sme-bj-2025", new_id="sme-bj-2026", as_of: str | None = None):
    return compare_policies(store.get("policy", old_id), store.get("policy", new_id), store.all_items("company"), date.fromisoformat(as_of) if as_of else date.today())


def accept_proposal(asset_id: str, proposal_id: str, company_id: str | None = None, visual_verified: bool = False) -> dict:
    asset = store.get("asset", asset_id)
    proposal = next((p for p in asset["proposals"] if p["id"] == proposal_id), None)
    if not proposal:
        raise KeyError("找不到候选")
    if proposal["state"] != "pending":
        raise ValueError("该候选已处理")
    if asset["status"] == "ocr_draft" and not visual_verified:
        raise ValueError("图片识别草稿须先对照原图核实，再确认候选")
    if asset["purpose"] == "company":
        if not company_id:
            raise ValueError("请选择企业")
        company = Company.model_validate(store.get("company", company_id))
        evidence = Evidence(id="ev-" + uuid4().hex, title=asset["filename"], locator=proposal["locator"], text=proposal["quote"], asset_id=asset_id)
        existing = company.facts.get(proposal["field"])
        # Conflict is preserved instead of silently replacing a previously confirmed value.
        differs = existing and (existing.value != proposal["value"] or existing.unit != proposal["unit"] or existing.period != proposal["period"])
        if differs:
            existing.status = "conflict"
            existing.evidence.append(evidence.id)
        else:
            company.facts[proposal["field"]] = Fact(value=proposal["value"], unit=proposal["unit"], period=proposal["period"], status="confirmed", evidence=[evidence.id] + (existing.evidence if existing else []))
        company.evidence.append(evidence)
        store.put("company", Company.model_validate(company.model_dump()).model_dump())
    else:
        store.put("ontology", {"id": proposal["id"], **proposal, "state": "accepted", "asset_id": asset_id, "accepted_at": store.now()})
    proposal["state"] = "accepted"
    store.put("asset", asset)
    store.event("proposal_accept", proposal_id, {"asset_id": asset_id, "company_id": company_id, "purpose": asset["purpose"]})
    return proposal
