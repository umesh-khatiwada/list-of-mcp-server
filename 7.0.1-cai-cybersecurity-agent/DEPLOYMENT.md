# Deployment Guide

This repository now treats every agent as an independent service so they can be deployed separately. Each service exposes its own entry point and relies on environment variables for configuration.

## Cybersecurity Agent Service

- Location: cybersecurity-agent/
- Entry point: python cybersecurity-agent/server.py
- Responsibilities: Serves the CAI-powered cybersecurity specialist through the A2A protocol.
- Required environment variables:
  - DEEPSEEK_API_KEY (or OPENAI_API_KEY) – API key for the CAI-compatible model
  - Optional overrides: DEEPSEEK_BASE_URL, CAI_MODEL, CYBERSECURITY_AGENT_HOST, CYBERSECURITY_AGENT_PORT, CYBERSECURITY_AGENT_PUBLIC_URL, CYBERSECURITY_AGENT_TEMPERATURE

### Running locally

```bash
export DEEPSEEK_API_KEY=sk-...
export CYBERSECURITY_AGENT_PORT=9003  # optional
python cybersecurity-agent/server.py
```

This launches an A2A endpoint such as http://127.0.0.1:9003/ that other services can discover.

## Orchestrator Service

- Location: orchestrator-agent/
- Entry point: python orchestrator-agent/orchestrator.py
- Responsibilities: Discovers remote A2A agents and routes user prompts.
- Required environment variables:
  - ORCHESTRATOR_AGENT_URLS – Comma-separated list of remote A2A base URLs
  - Optional: CYBERSECURITY_AGENT_URL (appends to the list), MISTRAL_API_KEY (for optional Mistral usage), SESSION_ID
  - DeepSeek/OpenAI credentials if using the bundled DeepSeek model helper: DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, CAI_MODEL

### Running locally

```bash
export ORCHESTRATOR_AGENT_URLS=http://127.0.0.1:9001,http://127.0.0.1:9002
export CYBERSECURITY_AGENT_URL=http://127.0.0.1:9003
export DEEPSEEK_API_KEY=sk-...
python orchestrator-agent/orchestrator.py
```

If no URLs are configured the orchestrator starts but warns that no downstream agents are reachable.

## Additional Agents

Directories such as blueteam-agent/ and redteam-agent/ are intentionally empty placeholders. You can package them using the same pattern: keep their logic self-contained within the directory, expose an entry point script, and provide agent-specific environment variables for runtime configuration.

## Packaging Notes

- Each service can be dockerised by copying only its directory plus shared dependency declarations (requirements.txt). No module-level imports reference files outside their own package.
- Dependencies are shared via the top-level requirements.txt; when deploying separately you can reuse or trim that list per service as needed.
- Configuration is exclusively environment-driven, so you can manage secrets independently per deployment.
