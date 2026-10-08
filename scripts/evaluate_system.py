from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from qicetong.evaluation import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="运行企策通可复现困难案例评测")
    parser.add_argument("--with-llm", action="store_true", help="同时运行本地 Qwen3 8B 单模型基线")
    parser.add_argument("--model", default="qwen3:8b")
    args = parser.parse_args()
    result = evaluate(include_llm_baseline=args.with_llm, model=args.model)
    concise = {
        "artifact": "artifacts/evaluation-results.json",
        "engine": result["engine"]["summary"],
        "llm_baseline": result["llm_baseline"]["summary"] if result["llm_baseline"] else None,
    }
    print(json.dumps(concise, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
