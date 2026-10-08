"""Register and verify the local Qicetong MCP and skills in a running Nexent."""
from __future__ import annotations

import json
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:5010"
MCP_NAME = "qicetong-beijing"
SKILL_NAMES = {
    "policy-applicability",
    "enterprise-precheck",
    "policy-change-review",
    "precheck-report",
    "system-evaluation",
}


def load_access(prefer_demo: bool = True) -> tuple[str, str, Path]:
    """Load the browser tenant account when present, otherwise the bootstrap SU account."""
    candidates = [ROOT / "runtime/nexent/demo-access.txt"] if prefer_demo else []
    candidates.append(ROOT / "runtime/nexent/local-access.txt")
    for secret_file in candidates:
        if not secret_file.is_file():
            continue
        values = {}
        for line in secret_file.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(": ")
            if separator:
                values[key] = value.strip()
        email = values.get("Email", "suadmin@nexent.com")
        password = values.get("Password")
        if password:
            return email, password, secret_file
    raise FileNotFoundError("No Nexent access file is available")


def request(client: httpx.Client, method: str, path: str, **kwargs):
    response = client.request(method, API + path, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {response.text[:400]}")
    return response.json()


def main():
    email, password, _ = load_access()
    result: dict = {}
    with httpx.Client(timeout=45, trust_env=False) as client:
        health = request(client, "GET", "/health/ready")
        if health.get("status") != "ready":
            raise RuntimeError(f"Nexent config API not ready: {health}")
        session = request(
            client, "POST", "/user/signin",
            json={"email": email, "password": password},
        )
        token = session["data"]["session"]["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        result["login"] = "ok"

        records = request(client, "GET", "/mcp/list")["remote_mcp_server_list"]
        record = next((x for x in records if x.get("remote_mcp_server_name") == MCP_NAME), None)
        config = json.loads((ROOT / "nexent/nexent-mcp-registration.json").read_text(encoding="utf-8"))
        if record is None:
            request(client, "POST", "/mcp/add", json=config)
            records = request(client, "GET", "/mcp/list")["remote_mcp_server_list"]
            record = next((x for x in records if x.get("remote_mcp_server_name") == MCP_NAME), None)
        if record is None:
            public_records = [
                {key: item.get(key) for key in ("mcp_id", "remote_mcp_server_name", "source")}
                for item in records
            ]
            raise RuntimeError(f"MCP registration did not appear in Nexent: {public_records}")
        if record.get("remote_mcp_server") != config["server_url"]:
            request(client, "PUT", "/mcp/update", json={
                "mcp_id": record["mcp_id"],
                "name": config["name"],
                "description": config["description"],
                "server_url": config["server_url"],
                "tags": config["tags"],
            })
        mcp_id = record.get("mcp_id") or record.get("id")
        request(client, "GET", "/tool/scan_tool")
        tool_data = request(client, "GET", "/mcp/tools", params={"mcp_id": mcp_id})
        tool_names = {x.get("name") for x in tool_data["tools"]}
        if len(tool_names) != 9 or not {"review_enterprise", "get_system_evaluation", "preview_uploaded_policy_change"}.issubset(tool_names):
            raise RuntimeError(f"Nexent discovered unexpected tools: {sorted(str(x) for x in tool_names)}")
        result["mcp"] = {"id": mcp_id, "tool_names": sorted(tool_names)}

        skills = request(client, "GET", "/skills")["skills"]
        installed = {x.get("name") for x in skills}
        for name in sorted(SKILL_NAMES - installed):
            archive = ROOT / "artifacts/nexent-skills" / (name + ".zip")
            if not archive.is_file():
                raise FileNotFoundError(archive)
            with archive.open("rb") as file:
                request(client, "POST", "/skills/upload", files={"file": (archive.name, file, "application/zip")}, data={"source": "custom", "skill_name": name})
        skills = request(client, "GET", "/skills")["skills"]
        installed = {x.get("name") for x in skills}
        if not SKILL_NAMES.issubset(installed):
            raise RuntimeError(f"Nexent skills missing: {sorted(SKILL_NAMES - installed)}")
        # Re-upload the edited workflow so the platform export contains the
        # same policy-change instructions as the source package.
        policy_skill_name = "policy-change-review"
        local_skill = (ROOT / "nexent/skills" / policy_skill_name / "SKILL.md").read_text(encoding="utf-8")
        remote_skill = request(client, "GET", f"/skills/{policy_skill_name}/files/SKILL.md").get("content", "")
        if remote_skill != local_skill:
            archive = ROOT / "artifacts/nexent-skills" / f"{policy_skill_name}.zip"
            with archive.open("rb") as file:
                request(client, "PUT", f"/skills/{policy_skill_name}/upload", files={"file": (archive.name, file, "application/zip")})
        result["skills"] = sorted(SKILL_NAMES)

        request(client, "GET", "/tool/scan_tool")
        all_tools = request(client, "GET", "/tool/list")
        selected_tools = [
            tool for tool in all_tools
            if tool.get("source") == "mcp"
            and (tool.get("origin_name") in tool_names or tool.get("name") in tool_names)
        ]
        if len(selected_tools) != 9:
            raise RuntimeError(f"Expected 9 Qicetong tool bindings, found {len(selected_tools)}")
        tool_ids = sorted(tool["tool_id"] for tool in selected_tools)
        skill_ids = sorted(skill["skill_id"] for skill in skills if skill.get("name") in SKILL_NAMES)

        agents = request(client, "GET", "/agent/list")
        agent = next((x for x in agents if x.get("name") == "qicetong_beijing"), None)
        payload = {
            "name": "qicetong_beijing",
            "display_name": "企策通·北京企业政策预审",
            "description": "北京试点政策适用性与企业材料预审，提供依据、证据链和待补事项。",
            "business_description": "面向北京科技型中小企业和高新技术企业申报准备。",
            "author": "企策通",
            "is_main_agent": True,
            "enabled": True,
            "provide_run_summary": False,
            "max_steps": 1,
            "duty_prompt": (ROOT / "nexent/agent-instructions.md").read_text(encoding="utf-8"),
            "constraint_prompt": "你运行在 Nexent 结构化 CodeAgent 中，系统会把 code 字段作为 Python 执行。政策预审只执行一个代码动作：先调用 review_enterprise，再在同一个 code 字段中调用 final_answer(report)；系统效果问题调用 get_system_evaluation 后直接 final_answer(result)。不要描述计划，不要创建任务清单。只能调用 list_enterprises、list_policy_catalog、search_policy_evidence、review_enterprise、get_evidence_graph、compare_policy_versions、preview_uploaded_policy_change、export_review_report、get_system_evaluation 和 final_answer。上传政策变化只能预览，不能发布规则。禁止调用 read_skill_config、run_skill_script、write_skill_file、upload_to_s3，禁止用自编脚本模拟业务结果。只交付工具返回结果；不得编造报告 ID、政策条款、材料状态或评测数值。",
            "few_shots_prompt": "示例：用户要求预审 demo-01 申请 hnte-bj-2026，核查日期 2026-09-24。唯一的 code 字段必须是：report = review_enterprise(company_id=\"demo-01\", policy_id=\"hnte-bj-2026\", as_of=\"2026-09-24\"); final_answer(report)。不要使用 print，不要创建 tasks 列表，不要调用不存在的工具，不要编造工具结果。",
            "enabled_tool_ids": tool_ids,
            "enabled_skill_ids": skill_ids,
        }
        if agent:
            payload["agent_id"] = agent["agent_id"]
        saved = request(client, "POST", "/agent/update", json=payload)
        agent_id = saved.get("agent_id") or payload.get("agent_id")
        if not agent_id:
            raise RuntimeError(f"Agent save returned no ID: {saved}")
        result["agent"] = {"id": agent_id, "name": payload["display_name"], "tool_ids": tool_ids, "enabled_skill_ids": skill_ids, "available_skill_ids": skill_ids}

    path = ROOT / "runtime/nexent/integration-results.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
