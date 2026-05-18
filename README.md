# foundry-demos-pycon

Fun Microsoft Foundry demos for PyCon 2026. This repo collects small, conference-friendly agents that show different ways to combine Foundry models, built-in tools, MCP, Streamlit, and Azure services.

## Agents and demos

### [CSV Whisperer](csv-whisperer/README.md)

A chat-style CSV analysis agent that lets users pick a sample dataset or upload their own CSV, then ask questions in plain English. The agent inspects the data, runs Python analysis, and creates charts when a visual answer helps.

**Agent:** `csv-whisperer/agent.py` configures the Foundry/OpenAI Responses API call and Code Interpreter workflow.

**Tech stack:** Microsoft Foundry, OpenAI Responses API, Code Interpreter, Python, Streamlit, pandas-style analysis, matplotlib chart generation, Azure `DefaultAzureCredential` authentication.

### [Prompt to Product](prompt-to-product/)

A product ideation agent that turns a short product description into launch-ready marketing copy and a rendered landing page with a generated hero image.

**Agent:** `prompt-to-product/agent.py` runs the copywriting and image-generation pipeline.

**Tech stack:** Microsoft Foundry, GPT-5.4 for structured marketing copy, MAI-Image-2e for image generation, Azure AI Projects, OpenAI client, Python, Streamlit, Jinja2 templates, Azure `DefaultAzureCredential` authentication.

### [PyPI Dependency Auditor](pypi-advisor/README.md)

A dependency auditing agent that reviews a `requirements.txt`, checks pinned packages for stale versions and known vulnerabilities, and produces a practical remediation report.

**Agent:** `pypi-advisor/audit_agent.py` creates and invokes the `PyPI-Dependency-Auditor` Foundry prompt agent.

**Tech stack:** Microsoft Foundry Agents, Azure AI Projects, Azure AI Agents SDK, Python, private MCP server on Azure Functions, PyPI API, OSV.dev vulnerability data, built-in Web Search, built-in Code Interpreter, Azure `DefaultAzureCredential` authentication.

### [Network Isolation Expert](networking-agent/README.md)

A Microsoft Foundry prompt agent for enterprise network-isolation questions, customer-blocker triage, architecture diagrams, and work item drafting.

**Agent:** `networking-agent/agent.yml` defines the deployable `network-isolation-expert` Foundry prompt agent.

**Tech stack:** Microsoft Foundry prompt-agent YAML, GPT-5, MCP project connections to WorkIQ Teams, OneDrive, and Mail, embedded domain instructions, Mermaid diagram output, optional local deployment metadata.

## Supporting demo assets

- `csv-whisperer/data/` includes sample coffee sales, movie ratings, and PyPI downloads CSV files.
- `pypi-advisor/mcp_server/` contains the Azure Functions MCP server with package metadata, vulnerability, comparison, and changelog tools.
- `pypi-advisor/demo_app/` and `pypi-advisor/demo_legacy_api/` provide intentionally stale sample applications for dependency-audit demos.
- `prompt-to-product/templates/` contains the landing-page HTML template rendered by the Streamlit app.
