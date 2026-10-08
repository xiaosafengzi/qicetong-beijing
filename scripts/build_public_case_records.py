from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "public_candidate_seed_2026.json"
OUTPUT = ROOT / "data" / "public_case_records_2026.jsonl"


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = source["candidates"]
    if len(candidates) != 50:
        raise ValueError("预期 50 条公开候选记录")

    records = []
    for index, candidate in enumerate(candidates, 1):
        records.append(
            {
                "record_id": f"PUB-{index:03d}",
                "data_class": "public_notice_only",
                "source_title": source["source_title"],
                "source_url": source["source_url"],
                "source_document_url": source["attachment_url"],
                "publication_date": "2026-07-09",
                "source_serial": int(candidate["source_serial"]),
                "observed_facts": {
                    "company_name": candidate["company_name"],
                    "district": candidate["district"],
                    "listed_in_proposed_batch": True,
                },
                "not_observed": [
                    "final_admission_result",
                    "employee_count",
                    "technology_staff_count",
                    "revenue",
                    "rd_expenses",
                    "intellectual_property_evidence",
                    "application_materials",
                ],
                "authorized_company_materials": False,
                "suitable_for": ["public_notice_extraction", "source_citation", "known_unknown_behavior"],
            }
        )

    if len({r["observed_facts"]["company_name"] for r in records}) != len(records):
        raise ValueError("公开记录中存在重复企业名称")
    OUTPUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")
    print(json.dumps({"public_records": len(records), "output": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
