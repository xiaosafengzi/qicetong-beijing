FROM ccr.ccs.tencentyun.com/nexent-hub/nexent:v2.6.0

# Compatibility overlay for Ollama-backed structured CodeAgent execution.
COPY agents/core_agent.py /opt/backend/.venv/lib/python3.11/site-packages/nexent/core/agents/core_agent.py
COPY agents/nexent_agent.py /opt/backend/.venv/lib/python3.11/site-packages/nexent/core/agents/nexent_agent.py
