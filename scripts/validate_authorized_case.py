from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path


CASE_ID = re.compile(r"^BJC-\d{3}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
CREDIT_CODE = re.compile(r"(?<![0-9A-Z])[0-9A-HJ-NPQRTUWXY]{18}(?![0-9A-Z])")
FORBIDDEN_KEYS = {
    "company_name", "unified_social_credit_code", "legal_representative", "address",
    "phone", "email", "bank_account", "employee_name", "id_card", "customer_name",
    "supplier_name",
}
ALLOWED_STATUSES = {"confirmed", "unverified", "conflict", "missing", "not_applicable"}
ALLOWED_RESULTS = {"pass", "fail", "unknown", "conflict"}


def walk(value, path="$"):
    if isinstance(value, dict):
        for key, item in value.items():
            yield f"{path}.{key}", key, item
            yield from walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{path}[{index}]")


def validate(payload: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["案例文件顶层必须是 JSON 对象"]
    required = {"case_id", "authorization", "profile", "facts", "evidence", "gold_standard", "provenance"}
    missing = sorted(required - payload.keys())
    if missing:
        errors.append(f"缺少顶层字段：{', '.join(missing)}")
        return errors

    if not CASE_ID.fullmatch(str(payload["case_id"])):
        errors.append("case_id 必须使用 BJC-001 格式")

    authorization = payload.get("authorization")
    if not isinstance(authorization, dict):
        errors.append("authorization 必须是对象")
        authorization = {}
    if authorization.get("internal_evaluation") is not True:
        errors.append("internal_evaluation 必须获得明确授权")
    if not SHA256.fullmatch(str(authorization.get("document_sha256", ""))):
        errors.append("授权文件 document_sha256 无效")
    for scope in ("defense_demo", "open_source"):
        if not isinstance(authorization.get(scope), bool):
            errors.append(f"authorization.{scope} 必须明确填写 true 或 false")
    if not authorization.get("withdrawal_contact"):
        errors.append("缺少授权撤回联系方式")
    try:
        signed_date = date.fromisoformat(str(authorization.get("signed_date")))
        if signed_date > date.today():
            errors.append("授权签署日期不能晚于今天")
    except ValueError:
        signed_date = None
        errors.append("signed_date 必须是 YYYY-MM-DD")
    try:
        expires_at = date.fromisoformat(str(authorization.get("expires_at")))
        if expires_at < date.today():
            errors.append("授权已过期")
        if signed_date and expires_at < signed_date:
            errors.append("授权截止日期不能早于签署日期")
    except ValueError:
        errors.append("expires_at 必须是 YYYY-MM-DD")

    profile = payload.get("profile")
    if not isinstance(profile, dict):
        errors.append("profile 必须是对象")
    else:
        for key in ("district", "industry"):
            if not isinstance(profile.get(key), str) or not profile[key].strip():
                errors.append(f"profile.{key} 不能为空")
        years = profile.get("operating_years")
        if isinstance(years, bool) or not isinstance(years, int) or years < 0:
            errors.append("profile.operating_years 必须是非负整数")

    facts = payload.get("facts", {})
    if not isinstance(facts, dict) or not facts:
        errors.append("facts 必须包含至少一个结构化事实")
    else:
        for key, fact in facts.items():
            if not isinstance(fact, dict):
                errors.append(f"facts.{key} 必须是对象")
                continue
            if fact.get("status") not in ALLOWED_STATUSES:
                errors.append(f"facts.{key}.status 无效")
            if fact.get("status") == "confirmed" and not fact.get("evidence"):
                errors.append(f"facts.{key} 已确认但没有证据引用")

    evidence = payload.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence 必须是数组")
        evidence = []
    evidence_ids = set()
    for index, item in enumerate(evidence):
        evidence_id = item.get("id") if isinstance(item, dict) else None
        if not evidence_id:
            errors.append(f"evidence[{index}] 缺少 id")
            continue
        if evidence_id in evidence_ids:
            errors.append(f"证据编号重复：{evidence_id}")
        evidence_ids.add(evidence_id)
        if not SHA256.fullmatch(str(item.get("file_sha256", ""))):
            errors.append(f"evidence[{index}].file_sha256 无效")

    for key, fact in (facts.items() if isinstance(facts, dict) else []):
        if not isinstance(fact, dict):
            continue
        references = fact.get("evidence", [])
        if not isinstance(references, list):
            errors.append(f"facts.{key}.evidence 必须是数组")
            continue
        for evidence_id in references:
            if evidence_id not in evidence_ids:
                errors.append(f"facts.{key} 引用了不存在的证据 {evidence_id}")

    gold = payload.get("gold_standard")
    if not isinstance(gold, list):
        errors.append("gold_standard 必须是数组")
        gold = []
    if not gold:
        errors.append("至少需要一条独立业务金标准")
    for index, item in enumerate(gold):
        if not isinstance(item, dict):
            errors.append(f"gold_standard[{index}] 必须是对象")
            continue
        if item.get("expected_status") not in ALLOWED_RESULTS:
            errors.append(f"gold_standard[{index}].expected_status 无效")
        if not str(item.get("annotator_id", "")).startswith("ANN-"):
            errors.append(f"gold_standard[{index}] 缺少匿名标注员编号")
        if item.get("review_state") not in {"draft", "reviewed", "adjudicated"}:
            errors.append(f"gold_standard[{index}].review_state 无效")

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance 必须是对象")
        provenance = {}
    reviewers = provenance.get("reviewed_by", [])
    if not isinstance(reviewers, list) or len({r for r in reviewers if isinstance(r, str)}) < 2:
        errors.append("脱敏结果至少需要两名复核人")
    if provenance.get("split") not in {"development", "blind_test", "holdout"}:
        errors.append("provenance.split 无效")

    for item_path, key, value in walk(payload):
        if key in FORBIDDEN_KEYS:
            errors.append(f"禁止出现直接标识字段：{item_path}")
        if isinstance(value, str):
            if EMAIL.search(value):
                errors.append(f"疑似邮箱未脱敏：{item_path}")
            if PHONE.search(value):
                errors.append(f"疑似手机号未脱敏：{item_path}")
            if CREDIT_CODE.search(value):
                errors.append(f"疑似统一社会信用代码未脱敏：{item_path}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="验证企策通授权脱敏企业案例")
    parser.add_argument("case", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.case.read_text(encoding="utf-8"))
    errors = validate(payload)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
