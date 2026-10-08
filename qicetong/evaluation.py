"""Reproducible challenge-suite evaluation for the deterministic review engine and LLM ablation."""
from __future__ import annotations

import copy
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .engine import review


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "data/evaluation_cases.json"
RESULTS_PATH = ROOT / "artifacts/evaluation-results.json"
PUBLIC_RESULTS_PATH = ROOT / "artifacts/public-notice-results.json"
PUBLIC_SUMMARY_PATH = ROOT / "artifacts/public-notice-summary.json"
PUBLIC_RECORDS_PATH = ROOT / "data/public_case_records_2026.jsonl"
VALID_STATUSES = {"pass", "fail", "unknown", "conflict"}


def _load_static_data() -> tuple[dict[str, dict], dict[str, dict], list[dict]]:
    companies = {
        item["id"]: item
        for item in json.loads((ROOT / "data/companies.json").read_text(encoding="utf-8"))
    }
    policies = {
        item["id"]: item
        for item in json.loads((ROOT / "data/policies.json").read_text(encoding="utf-8"))
    }
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return companies, policies, cases


def _mutate(document: dict, mutation: dict) -> None:
    parts = mutation["path"].split(".")
    target: dict[str, Any] = document
    for part in parts[:-1]:
        target = target[part]
    if mutation.get("delete"):
        target.pop(parts[-1], None)
    else:
        target[parts[-1]] = mutation.get("value")


def materialize_case(case: dict, companies: dict[str, dict], policies: dict[str, dict]) -> tuple[dict, dict]:
    company = copy.deepcopy(companies[case["base_company_id"]])
    for mutation in case.get("mutations", []):
        _mutate(company, mutation)
    return company, policies[case["policy_id"]]


def _score_prediction(case: dict, status: str | None, missing_fields: list[str] | None) -> dict:
    status_correct = status == case["expected_status"]
    expected_missing = case.get("expected_missing_fields")
    missing_correct = None if expected_missing is None else set(missing_fields or []) == set(expected_missing)
    exact = status_correct and missing_correct is not False
    return {"status_correct": status_correct, "missing_fields_correct": missing_correct, "exact": exact}


def _summarize(rows: list[dict]) -> dict:
    total = len(rows)
    status_correct = sum(bool(row["score"]["status_correct"]) for row in rows)
    exact = sum(bool(row["score"]["exact"]) for row in rows)
    missing_rows = [row for row in rows if row["score"]["missing_fields_correct"] is not None]
    missing_correct = sum(bool(row["score"]["missing_fields_correct"]) for row in missing_rows)
    categories: dict[str, dict] = {}
    for row in rows:
        bucket = categories.setdefault(row["category"], {"cases": 0, "exact": 0})
        bucket["cases"] += 1
        bucket["exact"] += int(row["score"]["exact"])
    for bucket in categories.values():
        bucket["accuracy"] = round(bucket["exact"] / bucket["cases"], 4)
    return {
        "case_count": total,
        "status_correct": status_correct,
        "status_accuracy": round(status_correct / total, 4) if total else 0.0,
        "exact_case_count": exact,
        "exact_case_accuracy": round(exact / total, 4) if total else 0.0,
        "missing_field_cases": len(missing_rows),
        "missing_field_exact": missing_correct,
        "missing_field_accuracy": round(missing_correct / len(missing_rows), 4) if missing_rows else None,
        "categories": categories,
    }


def run_engine_benchmark() -> dict:
    companies, policies, cases = _load_static_data()
    rows = []
    started = time.perf_counter()
    for case in cases:
        company, policy = materialize_case(case, companies, policies)
        case_started = time.perf_counter()
        report = review(company, policy, date.fromisoformat(case["as_of"]))
        check = next(item for item in report["checks"] if item["id"] == case["rule_id"])
        rows.append({
            "id": case["id"],
            "category": case["category"],
            "description": case["description"],
            "rule_id": case["rule_id"],
            "expected_status": case["expected_status"],
            "predicted_status": check["status"],
            "expected_missing_fields": case.get("expected_missing_fields"),
            "predicted_missing_fields": check.get("missing_fields", []),
            "reasoning": check.get("reasoning"),
            "latency_ms": round((time.perf_counter() - case_started) * 1000, 3),
            "score": _score_prediction(case, check["status"], check.get("missing_fields")),
        })
    return {
        "name": "企策通确定性证据规则引擎",
        "engine_version": "0.2.0",
        "summary": _summarize(rows),
        "total_latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "cases": rows,
    }


def _llm_case_payload(case: dict, company: dict, policy: dict) -> dict:
    rule = next(item for item in policy["rules"] if item["id"] == case["rule_id"])
    facts = {key: company.get("facts", {}).get(key, {"missing": True}) for key in rule["fields"]}
    return {
        "as_of": case["as_of"],
        "rule": {key: rule.get(key) for key in ("id", "title", "quote", "clause", "op", "fields", "expected", "threshold", "unit", "period") if key in rule},
        "facts": facts,
    }


def run_llm_baseline(model: str = "qwen3:8b", base_url: str = "http://127.0.0.1:11434") -> dict:
    """Evaluate an LLM-only ablation on the same structured facts and policy rules."""
    companies, policies, cases = _load_static_data()
    rows = []
    started = time.perf_counter()
    with httpx.Client(base_url=base_url, timeout=120, trust_env=False) as client:
        for case in cases:
            company, policy = materialize_case(case, companies, policies)
            payload = _llm_case_payload(case, company, policy)
            prompt = (
                "你是企业政策材料预审员。只根据给定规则和事实，判断该单项检查。"
                "事实缺失、未确认、期间或单位错误、分母为零时返回 unknown；材料状态 conflict 返回 conflict；"
                "满足返回 pass，不满足返回 fail。不要假定缺失值。只输出 JSON："
                '{"status":"pass|fail|unknown|conflict","missing_fields":[],"reason":"简短说明"}\n'
                + json.dumps(payload, ensure_ascii=False)
            )
            case_started = time.perf_counter()
            predicted_status = None
            predicted_missing: list[str] = []
            reason = ""
            error = None
            try:
                response = client.post("/api/chat", json={
                    "model": model,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "options": {"temperature": 0, "num_predict": 256},
                    "messages": [{"role": "user", "content": prompt}],
                })
                response.raise_for_status()
                parsed = json.loads(response.json()["message"]["content"])
                predicted_status = parsed.get("status")
                predicted_missing = parsed.get("missing_fields") or []
                reason = str(parsed.get("reason") or "")
                if predicted_status not in VALID_STATUSES:
                    raise ValueError(f"invalid status: {predicted_status}")
            except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                predicted_status = None
                predicted_missing = []
            rows.append({
                "id": case["id"],
                "category": case["category"],
                "description": case["description"],
                "rule_id": case["rule_id"],
                "expected_status": case["expected_status"],
                "predicted_status": predicted_status,
                "expected_missing_fields": case.get("expected_missing_fields"),
                "predicted_missing_fields": predicted_missing,
                "reasoning": reason,
                "error": error,
                "latency_ms": round((time.perf_counter() - case_started) * 1000, 3),
                "score": _score_prediction(case, predicted_status, predicted_missing),
            })
    return {
        "name": "Qwen3 8B 单模型规则判断基线",
        "model": model,
        "summary": _summarize(rows),
        "total_latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "cases": rows,
    }


def evaluate(include_llm_baseline: bool = False, model: str = "qwen3:8b") -> dict:
    result = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {
            "name": "企策通困难案例评测集",
            "path": str(CASES_PATH.relative_to(ROOT)).replace("\\", "/"),
            "data_type": "基于公开政策规则和模拟企业材料构造",
            "leakage_note": "评测案例不写入运行数据库；每次从静态基准数据复制并施加单一或成组扰动。",
        },
        "engine": run_engine_benchmark(),
        "llm_baseline": None,
    }
    if include_llm_baseline:
        result["llm_baseline"] = run_llm_baseline(model=model)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def latest_summary() -> dict:
    if not RESULTS_PATH.is_file():
        return evaluate(include_llm_baseline=False)
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def evaluate_public_notice(records_path: Path | None = None, output_path: Path | None = None) -> dict:
    """Measure safe abstention on actual public notices with no application facts.

    The public label is only proposed-list membership, never eligibility.
    These records are not inserted into the enterprise store.
    """
    policy = next(item for item in json.loads((ROOT / "data/policies.json").read_text(encoding="utf-8")) if item["id"] == "sme-bj-2026")
    path = records_path or PUBLIC_RECORDS_PATH
    if not path.is_file():
        raise ValueError("公开版不附企业名册。重跑此评测须先按 docs/data-publication.md 准备本地公开记录；历史汇总可在评测中心查看。")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for record in records:
        observed = record["observed_facts"]
        company = {
            "id": record["record_id"], "name": observed["company_name"],
            "district": observed["district"], "industry": "未观察到", "is_demo": False,
            "note": "仅来自公开拟入库公示；无申报材料授权", "facts": {}, "evidence": [],
        }
        report = review(company, policy, date.fromisoformat(record["publication_date"]))
        rows.append({
            "record_id": record["record_id"], "source_serial": record["source_serial"],
            "source_url": record["source_document_url"], "company_name": observed["company_name"],
            "public_label": "拟入库公示名单出现", "review_status": report["status"],
            "unsupported_pass_claim": report["status"] == "pass",
            "missing_field_count": len(report["missing_fields"]),
        })
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {"name": "北京市2026年第一批拟入库科技型中小企业公开记录", "path": "data/public_case_records_2026.jsonl" if path == PUBLIC_RECORDS_PATH else "external_test_fixture",
                    "type": "public_notice_only", "authorized_company_case_count": 0,
                    "claim_boundary": "只验证资料不足时不捏造资格；无真实申报材料与资格金标准，不能计算预审准确率。"},
        "summary": {"record_count": len(rows), "distinct_company_count": len({r["company_name"] for r in rows}),
                    "district_count": len({r["observed_facts"]["district"] for r in records}),
                    "abstained_count": sum(r["review_status"] in ("unknown", "conflict") for r in rows),
                    "unsupported_pass_claim_count": sum(r["unsupported_pass_claim"] for r in rows)},
        "rows": rows,
    }
    destination = output_path or PUBLIC_RESULTS_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def latest_public_notice_summary() -> dict:
    if PUBLIC_RESULTS_PATH.is_file():
        return json.loads(PUBLIC_RESULTS_PATH.read_text(encoding="utf-8"))
    if PUBLIC_SUMMARY_PATH.is_file():
        return json.loads(PUBLIC_SUMMARY_PATH.read_text(encoding="utf-8"))
    if PUBLIC_RECORDS_PATH.is_file():
        return evaluate_public_notice()
    return {"available": False, "rows": [],
            "dataset": {"type": "not_loaded", "authorized_company_case_count": 0,
                        "claim_boundary": "本环境未载入公开企业记录或历史汇总；此处没有新的评测结果。"},
            "summary": {"record_count": 0, "distinct_company_count": 0, "district_count": 0,
                        "abstained_count": 0, "unsupported_pass_claim_count": 0}}
