"""Load an isolated synthetic industry template without changing Beijing seed data."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from . import store


TEMPLATE = Path(__file__).resolve().parents[1] / "data/manufacturing_transfer.json"


def load_manufacturing_template() -> tuple[dict, list[tuple[dict, str]]]:
    source = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    policy = copy.deepcopy(source["policy"])
    for rule in policy["rules"]:
        rule["source"] = policy["source"]
    companies = []
    for example in source["examples"]:
        evidence = []
        facts = {}
        for field, (value, unit, period) in example["facts"].items():
            eid = f"{example['id']}-{field}"
            evidence.append({"id": eid, "title": "模拟来料抽样台账", "locator": f"{example['id']} / {field}",
                             "text": f"{field}: {value} {unit}; 期间 {period or '未指定'}"})
            facts[field] = {"value": value, "unit": unit, "period": period, "status": "confirmed", "evidence": [eid]}
        company = {"id": example["id"], "name": example["name"], "district": "演示工厂", "industry": "制造业",
                   "is_demo": True, "note": "完全合成的迁移验证批次", "facts": facts, "evidence": evidence}
        companies.append((company, example["expected_status"]))
    return policy, companies


def seed_manufacturing_template() -> tuple[dict, list[tuple[dict, str]]]:
    """Only call in a temporary QCT_RUNTIME for transfer tests, not in the Beijing demo."""
    policy, companies = load_manufacturing_template()
    store.put("policy", policy)
    for company, _ in companies:
        store.put("company", company)
    return policy, companies
