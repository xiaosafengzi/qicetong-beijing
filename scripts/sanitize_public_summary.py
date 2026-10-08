"""Export only historical aggregate counts; never distribute notice rows or names."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    original = ROOT / "artifacts/public-notice-results.json"
    data = json.loads(original.read_text(encoding="utf-8"))
    summary_keys = ("record_count", "distinct_company_count", "district_count", "abstained_count", "unsupported_pass_claim_count")
    output = {
        "generated_at": data["generated_at"],
        "historical_summary_only": True,
        "records_distributed": False,
        "original_result_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "dataset": {
            "name": data["dataset"]["name"], "type": "public_notice_aggregate_only",
            "authorized_company_case_count": 0,
            "source_url": "https://kw.beijing.gov.cn/zwgk/tzgg/202607/t20260709_4754163.html",
            "claim_boundary": "本仓库仅分发历史汇总，未附企业名册；不是克隆后重新运行的结果，也不代表资格准确率或企业授权。",
        },
        "summary": {key: data["summary"][key] for key in summary_keys},
        "rows": [],
    }
    target = ROOT / "artifacts/public-notice-summary.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({"output": str(target.relative_to(ROOT)), "rows_distributed": 0, "record_count": output["summary"]["record_count"]})


if __name__ == "__main__":
    main()
