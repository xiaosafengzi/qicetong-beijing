"""Register the verified Ollama model with Nexent and bind it to Qicetong."""
from __future__ import annotations

import argparse
import json

import httpx

from connect_qicetong import API, ROOT, load_access, request


MODEL_NAME = "qwen3:8b"
DISPLAY_NAME = "Qwen3 8B 本地"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-pending", action="store_true", help="Register the model while weights are still downloading")
    args = parser.parse_args()
    with httpx.Client(timeout=90, trust_env=False) as client:
        tags = client.get("http://127.0.0.1:11434/api/tags").json()
        model_downloaded = MODEL_NAME in {m.get("name") for m in tags.get("models", [])}
        if not model_downloaded and not args.allow_pending:
            raise RuntimeError("Local Ollama model has not finished downloading")
        email, password, _ = load_access()
        session = request(client, "POST", "/user/signin", json={"email": email, "password": password})
        client.headers["Authorization"] = "Bearer " + session["data"]["session"]["access_token"]

        models = request(client, "GET", "/model/list")["data"]
        model = next((m for m in models if m.get("display_name") == DISPLAY_NAME), None)
        runtime_settings = {
            "max_tokens": 4096,
            "context_window_tokens": 8192,
            "max_input_tokens": 7168,
            "max_output_tokens": 1024,
            "default_output_reserve_tokens": 1024,
            "temperature": 0.1,
            "top_p": 0.9,
            "extra_params": {"enable_thinking": False},
        }
        if model is None:
            payload = {
                "model_factory": "OpenAI-API-Compatible",
                "model_name": MODEL_NAME,
                "model_type": "llm",
                "display_name": DISPLAY_NAME,
                "api_key": "ollama",
                "base_url": "http://host.docker.internal:11434/v1",
                **runtime_settings,
            }
            request(client, "POST", "/model/create", json=payload)
            models = request(client, "GET", "/model/list")["data"]
            model = next((m for m in models if m.get("display_name") == DISPLAY_NAME), None)
        if model is None or not model.get("model_id"):
            raise RuntimeError("Local model did not appear in Nexent model list")
        model_id = model["model_id"]
        request(client, "POST", "/model/update", params={"display_name": DISPLAY_NAME}, json=runtime_settings)
        health = None
        if model_downloaded:
            health = request(client, "POST", "/model/healthcheck", params={"display_name": DISPLAY_NAME, "model_type": "llm"})
            if health.get("data", {}).get("connectivity") is not True:
                raise RuntimeError(f"Nexent cannot use the local model: {health.get('data')}")

        agents = request(client, "GET", "/agent/list")
        agent = next((a for a in agents if a.get("name") == "qicetong_beijing"), None)
        if agent is None:
            raise RuntimeError("Qicetong agent must be created before binding the model")
        request(client, "POST", "/agent/update", json={
            "agent_id": agent["agent_id"], "model_ids": [model_id],
            "business_logic_model_id": model_id,
            "business_logic_model_name": MODEL_NAME,
            "model_params_override": {
                str(model_id): {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "extra_params": {"__custom__": {"reasoning_effort": "none"}},
                }
            },
        })
        bound = request(client, "POST", "/agent/search_info", json={"agent_id": agent["agent_id"]})
        if bound.get("business_logic_model_id") != model_id:
            raise RuntimeError("Nexent did not persist the business model binding")
        if model_downloaded and model_id not in bound.get("model_ids", []):
            raise RuntimeError("Nexent did not activate the local model for this agent")
        current_version = bound.get("current_version_no")
        publish_required = not current_version
        if current_version:
            comparison = request(
                client,
                "POST",
                f"/agent/{agent['agent_id']}/versions/compare",
                json={"version_no_a": current_version, "version_no_b": 0},
            )
            publish_required = bool(comparison.get("differences"))
        if publish_required:
            request(
                client,
                "POST",
                f"/agent/{agent['agent_id']}/publish",
                json={
                    "version_name": "企策通评测增强版" if current_version else "企策通演示版",
                    "release_note": "新增困难案例评测、单模型消融、覆盖率指标与系统评测 MCP/Skill" if current_version else "北京企业政策预审本地演示版",
                },
            )
            bound = request(client, "POST", "/agent/search_info", json={"agent_id": agent["agent_id"]})
    output = {"model": MODEL_NAME, "model_id": model_id, "agent_id": agent["agent_id"], "published_version": bound.get("current_version_no"), "state": "ready" if model_downloaded else "pending_download", "health": health.get("data") if health else None, "agent_available": bound.get("is_available"), "unavailable_reasons": bound.get("unavailable_reasons", [])}
    (ROOT / "runtime/nexent/model-results.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
