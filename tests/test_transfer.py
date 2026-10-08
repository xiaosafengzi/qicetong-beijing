"""The generic evidence engine can run an isolated synthetic industry template."""
from datetime import date

from qicetong import store
from qicetong.engine import dependency_graph, review
from qicetong.mcp_server import review_enterprise
from qicetong.transfer import load_manufacturing_template, seed_manufacturing_template


def test_manufacturing_template_reuses_evidence_review_without_beijing_mutation(isolated_store):
    beijing_policy = store.get("policy", "sme-bj-2026")
    policy, examples = seed_manufacturing_template()
    assert store.get("policy", "sme-bj-2026") == beijing_policy
    assert policy["source"]["authority"] == "演示模板，无外部权威效力"

    for company, expected in examples:
        report = review(store.get("company", company["id"]), store.get("policy", policy["id"]), date(2026, 9, 22))
        graph = dependency_graph(report)
        assert report["status"] == expected
        assert len(report["checks"]) == 3
        assert graph["nodes"] and graph["edges"]

    unknown = review(examples[-1][0], policy, date(2026, 9, 22))
    assert any(check["status"] == "unknown" for check in unknown["checks"])
    tool_result = review_enterprise("mfg-unknown", policy["id"], "2026-09-22")
    assert tool_result["status"] == "unknown"
    assert tool_result["findings"] and tool_result["detail_tools"]["evidence_graph"]


def test_manufacturing_fixture_is_explicitly_synthetic():
    policy, examples = load_manufacturing_template()
    assert policy["state"] == "demo"
    assert all(company["is_demo"] for company, _ in examples)
    assert policy["source"]["url"] == ""
