"""Policy updates stay reviewable and never overwrite approved rules."""
from datetime import date

from fastapi.testclient import TestClient

from qicetong import documents, policy_change, store
from qicetong.app import app


def test_official_clause_aligns_three_existing_thresholds(isolated_store):
    official_clause = "（二）职工总数不超过500人、年销售收入不超过2亿元、资产总额不超过2亿元。"
    asset = documents.ingest("评价办法.txt", official_clause.encode(), "policy")
    policy = store.get("policy", "sme-bj-2026")
    result = policy_change.preview_policy_impact(asset, policy, store.all_items("company"), date(2026, 9, 22))
    by_rule = {item["rule_id"]: item for item in result["candidates"]}
    assert {"staff", "sales", "assets"} <= by_rule.keys()
    assert by_rule["staff"]["candidate_threshold"] == "500"
    assert by_rule["sales"]["candidate_threshold"] == "20000"
    assert by_rule["assets"]["candidate_threshold"] == "20000"
    assert all(not item["changed"] for item in by_rule.values())
    assert all(item["affected_count"] == 0 for item in by_rule.values())


def test_hypothetical_update_previews_impact_without_publishing(isolated_store):
    original = store.get("policy", "sme-bj-2026")
    asset = documents.ingest("假设通知.txt", "职工总数不超过50人。".encode(), "policy")
    with TestClient(app) as client:
        response = client.get("/api/policy-change-preview", params={
            "asset_id": asset["id"], "policy_id": original["id"], "as_of": "2026-09-22",
        })
    assert response.status_code == 200
    candidate = next(x for x in response.json()["candidates"] if x["rule_id"] == "staff")
    assert candidate["changed"] and candidate["affected_count"] >= 1
    assert any(x["rule_before"] != x["rule_after"] for x in candidate["affected_companies"])
    assert store.get("policy", original["id"]) == original


def test_official_percentage_clause_and_hypothetical_increase(isolated_store):
    policy = store.get("policy", "hnte-bj-2026")
    official = documents.ingest("高企条款.txt", "科技人员占企业当年职工总数的比例不低于10%；高新技术产品(服务)收入占企业同期总收入的比例不低于60%。".encode(), "policy")
    aligned = {x["rule_id"]: x for x in policy_change.extract_threshold_candidates(official, policy)}
    assert aligned["staff_ratio"]["candidate_threshold"] == "10"
    assert aligned["hightech"]["candidate_threshold"] == "60"
    assert not aligned["staff_ratio"]["changed"] and not aligned["hightech"]["changed"]

    hypothetical = documents.ingest("比例假设.txt", "科技人员占企业当年职工总数的比例不低于50%。".encode(), "policy")
    result = policy_change.preview_policy_impact(hypothetical, policy, store.all_items("company"), date(2026, 9, 22))
    candidate = next(x for x in result["candidates"] if x["rule_id"] == "staff_ratio")
    assert candidate["changed"]
    assert candidate["affected_count"] >= 1
    assert store.get("policy", policy["id"]) == policy


def test_ambiguous_or_incompatible_thresholds_abstain(isolated_store):
    text = "职工总数建议控制在300人左右。资产总额不超过400人。销售收入可能不超过两亿元。"
    asset = documents.ingest("模糊政策.txt", text.encode(), "policy")
    policy = store.get("policy", "sme-bj-2026")
    assert policy_change.extract_threshold_candidates(asset, policy) == []
