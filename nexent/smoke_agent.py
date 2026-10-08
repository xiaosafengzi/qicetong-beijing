"""Run one local Nexent conversation and capture a reproducible smoke-test trace."""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter

import httpx

from connect_qicetong import ROOT, load_access, request
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from qicetong import documents, store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("review", "evaluation", "policy_change", "search_review"), default="review")
    args = parser.parse_args()
    results = json.loads((ROOT / "runtime/nexent/model-results.json").read_text(encoding="utf-8"))
    if results.get("state") != "ready":
        raise RuntimeError("Local model must pass its Nexent health check first")
    email, password, _ = load_access()
    suffix = "" if args.mode == "review" else "-" + args.mode.replace("_", "-")
    asset_id = None
    if args.mode == "policy_change":
        store.initialize()
        asset_id = documents.ingest("演示用假设阈值.txt", "职工总数不超过50人。".encode("utf-8"), "policy")["id"]
    trace_path = ROOT / f"runtime/nexent/smoke-agent{suffix}-events.jsonl"
    event_types: Counter[str] = Counter()
    tools_seen: set[str] = set()
    execution_logs: list[str] = []
    started = time.monotonic()
    with httpx.Client(timeout=httpx.Timeout(300, connect=15), trust_env=False) as client:
        session = request(
            client, "POST", "/user/signin",
            json={"email": email, "password": password},
        )
        token = session["data"]["session"]["access_token"]
        with client.stream(
            "POST", "http://127.0.0.1:5014/agent/run",
            headers={"Authorization": "Bearer " + token, "Accept": "text/event-stream"},
            json={
                "query": {
                    "review": "请预审模拟企业 demo-01 申请政策 hnte-bj-2026，核查日期 2026-09-24。唯一动作必须是：report = review_enterprise(company_id=\"demo-01\", policy_id=\"hnte-bj-2026\", as_of=\"2026-09-24\"); final_answer(report)。不要自行补造数据。",
                    "evaluation": "请给出系统实测效果。唯一动作必须是：result = get_system_evaluation(); final_answer(result)。不要编造评测数值。",
                    "policy_change": f"请预览上传材料 {asset_id} 对 sme-bj-2026 在 2026-09-22 的假设影响。唯一动作必须是：result = preview_uploaded_policy_change(asset_id=\"{asset_id}\", policy_id=\"sme-bj-2026\", as_of=\"2026-09-22\"); final_answer(result)。这是演示用假设，不是已生效政策。",
                    "search_review": "请先检索高新技术企业科技人员比例条款，再预审模拟企业 demo-01 的 hnte-bj-2026，日期为 2026-09-24。唯一代码动作：sources = search_policy_evidence(query=\"科技人员 比例\", limit=3); report = review_enterprise(company_id=\"demo-01\", policy_id=\"hnte-bj-2026\", as_of=\"2026-09-24\"); final_answer({\"sources\": sources, \"report\": report})。不得自行补造数据。",
                }[args.mode],
                "agent_id": results["agent_id"],
                "model_id": results["model_id"],
                "is_debug": True,
                "enable_plan": False,
                "enable_automation_tool": False,
            },
        ) as response:
            if response.status_code >= 400:
                raise RuntimeError(f"Nexent agent run HTTP {response.status_code}: {response.read().decode('utf-8', 'replace')[:500]}")
            with trace_path.open("w", encoding="utf-8") as trace:
                for line in response.iter_lines():
                    if time.monotonic() - started > 600:
                        raise TimeoutError("Nexent smoke test exceeded ten minutes")
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    trace.write(json.dumps(event, ensure_ascii=False) + "\n")
                    event_types[str(event.get("type", "unknown"))] += 1
                    if event.get("type") == "tool" and event.get("tool_name"):
                        tools_seen.add(str(event["tool_name"]))
                    if event.get("type") == "execution_logs":
                        serial = json.dumps(event, ensure_ascii=False)
                        execution_logs.append(serial)
    summary = {
        "agent_id": results["agent_id"],
        "model_id": results["model_id"],
        "duration_s": round(time.monotonic() - started, 1),
        "event_types": dict(event_types),
        "tools_seen": sorted(tools_seen),
        "execution_log_events": len(execution_logs),
        "trace": str(trace_path),
    }
    (ROOT / f"runtime/nexent/smoke-agent{suffix}-results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    expected_tools = {
        "review": {"review_enterprise"}, "evaluation": {"get_system_evaluation"},
        "policy_change": {"preview_uploaded_policy_change"},
        "search_review": {"search_policy_evidence", "review_enterprise"},
    }[args.mode]
    if not expected_tools.issubset(tools_seen) or not execution_logs:
        raise RuntimeError(f"Agent stream did not execute {sorted(expected_tools)}")


if __name__ == "__main__":
    main()
