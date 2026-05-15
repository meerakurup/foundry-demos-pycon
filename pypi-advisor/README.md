# PyPI Dependency Auditor

A Python dependency auditing agent powered by **Microsoft Foundry** and a private **MCP server** on Azure Functions. The agent is live and running in Microsoft Foundry — you can use it directly or run it locally via the CLI.

**What it does:** Given a `requirements.txt`, the agent checks every package for outdated versions, known CVEs (via OSV.dev), and available alternatives, then produces an actionable audit report.

### Key components

- **Private MCP server** on Azure Functions — exposes 4 tools (`get_package_info`, `check_vulnerabilities`, `compare_packages`, `get_changelog`) backed by PyPI and OSV.dev APIs
- **Foundry prompt agent** (`PyPI-Dependency-Auditor`) — orchestrates the MCP tools alongside built-in **Web Search** and **Code Interpreter**
- **Demo apps** — sample apps with intentionally outdated/vulnerable dependencies for testing

```
pypi-advisor/
├── mcp_server/
│   ├── function_app.py      ← Azure Function MCP server (4 tools)
│   ├── host.json            ← MCP extension config
│   ├── local.settings.json  ← Local dev settings
│   └── requirements.txt     ← Server dependencies (azure-functions, httpx)
├── demo_app/
│   ├── app.py               ← Sample "inherited" app to audit
│   └── requirements.txt     ← Intentionally outdated/vulnerable deps
├── demo_legacy_api/
│   ├── app.py               ← Sample FastAPI inventory app to audit
│   ├── README.md            ← Run and audit instructions
│   └── requirements.txt     ← Separate intentionally stale deps
├── audit_agent.py           ← CLI script — creates & invokes the Foundry agent
├── requirements.txt         ← Agent dependencies (azure-ai-projects, azure-ai-agents, azure-identity)
├── .env.template            ← Environment variable template
└── README.md
```

---

## The agent in Microsoft Foundry

The `PyPI-Dependency-Auditor` agent is deployed and running in Microsoft Foundry. It uses:

| Tool | Source | Purpose |
|------|--------|---------|
| `get_package_info` | MCP Server (Azure Function) | Latest version, release date, license, staleness |
| `check_vulnerabilities` | MCP Server (Azure Function) | CVE lookup via OSV.dev for a pinned version |
| `compare_packages` | MCP Server (Azure Function) | Side-by-side comparison of two packages |
| `get_changelog` | MCP Server (Azure Function) | Recent release history for a package |
| Web Search | Built-in (Bing) | Real-world exploit context and migration guides |
| Code Interpreter | Built-in (sandbox) | Stats computation and chart generation |

You can interact with the agent directly in the [Microsoft Foundry portal](https://ai.azure.com) or invoke it programmatically via `audit_agent.py`.

---

## Prerequisites

- Python 3.10+
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- [Azure Functions Core Tools v4](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local) (v4.0.7030+) — only needed if running the MCP server locally
- A **Microsoft Foundry project** with a deployed model (gpt-5 recommended, gpt-5.4-mini for speed)

---

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.template .env
```

Edit `.env` with your values:

```env
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
FOUNDRY_MODEL=gpt-5
PYPI_MCP_URL=http://localhost:7071/runtime/webhooks/mcp
```

Get your project endpoint from the AI Toolkit sidebar in VS Code or from the [Microsoft Foundry portal](https://ai.azure.com).

### 3. Start the MCP server (local development)

```bash
cd mcp_server
pip install -r requirements.txt
func start
```

The MCP server will be available at `http://localhost:7071/runtime/webhooks/mcp`.

### 4. Authenticate and run

```bash
az login
python audit_agent.py                          # audits demo_app/requirements.txt
python audit_agent.py /path/to/requirements.txt # audits any project
python audit_agent.py demo_legacy_api/requirements.txt # audits the second demo app
```

### What happens when you run it

1. The agent creates a versioned `PyPI-Dependency-Auditor` in your Foundry project
2. Connects to the MCP server for PyPI metadata and CVE data
3. Uses **Web Search** to enrich CVE findings with real-world exploit context
4. Uses **Code Interpreter** to compute summary stats and generate charts
5. Outputs a structured audit report with severity levels and recommended actions
6. Enters **interactive mode** for live follow-up questions

---

## Deploying the MCP server to Azure

```bash
cd mcp_server
func azure functionapp publish <YOUR_FUNCTION_APP_NAME>
```

Then update `PYPI_MCP_URL` in your `.env`:

```
PYPI_MCP_URL=https://<app>.azurewebsites.net/runtime/webhooks/mcp
```

For production, the MCP extension uses the `mcp_extension` system key. Retrieve it with:

```bash
az functionapp keys list --resource-group <RG> --name <APP> \
  --query systemKeys.mcp_extension --output tsv
```

To use the deployed MCP server with the Foundry agent in production, create a [project connection](https://learn.microsoft.com/azure/ai-foundry/agents/how-to/tools/mcp) in Foundry to store the key and reference it via `project_connection_id` in the `MCPTool` definition.

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│  audit_agent.py (Foundry prompt agent)           │
│                                                  │
│  Tools:                                          │
│  ├─ MCPTool → Private MCP Server                 │
│  ├─ WebSearchPreviewTool → Bing                  │
│  └─ CodeInterpreterTool → sandboxed Python       │
└──────────────┬───────────────────────┬───────────┘
               │                       │
               ▼                       ▼
┌──────────────────────────┐   ┌──────────────────┐
│ Azure Function           │   │ Built-in tools   │
│ MCP Server               │   │ (Web Search,     │
│ (PyPIAuditor)            │   │  Code Interp.)   │
│                          │   └──────────────────┘
│ get_package_info         │
│ check_vulnerabilities    │
│ compare_packages         │
│ get_changelog            │
│          │     │         │
│          ▼     ▼         │
│   PyPI API   OSV.dev     │
└──────────────────────────┘
```
