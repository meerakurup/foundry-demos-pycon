# networking-foundry

Foundry prompt-agent definition for a Microsoft Foundry network isolation expert.

## What This Agent Does

Answers architecture questions, triages customer blockers, and drafts new bug/feature work item templates for the E2E Network Isolation investment theme.

## Tools

| Tool | Type | Endpoint | Auth |
|------|------|----------|------|
| **MicrosoftLearn** | MCP | `https://learn.microsoft.com/api/mcp` | None (public) |
| **File search** | file_search | Vector store `vs_d2E3svfl32bIIFybF508tmd7` | Project-scoped |

## Files

| File | Purpose |
|------|---------|
| `agent.yml` | Deployable Foundry prompt-agent definition (instructions + tools) |
| `skills/SKILL.md` | Domain knowledge uploaded to the vector store for file search |
| `instructions.md` | Reference prompt material (not auto-loaded by Foundry) |
| `agent-metadata.example.yaml` | Template for local deployment metadata |
| `create_vector_store.py` | Script to create/update the file search vector store |

## Prerequisites

1. **An Azure subscription** with access to [Microsoft Foundry](https://ai.azure.com).
2. **A Foundry project** of your own (the reference deployment uses `mkurup-test` under `mkurup-test-resource`, but you should use yours).
3. **Model**: a `gpt-5` deployment in your project. If you deploy a different model, update the `model:` field in `agent.yml`.
4. **Azure CLI** signed in (`az login`) so `DefaultAzureCredential` can authenticate, with a role such as **Azure AI Developer** on the project.
5. **Python 3.9+** and the packages in `requirements.txt`.

## Deploy It Yourself (with your own Foundry endpoint)

The scripts currently hardcode the reference project endpoint. To deploy into your own project, follow these steps.

### 1. Get your project endpoint

In the Foundry portal, open your project → **Overview** → copy the **Project endpoint**. It looks like:

```
https://<your-resource>.services.ai.azure.com/api/projects/<your-project>
```

### 2. Authenticate and install dependencies

```bash
az login
pip install -r requirements.txt
```

### 3. Point the scripts at your endpoint

Both scripts read the project endpoint from the `ENDPOINT` environment variable (falling back to the reference project if unset). Set it to your own endpoint:

```bash
# PowerShell
$env:ENDPOINT = "https://<your-resource>.services.ai.azure.com/api/projects/<your-project>"

# bash/zsh
export ENDPOINT="https://<your-resource>.services.ai.azure.com/api/projects/<your-project>"
```

### 4. Create your own vector store

Run the script to upload `skills/SKILL.md` and `skills/DIAGRAMS.md` into a new vector store in your project:

```bash
python create_vector_store.py
```

It prints a new vector store ID (e.g. `vs_...`). Copy that ID into `agent.yml` under `tools` → `file_search` → `vector_store_ids`, replacing the existing `vs_d2E3svfl32bIIFybF508tmd7` value.

### 5. Deploy the agent

```bash
python deploy_agent.py
```

This creates the `network-isolation-expert` prompt agent (instructions + tools from `agent.yml`) in your project. Open the Foundry playground to test it.

### Alternative: deploy via the portal

You can skip the scripts entirely: in the Foundry portal go to **Agents → + New agent → Prompt agent**, then paste the contents of `agent.yml`. You'll still need to create a vector store (step 4) and update the `vector_store_ids` in the pasted definition with your own ID.

## Mermaid Diagrams

The agent produces Mermaid source in fenced code blocks. Render client-side or in any Mermaid-compatible viewer. Do not send customer architecture details to public rendering services.

## Optional Foundry Metadata

Copy `agent-metadata.example.yaml` to `.foundry/agent-metadata.yaml` and fill in your project endpoint for local tooling.
