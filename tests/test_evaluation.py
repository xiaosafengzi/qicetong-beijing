import json

import pytest

from qicetong import evaluation
from qicetong.evaluation import evaluate_public_notice, run_engine_benchmark


def test_challenge_suite_is_complete_and_reproducible():
    result = run_engine_benchmark()
    summary = result["summary"]
    assert summary["case_count"] == 15
    assert summary["status_accuracy"] == 1.0
    assert summary["exact_case_accuracy"] == 1.0
    assert summary["missing_field_accuracy"] == 1.0
    assert len(summary["categories"]) >= 10


def test_benchmark_does_not_mutate_static_company_data():
    first = run_engine_benchmark()
    second = run_engine_benchmark()
    assert [(x["id"], x["predicted_status"]) for x in first["cases"]] == [
        (x["id"], x["predicted_status"]) for x in second["cases"]
    ]


def test_public_notice_is_not_treated_as_authorized_application_data(tmp_path):
    records = [{"record_id": f"SYN-{index}", "source_serial": index, "publication_date": "2026-07-09",
                "source_document_url": "https://example.invalid/synthetic-notice",
                "observed_facts": {"company_name": f"合成企业{index}", "district": "模拟区"}} for index in range(1, 3)]
    fixture = tmp_path / "synthetic.jsonl"
    fixture.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records), encoding="utf-8")
    result = evaluate_public_notice(fixture, tmp_path / "results.json")
    summary = result["summary"]
    assert summary["record_count"] == 2
    assert summary["distinct_company_count"] == 2
    assert summary["unsupported_pass_claim_count"] == 0
    assert summary["abstained_count"] == 2
    assert result["dataset"]["authorized_company_case_count"] == 0


def test_public_clone_uses_history_without_redistributing_rows(tmp_path, monkeypatch):
    summary = json.loads(evaluation.PUBLIC_SUMMARY_PATH.read_text(encoding="utf-8"))
    monkeypatch.setattr(evaluation, "PUBLIC_RESULTS_PATH", tmp_path / "no-raw-results.json")
    monkeypatch.setattr(evaluation, "PUBLIC_RECORDS_PATH", tmp_path / "no-records.jsonl")
    result = evaluation.latest_public_notice_summary()
    assert result == summary
    assert result["historical_summary_only"] and result["records_distributed"] is False
    assert result["rows"] == [] and result["summary"]["record_count"] == 50
    with pytest.raises(ValueError, match="公开版不附企业名册"):
        evaluate_public_notice()


def test_missing_optional_public_data_does_not_break_evaluation_page(tmp_path, monkeypatch):
    for name in ("PUBLIC_RESULTS_PATH", "PUBLIC_SUMMARY_PATH", "PUBLIC_RECORDS_PATH"):
        monkeypatch.setattr(evaluation, name, tmp_path / name)
    result = evaluation.latest_public_notice_summary()
    assert result["available"] is False and result["summary"]["record_count"] == 0
