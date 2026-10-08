from scripts.validate_authorized_case import validate


def valid_case():
    return {
        "case_id": "BJC-001",
        "authorization": {
            "document_sha256": "a" * 64,
            "signed_date": "2026-09-24",
            "internal_evaluation": True,
            "defense_demo": False,
            "open_source": False,
            "expires_at": "2027-12-31",
            "withdrawal_contact": "项目数据负责人编号 DPO-01",
        },
        "profile": {"district": "海淀区", "industry": "软件和信息技术服务业", "operating_years": 6},
        "facts": {"employees": {"value": 80, "unit": "人", "period": "2025", "status": "confirmed", "evidence": ["ev-1"]}},
        "evidence": [{"id": "ev-1", "document_type": "人员汇总表", "locator": "汇总行", "snippet": "职工总数为80人", "file_sha256": "b" * 64}],
        "gold_standard": [{"policy_id": "sme-bj-2026", "rule_id": "staff", "expected_status": "pass", "missing_fields": [], "reason": "80人不超过500人", "annotator_id": "ANN-01", "review_state": "reviewed"}],
        "provenance": {"received_at": "2026-09-24T10:00:00+08:00", "deidentified_at": "2026-09-24T11:00:00+08:00", "reviewed_by": ["REV-01", "REV-02"], "split": "blind_test"},
    }


def test_valid_authorized_case():
    assert validate(valid_case()) == []


def test_rejects_direct_identifiers_and_missing_authorization():
    payload = valid_case()
    payload["authorization"]["internal_evaluation"] = False
    payload["profile"]["company_name"] = "某真实企业"
    payload["evidence"][0]["snippet"] = "联系人 test@example.com，手机号 13800138000"
    errors = validate(payload)
    assert any("明确授权" in item for item in errors)
    assert any("直接标识字段" in item for item in errors)
    assert any("邮箱" in item for item in errors)
    assert any("手机号" in item for item in errors)


def test_rejects_malformed_case_without_crashing():
    payload = valid_case()
    payload["authorization"] = []
    payload["facts"] = []
    payload["evidence"] = [None]
    payload["gold_standard"] = [None]
    payload["provenance"] = []
    errors = validate(payload)
    assert any("authorization 必须是对象" in item for item in errors)
    assert any("facts 必须包含" in item for item in errors)
    assert any("provenance 必须是对象" in item for item in errors)


def test_rejects_unspecified_publication_scope_and_invalid_date():
    payload = valid_case()
    payload["authorization"]["open_source"] = None
    payload["authorization"]["expires_at"] = "2020-01-01"
    errors = validate(payload)
    assert any("open_source" in item for item in errors)
    assert any("授权已过期" in item for item in errors)
