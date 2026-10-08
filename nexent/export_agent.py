"""Export the real configured Nexent agent and bundled custom skills."""
from __future__ import annotations

import json
import re
import zipfile
from io import BytesIO

import httpx

from connect_qicetong import API, ROOT, load_access, request


def main() -> None:
    email, password, _ = load_access()
    with httpx.Client(timeout=90, trust_env=False) as client:
        session = request(client, "POST", "/user/signin", json={"email": email, "password": password})
        client.headers["Authorization"] = "Bearer " + session["data"]["session"]["access_token"]
        agents = request(client, "GET", "/agent/list")
        agent = next((item for item in agents if item.get("name") == "qicetong_beijing"), None)
        if agent is None:
            raise RuntimeError("Qicetong agent is not configured")
        response = client.post(API + "/agent/export", json={"agent_id": agent["agent_id"]})
        response.raise_for_status()

    output_dir = ROOT / "artifacts/nexent-agent"
    output_dir.mkdir(parents=True, exist_ok=True)
    if response.headers.get("content-type", "").startswith("application/zip"):
        archive = BytesIO(response.content)
        with zipfile.ZipFile(archive) as bundle:
            bad = [name for name in bundle.namelist() if name.startswith(("/", "\\")) or ".." in name.split("/")]
            if bad:
                raise RuntimeError(f"Unsafe paths in Nexent export: {bad}")
            names = bundle.namelist()
        output = output_dir / "qicetong-beijing-agent.zip"
        output.write_bytes(response.content)
        result = {"agent_id": agent["agent_id"], "format": "zip", "path": str(output.relative_to(ROOT)), "entries": names}
    else:
        payload = response.json()
        output = output_dir / "qicetong-beijing-agent.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        result = {"agent_id": agent["agent_id"], "format": "json", "path": str(output.relative_to(ROOT))}
    # Do not print or persist authentication material. Export content is created by Nexent itself.
    result["path"] = re.sub(r"\\+", "/", result["path"])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
