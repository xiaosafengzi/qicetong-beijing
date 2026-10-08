"""Reviewable numeric policy-change candidates and non-persistent impact previews.

This module only reads uploaded text. A match is not proof that a document is
official or that a rule has changed; publishing policy rules remains manual.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from .engine import review


TERMS = {
    "employees": ("职工总数", "员工总数", "员工人数"),
    "sales": ("年销售收入", "销售收入"),
    "assets": ("资产总额",),
}
PERCENT_TERMS = {
    "staff_ratio": ("科技人员",),
    "hightech": ("高新技术产品", "高新产品"),
}
COMPARATOR = r"(?:不超过|不得超过|小于等于|≤)"
NUMBER = r"([0-9][0-9,，]*(?:\.[0-9]+)?)"
UNIT = r"(亿元|万元|元|人)"


def _normalized_amount(number: str, unit: str, expected_unit: str) -> Decimal | None:
    try:
        value = Decimal(number.replace(",", "").replace("，", ""))
    except InvalidOperation:
        return None
    if value < 0 or not value.is_finite():
        return None
    if expected_unit == "人":
        return value if unit == "人" and value == value.to_integral_value() else None
    if expected_unit == "万元":
        return value * {"元": Decimal("0.0001"), "万元": Decimal(1), "亿元": Decimal(10000)}[unit] if unit != "人" else None
    return None


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _normalized_percent(number: str) -> Decimal | None:
    try:
        value = Decimal(number.replace(",", "").replace("，", "")) / 100
    except InvalidOperation:
        return None
    return value if value.is_finite() and Decimal(0) <= value <= Decimal(1) else None


def extract_threshold_candidates(asset: dict, policy: dict) -> list[dict]:
    """Find explicit upper bounds aligned to already reviewed rules.

    Terms, comparator, number and unit must appear in the same clause. This
    deliberately abstains on more complex phrasing and unrecognised concepts.
    """
    proposals = []
    seen = set()
    for rule in policy["rules"]:
        op = rule.get("op")
        if op == "lte" and len(rule.get("fields", [])) == 1:
            field = rule["fields"][0].split("_20", 1)[0]
            aliases = TERMS.get(field, ())
        elif op == "ratio":
            aliases = PERCENT_TERMS.get(rule["id"], ())
        else:
            continue
        if not aliases:
            continue
        for chunk in asset.get("chunks", []):
            for clause in re.split(r"[\r\n。；;、]", chunk["text"]):
                if not clause.strip():
                    continue
                for term in aliases:
                    if op == "lte":
                        pattern = re.compile(re.escape(term) + r"[^。；;、\r\n]{0,20}?" + COMPARATOR + r"\s*" + NUMBER + r"\s*" + UNIT)
                    else:
                        pattern = re.compile(re.escape(term) + r"[^。；;、\r\n]{0,55}?" + r"(?:比例|占比)\s*(?:不低于|至少|≥)\s*" + NUMBER + r"\s*(%)")
                    for match in pattern.finditer(clause):
                        amount = (_normalized_amount(match.group(1), match.group(2), rule["unit"])
                                  if op == "lte" else _normalized_percent(match.group(1)))
                        if amount is None:
                            continue
                        current = Decimal(str(rule["threshold"]))
                        key = (rule["id"], amount)
                        if key in seen:
                            continue
                        seen.add(key)
                        identity = f"{asset['id']}:{policy['id']}:{rule['id']}:{amount}"
                        proposals.append({
                            "id": "change-" + hashlib.sha256(identity.encode()).hexdigest()[:20],
                            "policy_id": policy["id"], "rule_id": rule["id"],
                            "rule_title": rule["title"], "field": rule["fields"][0],
                            "term": term, "comparator": "≤" if op == "lte" else "≥",
                            "candidate_threshold": _decimal_text(amount if op == "lte" else amount * 100),
                            "current_threshold": _decimal_text(current if op == "lte" else current * 100),
                            "unit": rule["unit"] if op == "lte" else "%",
                            "changed": amount != current, "quote": clause.strip()[:300],
                            "locator": chunk["locator"], "asset_id": asset["id"],
                            "state": "pending_human_verification",
                        })
    return proposals


def preview_policy_impact(asset: dict, policy: dict, companies: list[dict], as_of: date) -> dict:
    """Simulate each candidate separately; never save an inferred policy rule."""
    candidates = extract_threshold_candidates(asset, policy)
    results = []
    for candidate in candidates:
        impacts = []
        if candidate["changed"]:
            proposed = copy.deepcopy(policy)
            proposed_rule = next(r for r in proposed["rules"] if r["id"] == candidate["rule_id"])
            threshold = Decimal(candidate["candidate_threshold"])
            proposed_rule["threshold"] = float(threshold / 100 if candidate["unit"] == "%" else threshold)
            for company in companies:
                before = review(company, policy, as_of)
                after = review(company, proposed, as_of)
                old_check = next(c for c in before["checks"] if c["id"] == candidate["rule_id"])
                new_check = next(c for c in after["checks"] if c["id"] == candidate["rule_id"])
                if old_check["status"] != new_check["status"] or before["status"] != after["status"]:
                    impacts.append({
                        "company_id": company["id"], "company_name": company["name"],
                        "is_demo": company["is_demo"], "rule_before": old_check["status"],
                        "rule_after": new_check["status"], "overall_before": before["status"],
                        "overall_after": after["status"],
                    })
        results.append({**candidate, "affected_companies": impacts, "affected_count": len(impacts)})
    policy_hash = hashlib.sha256(json.dumps(policy, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {
        "asset_id": asset["id"], "policy_id": policy["id"], "as_of": str(as_of),
        "policy_sha256": policy_hash, "candidates": results,
        "checked_company_count": len(companies),
        "note": "仅为上传文件的待核验候选与假设影响；未核验文件权威性、有效期或上下文，也未修改任何生效规则。",
    }
