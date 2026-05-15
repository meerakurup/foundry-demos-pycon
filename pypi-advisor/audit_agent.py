"""
audit_agent.py
--------------
Python Dependency Auditor — Azure AI Foundry + Private MCP Server

Creates a Foundry prompt agent that connects to your private PyPI Auditor
MCP server (hosted on Azure Functions) and audits a requirements.txt file.
Also uses built-in Web Search and Code Interpreter tools.

Prerequisites
-------------
pip install azure-ai-projects azure-ai-agents azure-identity python-dotenv

Environment variables (put in a .env file or export):
  FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<id>
  FOUNDRY_MODEL=gpt-5
  PYPI_MCP_URL=https://<function-app>.azurewebsites.net/runtime/webhooks/mcp

Run
---
  python audit_agent.py                          # audits demo_app/requirements.txt
  python audit_agent.py path/to/requirements.txt # audits a custom file
"""

import os
import sys
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MCPTool,
    CodeInterpreterTool,
    WebSearchPreviewTool,
    PromptAgentDefinition,
)
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FOUNDRY_PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
FOUNDRY_MODEL = os.getenv("FOUNDRY_MODEL", "gpt-5")
PYPI_MCP_URL = os.environ["PYPI_MCP_URL"]

AGENT_INSTRUCTIONS = """
You are a senior Python dependency auditor. Your job is to audit a
requirements.txt and produce a clear, actionable report for a developer.

You have three tool sources:

1. **PyPI Auditor MCP tools** — use these for all package version,
   vulnerability, and changelog data. For EACH package:
   - Call get_package_info to find the latest version and staleness.
   - Call check_vulnerabilities with the PINNED version to find CVEs.
   - If a package has a popular alternative, call compare_packages.
   - Call get_changelog for any package > 6 months behind latest.

2. **Web Search** — use this to enrich CVE findings with real-world context:
   active exploits, patches, official migration guides.

3. **Code Interpreter** — use this to parse files, compute summary stats
   (% outdated, severity breakdown), or generate charts.

Format your final report as:

## Dependency Audit Report

### Summary
(stats: total packages, % outdated, critical issues count)

### 🔴 Critical Issues  (CVEs, security vulnerabilities)
### 🟠 Outdated Packages (> 6 months behind latest)
### 🟡 Minor Updates Available
### ✅ Up to Date

For each package include:
- Pinned version → Latest version
- CVEs found (with severity)
- Recommended action (upgrade, replace, or OK to keep)

Be concise. A developer should be able to act on this report immediately.
""".strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_audit(requirements_path: Path) -> None:
    requirements_text = requirements_path.read_text()

    print(f"\n📦 Auditing: {requirements_path}\n{'─' * 50}")
    print(requirements_text)
    print("─" * 50)
    print("🤖 Agent is running — this may take ~30 seconds...\n")

    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=FOUNDRY_PROJECT_ENDPOINT,
        credential=credential,
    )

    # Create a prompt agent version with MCP + built-in tools
    agent = project_client.agents.create_version(
        agent_name="PyPI-Dependency-Auditor",
        definition=PromptAgentDefinition(
            model=FOUNDRY_MODEL,
            instructions=AGENT_INSTRUCTIONS,
            tools=[
                # Private MCP server (Azure Function)
                MCPTool(
                    server_label="pypi-auditor",
                    server_url=PYPI_MCP_URL,
                    require_approval="never",
                    allowed_tools=[
                        "get_package_info",
                        "check_vulnerabilities",
                        "compare_packages",
                        "get_changelog",
                    ],
                ),
                # Built-in: real-time web search for CVE context
                WebSearchPreviewTool(),
                # Built-in: sandboxed Python for parsing & charts
                CodeInterpreterTool(),
            ],
        ),
    )

    print(f"✅ Agent created: {agent.name} (version {agent.version})")

    # Use the OpenAI Responses API to invoke the agent
    openai_client = project_client.get_openai_client()

    response = openai_client.responses.create(
        model=FOUNDRY_MODEL,
        input=f"Please audit this requirements.txt:\n\n{requirements_text}",
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    # Print the agent's text output
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "output_text":
                    print(content.text)

    # --- Interactive follow-up (live demo) ---
    print("\n" + "─" * 50)
    print("💬 Ask follow-up questions (press Enter on empty line to quit)")
    print("─" * 50)

    previous_response_id = response.id

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question:
            break

        response = openai_client.responses.create(
            model=FOUNDRY_MODEL,
            input=question,
            previous_response_id=previous_response_id,
            extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
        )
        previous_response_id = response.id

        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        print(f"\n{content.text}")

    # Keep the agent for review — print how to delete manually later
    print(f"\n✅ Audit complete. Agent '{agent.name}' (version {agent.version}) is still available in your Foundry project.")
    print(f"   To delete later: project_client.agents.delete(agent_name='{agent.name}')")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) > 1:
        req_path = Path(sys.argv[1])
    else:
        req_path = Path(__file__).parent / "demo_app" / "requirements.txt"

    if not req_path.exists():
        print(f"Error: {req_path} not found")
        sys.exit(1)

    run_audit(req_path)


if __name__ == "__main__":
    main()
