"""Evaluate the same evidence engine on a synthetic manufacturing template."""
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qicetong.engine import dependency_graph, review
from qicetong.transfer import load_manufacturing_template


def main():
    policy, companies = load_manufacturing_template()
    rows = []
    for company, expected in companies:
        report = review(company, policy, date(2026, 9, 22))
        graph = dependency_graph(report)
        rows.append({"id": company["id"], "expected": expected, "actual": report["status"],
                     "match": report["status"] == expected, "check_count": len(report["checks"]),
                     "graph_nodes": len(graph["nodes"]), "graph_edges": len(graph["edges"])})
    result = {"data_type": "synthetic_transfer_demonstration", "industry": "manufacturing_quality",
              "engine_reused": True, "mcp_contract_tested": False,
              "cases": rows, "matched": sum(row["match"] for row in rows), "total": len(rows),
              "claim_boundary": "只证明模板可装入现有证据引擎；不代表制造业真实规则或真实批次效果。"}
    output = ROOT / "artifacts/manufacturing-transfer-results.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"artifact": str(output.relative_to(ROOT)), "matched": result["matched"], "total": result["total"]}))


if __name__ == "__main__":
    main()
