# networking-foundry

Foundry prompt-agent definition for a Microsoft Foundry network isolation expert.

## Runtime File

- `agent.yml` is the deployable Foundry prompt-agent definition.
- The agent is intentionally self-contained: the full behavior and core domain knowledge live in the `instructions` block because Foundry prompt agents do not automatically load local Markdown files.
- `model` is set to `gpt-5`, which is deployed in the `mkurup-test-resource` Foundry resource. Change this value if you want to use a different model deployment.
- `temperature` is intentionally omitted because the deployed `gpt-5` model does not support it.
- The agent uses direct WorkIQ catalog MCP connections for Teams, OneDrive, and Mail. The custom Logic App toolbox source is excluded until its 403 auth issue is fixed.
- Mermaid diagram support is implemented in the prompt instructions. The agent emits fenced `mermaid` blocks that render in Mermaid-compatible clients without sending private content to a public renderer.

## Source Reference Files

- `instructions.md` is the original source/reference prompt material.
- `skills/SKILL.md` is the original domain knowledge source used to build the embedded instructions.
- Updating either reference file does not change the deployed agent until the relevant content is copied into `agent.yml`.

## Deploy Shape

The Foundry prompt-agent definition should keep this shape:

```yaml
kind: prompt
name: network-isolation-expert
model: gpt-5
instructions: |
  ...self-contained system instructions...
```

Avoid `instructions: file:...` and `knowledgeFiles:` for this package unless the target deployment tool explicitly documents support for them.

## WorkIQ Tools

The deployed agent uses the working catalog MCP project connections directly:

```yaml
tools:
  - type: mcp
    server_label: WorkIQTeams
    server_url: https://agent365.svc.cloud.microsoft/agents/servers/mcp_TeamsServer
    project_connection_id: WorkIQTeams
    require_approval: always
  - type: mcp
    server_label: WorkIQOneDrive
    server_url: https://agent365.svc.cloud.microsoft/agents/servers/mcp_OneDriveRemoteServer
    project_connection_id: WorkIQOneDrive
    require_approval: always
  - type: mcp
    server_label: WorkIQMail
    server_url: https://agent365.svc.cloud.microsoft/agents/servers/mcp_MailTools
    project_connection_id: WorkIQMail
    require_approval: always
```

The `meera-workiq-toolbox` wrapper endpoint is not used by the deployed agent because the toolbox version includes a custom Logic App MCP source, `meeraworkiqmcp`, that currently returns HTTP 403 during tool enumeration.

## Mermaid Diagrams

The agent can produce visual diagrams by returning Mermaid source in Markdown:

````markdown
```mermaid
flowchart LR
  Client[Client] --> PrivateEndpoint[Private endpoint]
  PrivateEndpoint --> Foundry[Microsoft Foundry]
  Foundry --> Storage[Storage / Search / Key Vault]
```
````

This is intentionally prompt-native rather than an MCP tool because public Mermaid renderers are HTTP services, not Foundry MCP servers. For confidential diagrams, keep rendering client-side or use a private renderer. Do not send customer architecture, tenant IDs, private IPs, or endpoint names to public rendering services.

## WorkIQ Toolbox Pending Auth

The toolbox MCP endpoint is:

```yaml
tools:
  - type: mcp
    server_label: meera-workiq-toolbox
    server_url: https://mkurup-test-resource.services.ai.azure.com/api/projects/mkurup-test/toolboxes/meera-workiq-toolbox/versions/1/mcp?api-version=v1
    headers:
      Foundry-Features: Toolboxes=V1Preview
    require_approval: always
```

Do not commit bearer tokens. A deployment with the toolbox MCP tool but no `Authorization` header failed invocation with a 401 from the toolbox endpoint. The deployed agent uses direct WorkIQ catalog project connections instead.

## Optional Foundry Metadata

Use `.foundry/agent-metadata.example.yaml` as the starting point for local deployment metadata. Copy it to `.foundry/agent-metadata.yaml` and fill in your project endpoint when you are ready to deploy or invoke the agent from tooling.
