"""Evaluate safe abstention on public notice records; no enterprise data is stored."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qicetong.evaluation import evaluate_public_notice


if __name__ == "__main__":
    result = evaluate_public_notice()
    print(json.dumps({"artifact": "artifacts/public-notice-results.json", "dataset": result["dataset"],
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
