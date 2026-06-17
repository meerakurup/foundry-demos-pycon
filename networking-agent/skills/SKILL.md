---
name: network-isolation
description: "Domain knowledge for Microsoft Foundry network isolation features — VNET, private endpoints, NSP, managed VNET, VNET injection, and agent tools VNET support."
updated: 2026-06-17
---

# Network Isolation — Domain Knowledge

## When to Use This Skill

- User asks about VNET configuration, private endpoints, NSP, or managed VNET for Microsoft Foundry 
- Triaging a customer blocker related to network isolation
- Drafting a spec or work item for a network isolation feature
- Reviewing a customer's network architecture for Foundry deployment
- Assessing enterprise readiness for network isolation features

## Do NOT Use This Skill For

- Pricing, quota, or capacity questions 
- General Azure networking unrelated to AI Foundry
- Authentication or identity questions (→ `unified-endpoint-auth` area)
- Encryption or CMK questions (→ `encryption-cmk` area)

---

## Architecture Overview

Network isolation in Microsoft Foundry breaks down into **three traffic paths** — one inbound and two outbound:

> **Diagram**: See `DIAGRAMS.md` → "Architecture Overview — Three Traffic Paths" for the visual.

| # | Path | Direction | Secured By |
|---|------|-----------|------------|
| 1 | Client → Foundry Resource | **Inbound** | PNA flag (Public Network Access disable/enable) |
| 2 | Foundry → Azure PaaS (Storage, Key Vault, AI Search, etc.) | **Outbound — Service** | NSP or Private Endpoints |
| 3 | Compute (Agents, Evals, Tracing) → External | **Outbound — Compute** | Managed VNET outbound rules |

---

## Deployment Architecture Patterns

### Pattern 1: Custom (BYO) VNET Setup

Customer-managed VNET where Foundry compute is injected directly into the customer's network. The customer has full control over outbound traffic and can optionally deploy an Azure Firewall.

> **Diagram**: See `DIAGRAMS.md` → "Pattern 1: Custom (BYO) VNET Setup" for the visual.

| Component | Description |
|-----------|-------------|
| **Inbound** | Private endpoints in dedicated PE subnet connecting to each Azure PaaS resource |
| **Compute** | Agents & Evaluations VNET-injected into a separate subnet within customer's VNET |
| **Outbound** | Customer-controlled — optional Azure Firewall for agent outbound traffic |
| **On-prem** | ExpressRoute/VPN and Bastion jump box |

### Pattern 2: Hub-and-Spoke BYO VNET Architecture

Enterprise-grade hub-and-spoke topology for BYO VNET deployments. Separates concerns across three VNETs: hub (firewall/traffic control), spoke (Foundry compute + PEs), and DNS (private zone resolution).

> **Diagram**: See `DIAGRAMS.md` → "Pattern 2: Hub-and-Spoke BYO VNET Architecture" for the visual.

| VNET | Purpose |
|------|---------|
| **Hub** | Firewall for controlling inbound (on-prem) and outbound (internet) traffic |
| **Spoke** | Agents/Evaluations compute subnet (VNET-injected) + Private Endpoint subnet for Azure PaaS |
| **DNS** | Private DNS zones for all private link domains (cognitiveservices, openai, AI services, search, documents, blob) |

All three VNETs connected via **VNET Peering**.

### Subnet Sizing & IP Allocation

This guidance applies **instance-wide** across all agent types (Hosted and Prompt). Both share the same delegated subnet and underlying ACA infrastructure.

| Parameter | Value |
|-----------|-------|
| **Recommended subnet** | /24 CIDR (251 usable IPs) for production |
| **Minimum for 50 concurrent sessions** | /26 (59 usable IPs) |
| **Minimum viable** | /27 (27 usable) — risky, caps at ~17 concurrent sessions |
| **Utilization target** | Stay below **80%** to absorb upgrade and scaling spikes |
| **Instance cap (preview)** | ~250 projects at low traffic, as few as ~25 at full scale |
| **Hosted agent limit** | ~200 hosted agents per instance |
| **Hosted revision limits** | 100 active / 1,000 total per agent |
| **Prompt agent revision limit** | 1,000 total per agent |
| **Reserved range used by Agent service infrastructure** | Do NOT use the following IP ranges: 169.254.0.0/16, 172.30.0.0/16, 172.31.0.0/16, 192.0.2.0/24,0.0.0.0/8, 127.0.0.0/8, 100.100.0.0/17, 100.100.192.0/19, 100.100.224.0/19, 100.64.0.0/11 |
| **Supported IP ranges** | RFC 1918 only: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`. No public or CGNAT (`100.64.0.0/10`) ranges. |

**Concurrent sessions by subnet size:**

| Subnet | Total IPs | Usable | Max Concurrent Sessions |
|--------|-----------|--------|------------------------|
| /27 | 32 | ~27 | ~17 |
| /26 | 64 | ~59 | ~50 (platform max per subscription per region) |
| /24 | 256 | ~251 | 50 (platform max) + headroom for upgrades |

**IP consumption model** — IPs are reserved at approximately **1 IP per 10 pods**:

| Scenario | Example | IP Usage |
|----------|---------|----------|
| Low traffic | 10 projects, each at 1 replica | ~1 IP shared across 10 pods |
| High traffic | 10 projects, each scaled to 10 replicas | 100 pods, ~10 IPs |

**Why /24 over /27:** Platform upgrades run old + new infrastructure in parallel, temporarily ~2x steady-state IP usage. At 200+ agents on a /27, upgrade + scaling events can exhaust the subnet. Don't plan to run at theoretical maximum — target 80% utilization.

**IP consumption by agent type:**
- **Hosted agents** — each revision/replica consumes IPs (parallel revisions + replicas = more pods drawing from subnet). Each Micro-VM has a dedicated NIC.
- **Prompt agents** — revisions do NOT consume IPs (data proxy runs in single-revision mode)
- **Platform upgrades** — temporarily double IP usage regardless of agent type. Timing is fully Microsoft-managed.

### Pattern 3: Managed VNET Setup

Microsoft-managed VNET where Foundry provisions and manages the network. Customer configures outbound rules but the VNET itself lives in Microsoft's tenant. Simpler setup than BYO VNET.

> **Diagram**: See `DIAGRAMS.md` → "Pattern 3: Managed VNET Setup" for the visual.

| Component | Description |
|-----------|-------------|
| **Managed VNET** | Lives in Microsoft's tenant — Foundry manages the network, customer configures outbound rules |
| **Inbound** | Customer accesses Foundry via PE from their own VNET |
| **Outbound (managed)** | PEs inside managed VNET connect to Azure PaaS resources — customer defines approved outbound rules |
| **Customer VNET** | Has its own PEs for direct access to connected resources |
| **On-prem** | ExpressRoute/VPN + Bastion to customer's VNET |

---

## Region Support

Region availability differs between BYO VNET and Managed VNET. For BYO VNET, the **supported regions depend on the IP class range** you choose — this is the most common source of confusion. **Managed VNET uses a Class A (`10.0.0.0/8`) range, so it is restricted to the same Class A region list** as BYO VNET with Class A (see below) — it is *not* available in regions that only support Class B/C.

### BYO VNET (VNET Injection) — Region Support Depends on IP Class

With BYO VNET, you may use any Private Class A, B, or C RFC 1918 range — **but Class A is region-restricted**. The Foundry resource must be deployed in the **same region as the VNet**. (Other resources — Cosmos DB, AI Search, Storage — can live in different regions, with cross-region cost implications.)

| IP Class | Range | Region Support |
|----------|-------|----------------|
| **Class A** | `10.0.0.0/8` (10.x.x.x) | **Restricted** — only the regions listed below |
| **Class B** | `172.16.0.0/12` (172.16–31.x.x) | All BYO VNET regions |
| **Class C** | `192.168.0.0/16` (192.168.x.x) | All BYO VNET regions |

**Note:** North Central US is not supported with Capability Host or BYO VNET for the Agent service. This is subject to change with engineering efforts. 

**Class A (10.x.x.x) is supported ONLY in these regions:**

Australia East, Brazil South, Canada East, East US, East US 2, France Central, Germany West Central, Italy North, Japan East, South Africa North, South Central US, South India, Spain Central, Sweden Central, UAE North, UK South, West US, West US 3.

**For any region NOT in the Class A list, you must use a Class B (`172.16.x.x`) or Class C (`192.168.x.x`) range.**

- You may **not** use any IP range that overlaps the ranges above, and public/CGNAT ranges (`100.64.0.0/10`) are never supported.
- This is the same Class A limitation called out in the VNET Injection feature section — only a handful of GA regions support Class A.
- Model deployment region availability is a separate constraint — see [Azure OpenAI model region support](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/models-sold-directly-by-azure). Your chosen region must support both the VNET/IP-class requirement **and** the model you intend to deploy.

**How to answer "which region/IP range should I use?":**
- If the customer needs a Class A (10.x.x.x) range (e.g., to fit an existing enterprise addressing scheme), confirm their target region is in the Class A list above — otherwise they must pick a different region or switch to Class B/C.
- If the customer's region isn't in the Class A list, steer them to Class B or Class C, which work in all BYO VNET regions.
- If the customer has exhausted private IP space and needs public IPs, BYO VNET will not work — VNET injection does not support public IP ranges.

### Region Expansion Roadmap (Engineering — as of June 2026)

> Source: Agents Team region-expansion plan. ETAs are engineering targets and can shift — confirm against current status before committing a customer. Use this to answer "is my region coming soon?" not as a GA guarantee.

**Phase 1 — Multiple regions build-out (BYO VNET availability).** ETA **June 15, 2026** · Owner: Agents Team. Validations are complete; these regions are being enabled for production traffic. Some regions on this list have existing V1 customers, so the rollout is **staged for those regions to reduce livesite impact**.

Regions: Japan West, UK West, Switzerland West, West Central US, Central US, West Europe, Canada Central, Japan East, Norway East, Poland Central, South India, Switzerland North, UAE North, UK South, West US.

**Phase 2 — Class A (10.x.x.x) region support expansion.** ETA **July 15, 2026** · Owner: Agents Team. Work starts **after** the Phase 1 region expansion completes. Adds Class A support to additional regions, beginning with:

Regions: Korea Central, Southeast Asia, ... (more to come).

- Until Phase 2 lands, customers needing 10.x.x.x in Korea Central / Southeast Asia (or any region not in the current Class A list) must use Class B/C with BYO VNET. **Managed VNET does not help here** — it is Class A-only and limited to the same Class A region list.
- Phase 1 expands overall BYO VNET region availability; it does **not** automatically add Class A support (for either BYO VNET or Managed VNET) — that is Phase 2.

### Managed VNET — Region Support

- Managed VNET is **subject to the Class A region restriction** — Foundry provisions the network in its own tenant and the auto-provisioned address space uses a Class A range (`10.0.0.0/8`), so the IP-class-by-region constraint does apply.
- Supporting Class B ranges with managed VNET is on the backlog for future development.


### Quick Decision Guide

| Situation | Recommendation |
|-----------|----------------|
| Need a 10.x.x.x (Class A) range | Confirm region is in the Class A list above (applies to both BYO VNET Class A and Managed VNET); for regions outside that list, use Class B/C with BYO VNET |
| Target region not in Class A list | Use Class B (`172.16.x.x`) or Class C (`192.168.x.x`) with BYO VNET — Managed VNET is **not** available (Class A-only) |
| Exhausted private IP space | Use Managed VNET (Class A regions only) |
| Want simplest setup, no VNET to manage | Managed VNET (Class A regions only) |

---

## Capability Hosts

> Source: [Capability hosts for Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/capability-hosts)

### What is a capability host?

A **capability host** is a sub-resource on the Foundry **account** and Foundry **project** that tells Foundry Agent Service **where to store and process agent data** — specifically:

- **Conversation history (threads)** → Azure Cosmos DB
- **File uploads** → Azure Storage account
- **Vector stores** (embeddings/retrieval) → Azure AI Search

It exists at **two scopes**:

| Scope | Purpose |
|-------|---------|
| **Account capability host** | Enables Agent Service at the account level. Prerequisite for any project capability host. |
| **Project capability host** | Defines which **BYO (bring-your-own) resources** Agent Service uses for that specific project. This is what Agent Service actually reads at runtime to resolve storage/thread/vector resources. |

**Two modes:**
- **No capability host (basic setup)** → Agent Service uses **Microsoft-managed** storage, threads, and vector search. Nothing to configure.
- **Capability hosts at both account + project (standard setup)** → Your own Cosmos DB, Storage, and AI Search hold all agent data, keeping it in your subscription/tenant.

**Key constraints:**
- One capability host per scope (account / project). A second one at the same scope returns **409 Conflict**.
- **No updates** — to change config you must delete and recreate.
- **No inheritance** — account-level connections can be inherited by new projects, but the project capability host config is *not* inherited; you must create a project capability host that explicitly references the connections.
- Currently managed via **REST API only** (no SDK support for capability host management).

### Why this matters for VNET / network-isolated setups

**Network isolation (BYO VNET) requires the standard agent setup, which requires capability hosts.** The two are tightly coupled:

- A **private-networking / VNET-injected** deployment is by definition a **standard setup** — agent data must live in *your* Cosmos DB, Storage, and AI Search so it stays inside your network boundary. Those resources are wired in through the **project capability host**.
- The BYO resources referenced by the capability host are exactly the ones you secure with **private endpoints** (and matching private DNS zones): Cosmos DB (`privatelink.documents.azure.com`), Storage blob (`privatelink.blob.core.windows.net`), AI Search (`privatelink.search.windows.net`).
- This is why the VNET setup flow **fails without all three BYO connections** — e.g. errors like *"Agents CapabilityHost supports a single, non empty value for storageConnections / threadStorageConnections / vectorStoreConnections"* mean a required connection is missing from the capability host.
- Each capability-host connection needs a valid `metadata.ResourceId`, `authType`, `category`, and `target` for Agent Service to resolve the (often private-endpoint-only) resource at runtime.

> **Note (upcoming change in 2026):** Engineering is planning to **obfuscate the notion of a *project* capability host from users** so that VNET-secured agents can be set up without manually wiring BYO resources/capability hosts. Treat the explicit project capability host steps above as the **current** flow that is expected to be simplified — don't over-index on it as a permanent requirement. 

---

## Agent Service Networking Deep Dive (BYO VNET)

> Source: [Deep dive into Foundry Agent Service networking](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agents-networking-deep-dive)

When running Foundry Agent Service with a bring-your-own VNet, two zones are involved: the **Microsoft-managed Foundry Platform Network** and the **Customer VNet**. The agent type (Hosted vs. Prompt) determines the internal traffic path.

### Platform-to-Customer VNet Architecture

> **Diagram**: See `DIAGRAMS.md` → "Platform-to-Customer VNet Architecture" for the visual.

**Request flows:**
- **Hosted Agent**: Client → Foundry Endpoint → Micro-VM (`/invoke`, host-level) → Tools Service (host-level) → Data Proxy → Customer Resources (PE)
- **Prompt Agent**: Client → Foundry Endpoint → Tools Service (HTTPS) → Data Proxy → Customer Resources (PE). No Micro-VM on this path.

**Security model:**
- Micro-VMs and Data Proxy only see the customer VNet interface — platform NICs are host-level (opaque to workload guest OS).
- All egress to customer resources flows exclusively through Private Endpoints in the PE subnet.
- Subnet layout: Delegated `/26` for micro-VMs + Data Proxy | PE `/26` for Private Endpoints.

### Key Concepts

| Term | Definition |
|------|-----------|
| **Foundry instance** | Top-level container that holds projects, agents, and networking configuration |
| **Hosted agent** | Agent you build and deploy via your own container image (ACR). You control CPU, memory, and code. Runs on ACA. |
| **Prompt agent** | Agent where compute and scaling are fully managed by Microsoft. Defined through configuration only — no container image or infra management. |
| **Single-tenant data proxy** | Platform-managed component dedicated to your Foundry project for outbound connectivity. Each project gets an isolated data proxy. All tool calls route through it. |
| **Tool server** | Backend service registered at project level that agents call (e.g. query a DB, invoke an API). In BYO VNet, tool traffic routes through the data proxy. |
| **Delegated subnet** | Subnet in your VNet delegated to Foundry Agent Service. All agent infra (data proxies + Micro-VMs) deploys here and consumes IPs from it. |
| **Micro-VM** | Lightweight VM that runs a Hosted agent |
| **Version** | A change that affects how an agent runs (new code, image, or config). Only runtime-affecting changes create a new version. |
| **Revision** | Deployment unit for an agent. Can be versioned (tied to a runtime change) or non-versioned (metadata-only like tags or scaling). |

### How Traffic Flows

**Inbound**: Clients send HTTPS to `<your-resource>.services.ai.azure.com`. The platform API gateway authenticates and routes by agent type.

**Hosted agent path**: Platform forwards to a Micro-VM in the delegated subnet over `/invoke`. The Micro-VM has two network paths:
- **Agent's own outbound**: Direct, through the Micro-VM's dedicated NIC in the delegated subnet.
- **Tool server calls**: Always through the single-tenant data proxy, regardless of agent type.

**Prompt agent path**: Foundry endpoint forwards directly to the Tools Service, which calls the data proxy. IPs allocated at project level — all prompt agents in a project share data proxy infrastructure.

**Egress to customer resources**: Data proxy reaches storage, databases, and Key Vault through private endpoints in the PE subnet. Requires corresponding Private DNS zones (`privatelink.blob.core.windows.net`, `privatelink.database.windows.net`, `privatelink.vaultcore.azure.net`, etc.).

### Hosted Agent Networking Behavior

- Runs on Azure Container Apps. You deploy via your own ACR.
- Each Hosted agent runs in a Micro-VM with a **dedicated NIC** in the delegated subnet.
- New deployments (image, config, code) create a **new revision**. During rollout, old + new revisions run in parallel and both consume IPs.
- **Revision limits**: 100 active / 1,000 total per agent. Oldest inactive revisions auto-purged at limit.
- ~200 Hosted agents per instance (preview). Separate from the ~250 project cap.
- Custom CPU and memory configurations supported — select from available pairs at version creation.
- Scaling doesn't introduce latency — performance is only affected if IP exhaustion prevents scale-out.

### Prompt Agent Networking Behavior

- Also runs on ACA, but compute and scaling are fully Microsoft-managed. No CPU/memory config.
- Revisions **do not consume IPs** — data proxy runs in single-revision mode.
- Uses the single-tenant data proxy for all outbound. IPs allocated at project level.
- No hard limit on prompt agents per Foundry instance. No expected latency issues from agent count.

### VNet Peering and IP Overlap

- All peered VNets must use **unique, non-overlapping IP ranges** — overlapping ranges cause routing failures.
- Only RFC 1918 private IPv4 ranges supported. **CGNAT addresses (e.g. `100.64.0.0/10`) are not supported** and cause routing failures.
- If IP overlap is unavoidable, use [Managed VNet](https://learn.microsoft.com/en-us/azure/foundry/how-to/managed-virtual-network) instead — it automates network setup and eliminates overlap concerns.

### Monitoring IP Usage and Detecting Exhaustion

The Azure portal **does not currently expose IP utilization** for delegated subnets. Primary indicators of IP exhaustion:

| Signal | Meaning |
|--------|---------|
| Data proxy returning **HTTP 5xx** | Data proxy can't scale — IPs exhausted |
| Hosted agent session creation **4xx errors** | Can't allocate Micro-VM for new sessions |
| New project provisioning failures | No IPs available for new project data proxy |

**Mitigation**: Deploy a new Foundry instance with a fresh subnet when these signals appear. The platform does **not** proactively warn when IP capacity is low.

---

## Feature Landscape

### Recent update snapshot (June 2026)
- **Hosted agents + private ACR**: Public ACR remains the generally available preview path. Private-network-secured ACR is now in **private preview** for hosted agents; treat it as allowlist/private-preview only, not broadly available customer guidance.
- **Fabric Data Agent behind VNET**: Still **unsupported today**. It currently requires Fabric public network access; Fabric workspace-level private link is not supported for this integration. Engineering is actively fixing this now, so describe it as an active gap rather than a dead-end capability.
- **Agent tools behind VNET**: Do not imply all tools work just because the Foundry resource is VNET-isolated. Several tools still bypass, require public endpoints, or are under development. Always separate **BYO/custom VNET** support from **Managed VNET** support.
- **Managed VNET post-GA work**: Key follow-ups are agent/tool validation, missing CLI/SDK commands and adding support in GA version (current preview version SDK/CLI support), firewall/traffic logging, and hosted-agent private ACR validation via ACR private endpoint.

### 1. NextGen Private Network
- **Also known as**: NextGen network isolation, E2E network isolation, end-to-end private networking, private networking in Microsoft Foundry, private endpoint support in Microsoft Foundry, PE support in Foundry
- **What**: NextGen refers to the new UI for Microsoft Foundry. The UI used to be called mainline which is the old UI that is not built for developers. The new one called NextGen internally is built for developers who want to build AI Agents. NextGen Private Network is the network isolation support in the new UI. When a user sets inbound network isolation to Disabled or Selected networks - they should be able to use securely access the Foundry resource without any errors if they have added their necessary IPs or are using a private endpoint. 
- **Status**: Delivered in March 2026. At Ignite 2025, this experience was broken. It was fixed in March 2026 and is now supported for all customers. 
- **Key concept**: Disallows any data plane actions to be taken if the user is not coming from a secured network via Private endpoints or specified IP. 
- **Customer value**: Full network isolation for agent building, evaluations, fine-tuning. 
- **Common questions**:
  - "How is this different from the old AOAI private endpoint?" → NextGen uses Foundry-native endpoints vs. Cognitive Services endpoints. 
  - "Can I migrate from AOAI private endpoints?" → Not yet, but we are working on it this quarter. There are two additional DNS zones needed for Foundry private endpoint than AOAI needed. 

### 2. Managed VNET (GA Readiness)
- **Also known as**: Managed virtual network support, Foundry-managed VNET
- **What**: Azure-managed virtual network for Foundry workspaces — customers don't manage the VNET directly
- **Key concept**: Foundry provisions and manages the VNET, customer configures approved outbound rules
- **Modes**: 
  - **Allow Internet Outbound** — allows outbound to internet, no firewall created
  - **Allow Only Approved Outbound** — strict, only pre-approved destinations, creates a firewall to track outbound access
- **Customer value**: Simpler setup than VNET injection, suitable for most enterprise scenarios
- **Region availability**: Managed VNET uses a Class A (`10.0.0.0/8`) address space, so it is **restricted to the Class A region list** (see [Region Support](#region-support)). It is **not** available in regions that only support Class B/C. Class B support for Managed VNET is on the backlog.
- **Common questions**:
  - "Can managed VNET access my on-prem resources?" → Yes, via private endpoints to ExpressRoute/VPN gateways
  - "What about compute targets?" → All compute (training, inference) runs inside the managed VNET
- **Issues / post-GA work**: Agent tools still need feature-by-feature validation behind Managed VNET; do not assume a tool works unless it is explicitly validated. Firewall/traffic logs are not available yet. CLI coverage is still catching up for some network flows. Hosted agents with private ACR are in private preview only and require ACR private endpoint validation; public ACR remains the standard preview path.
- **ADO Item**: [Managed VNET Support in FDP Foundry (Post GA)](https://dev.azure.com/msdata/Vienna/_boards/board/t/AICoreEnterpriseNetworking/Epics?workitem=5294708)

### 3. Agent Tools VNET Support
- **What**: Ensuring AI agent tool calls (Grounding with Search, Function Calling, Code Interpreter, OpenAPI, Fabric Data Agent, Logic Apps, File Search, Browser Automation, Computer Use, etc.) work within network-isolated environments.
- **Key challenge**: Agent tools often need to call external services. Some tools can route through the customer's VNET or private endpoints; others still use Microsoft backbone/public endpoints or are not yet VNET-ready.
- **Customer value**: Agents can be deployed in fully isolated environments without losing tool capabilities
- **Important scoping**: The matrix below is for **custom/BYO VNET** unless otherwise stated. Managed VNET support is less mature and must be validated per tool.

| Tool | BYO/custom VNET status | Managed VNET status | Traffic path / notes |
|------|------------------------|---------------------|----------------------|
| MCP Tool (Private MCP) | **Supported** | **Validate per scenario** | Through your VNet subnet / data proxy to private MCP endpoint |
| Azure AI Search | **Supported** | **Supported when private endpoint/outbound rule is configured** | Through private endpoint |
| Code Interpreter | **Partial** | **Partial / validate** | Microsoft backbone. Works without files. File upload/download not supported; workaround: use SDK to create a container with required files and pass `container_id` to Code Interpreter. Workaround not available in Foundry portal UI. |
| Function Calling | **Supported** | **Validate per scenario** | Microsoft backbone network unless the function target is a private endpoint-enabled service |
| Bing Grounding | **Supported** | **Requires allowed public egress** | Public endpoint |
| Web Search | **Supported** | **Requires allowed public egress** | Public endpoint |
| SharePoint Grounding | **Supported** | **Requires allowed M365/public egress** | Public endpoint |
| Foundry IQ (preview) | **Supported** | **Validate per scenario** | Via MCP |
| OpenAPI Tool | **Supported** | **Validate per scenario** | Through your VNet subnet when target is private/network-reachable |
| Azure Functions | **Supported** | **Validate per scenario** | Through your VNet subnet/private endpoint when configured |
| A2A (Agent-to-Agent) | **Supported** | **Validate per scenario** | Through your VNet subnet when both sides are network-reachable |
| Fabric Data Agent | **Not supported today; fix in progress** | **Not supported today; fix in progress** | Currently requires Fabric public network access. Fabric workspace-level private link is not supported for this integration yet. Track as active engineering work, not as customer-ready. |
| Logic Apps | **Not supported** | **Not supported** | Under development |
| File Search | **Not supported** | **Not supported** | Under development |
| Browser Automation | **Not supported** | **Not supported** | Under development |
| Computer Use | **Not supported** | **Not supported** | Under development |
| Image Generation | **Not supported** | **Not supported** | Under development |

**How to answer tool-gap questions:**
- Be explicit that "the agent is behind a VNET" does **not** automatically mean every tool call stays private or works.
- For private data sources, prefer tools with an explicit private-network path (Private MCP, OpenAPI/Azure Functions to private endpoints, AI Search via private endpoint).
- For public SaaS or M365 grounding tools, confirm whether the customer's policy allows required public/Microsoft egress.
- For Fabric Data Agent, say: "Unsupported today behind VNET/Fabric private link, but engineering is actively fixing it." Do not claim a committed ETA unless one is provided in the active work item.
- **ADO Item**: [Agent Tools VNET support](https://dev.azure.com/msdata/Vienna/_workitems/edit/5116830) 

### 4. Private Endpoints
- **What**: Azure Private Link endpoints that give Foundry resources a private IP address on the customer's VNET
- **Key resources that support private endpoints**: 
  - AI Foundry workspace (hub and project)
  - Azure OpenAI / model endpoints
  - Storage accounts (for training data, artifacts)
  - Azure AI Search (for RAG patterns) 
  - Key Vault (for secrets management)
- **Customer value**: All traffic stays on the Microsoft backbone, never traverses public internet
- **DNS Confusion**: Specifically the private endpoint used inbound to access Microsoft Foundry has 3 DNS zones. They are: privatelink.services.ai.azure.com, privatelink.openai.azure.com, privatelink.cognitiveservices.azure.com. Make sure customers know the 1 PE has 3 DNS zones associated with it. 
- **Common questions**:
  - "Do I need a private endpoint for each service?" → Yes, each Azure service the Foundry workspace connects to needs its own PE
  - "What about DNS?" → Private DNS zones must be configured correctly — this is the #1 support issue
  - "I have an inbound PE for Foundry, and I set the PNA flag to disabled, but I still can't access my workspace. Why?" → Customer is not securely access Foundry from their laptop/on-prem. There are three ways to access Foundry secured by a VNET (aka PNA disabled with PE inbound). 1. Azure VPN Gateway 2. Bastion VM 3. ExpressRoute. More information on this in the reference docs for Private endpoints. 


### 5. NSP (Network Security Perimeter)
- **What**: Azure Network Security Perimeter — a logical boundary around Azure PaaS resources that enforces network access rules
- **Key concept**: NSP provides a declarative, policy-based approach vs. per-resource private endpoint configuration
- **Customer value**: Simplified management at scale — define perimeter once, apply to multiple resources
- **Status**: GA for Microsoft Foundry.
- **Common questions**:
  - "How does NSP relate to private endpoints?" → NSP is complementary — it can replace some PE configurations for PaaS-to-PaaS communication.
  - "Is NSP supported for AI Foundry?" → Yes, NSP is GA for Microsoft Foundry
- **Unsupported**: NSP Foundry is not supported for Hosted Agents. NSP Foundry does not support Service Tags for inbound rules. NSP Foundry does not support Cross Perimeter rules yet. We are working on adding support for these features in future releases. 
- **ADO Item**: [NSP Network Security Perimeter Readiness](https://dev.azure.com/msdata/Vienna/_workitems/edit/4938528)

### 6. VNET Injection
- **Also known as**: Customer-managed VNET, Bring Your Own VNET, BYO VNET, custom VNET.
- **What**: Customer-managed VNET where Foundry Agent and Evaluations client compute is injected directly into the customer's network.
- **Key concept**: Customer creates and manages the VNET, Foundry deploys compute into designated subnets. Only the Agent client is injected — the Foundry service itself is NOT in the VNET.
- **Customer value**: Full control over network topology, NSG rules, routing tables
- **Trade-off**: More complex setup and management vs. managed VNET, only supports Private Class A, B, C IP ranges, Supports Private Class A in only a handful of regions in GA, Will not work for customers who have exhaused their private IP space and need to use public IPs with NSG rules for isolation. VNET injection does NOT support public IP ranges. 
- **On-prem connectivity**: With BYO VNET, agents inherit existing hybrid connectivity — ExpressRoute, Site-to-Site VPN, or Point-to-Site VPN. Agent traffic follows customer-defined NSGs/UDRs. With Managed VNET, direct on-prem routing is not available — use PE outbound rules to reach Azure-accessible resources instead.
- **Network policy scope**: NSGs, UDRs, and NSP rules apply at the **subnet/instance level**, not per-individual-agent. To apply different network policies to different agents, use separate Foundry instances in separate subnets.
- **Common questions**:
  - "When should I use VNET injection vs. managed VNET?" → VNET injection when you need full control over network config + hybrid/on-prem connectivity. Managed VNET for simpler setup without a customer VNET.
  - "What subnet requirements exist?" → /24 recommended (see Subnet Sizing section above). Same region/subscription as the custom VNET due to Class A limitation. 
  - "Can agents reach on-prem resources?" → Yes, via whatever hybrid connectivity (ExpressRoute/VPN) exists on the VNET. Agent client runs in your VNET so it inherits your routing.

### 7. AI Gateway / APIM Integration
- **What**: Azure API Management (APIM) as an AI Gateway in front of Foundry resources
- **Status**: Partially supported. BYO AI Gateway is a partner dependency on the APIM team. The only supported version of APIM with virtual network isolation e2e is: APIM v2 PE + VNet integration and APIM v2 VNet Injection.  
- **Key behavior**: Creating an AI Gateway with a private Foundry resource results in an **automatically public** gateway. To use with a private Foundry, the APIM instance must also have network isolation configured separately.
- **VNET support**: APIM in VNET is supported via Private Endpoint.
- **Non-APIM gateways**: No first-party BYO gateway feature. With BYO VNET, customers can place any reverse proxy (NGINX, Kong, F5, etc.) in front of the agent endpoint using standard VNET routing — customer owns gateway config, TLS, and rate limiting.
- **Reference**: [Networking for AI Gateway](https://learn.microsoft.com/azure/api-management/virtual-network-concepts)


### 8. Publish Agents to M365/Teams behind a VNET
- **Also known as**: Publish to Teams, Teams integration, M365 Copilot publish, agent-to-Teams behind private endpoint
- **What**: Publishing a Foundry agent that is deployed behind a private endpoint (PNA disabled) to Microsoft Teams and Microsoft 365 Copilot, so end users can interact with the agent as a Teams chat bot.
- **Key challenge**: The Foundry Portal "Publish to Teams" button does **not work** when PNA is disabled — it requires public network access. Enterprise customers must use a **programmatic approach** and deploy additional inbound network infrastructure to allow the Bot Service Connector to reach the agent's private messaging endpoint.
- **Customer value**: Users interact with agents directly in Teams without leaving their collaboration tool, while maintaining full network isolation for the agent backend.
- **Status**: Officially documented as an **Early Access Preview**. The manual REST API flow below is the supported replacement for the one-click **Publish to Teams and Microsoft 365 Copilot** button when PNA is disabled. The Microsoft 365 publish API itself is still in preview (GA planned; request format may change).

- **Programmatic steps** (per the official Learn doc — steps 1–4 are the manual equivalent of the one-click button; step 5 is only needed when PNA is disabled):
  1. **Get the agent identity and tenant ID** — get a bearer token for the `https://ai.azure.com` audience, call **Agents - Get agent** to read `instance_identity.principal_id` and `versions.latest.agent_guid`, then get your tenant ID via `az account show --query tenantId -o tsv`.
  2. **Create the Azure Bot Service resource** — deploy via Bicep with `publicNetworkAccess: 'Disabled'`, `msaAppType: 'SingleTenant'`, the agent principal ID as `msaAppId`, your tenant ID as `msaAppTenantId`, and an `MsTeamsChannel`. The bot `endpoint` is the agent's activity protocol endpoint.
  3. **Enable the activity protocol + Bot Service authorization** — PATCH the agent (Agents - Update agent) to add the `activity` protocol and a Bot Service auth scheme. Keep `responses` and `Entra` in the lists or you break Foundry portal/SDK chat.
  4. **Call Foundry's Microsoft 365 publish API** — POST to the `…/microsoft365/publish` endpoint with `agentGuid`, `botId` (agent principal ID), and store metadata. The agent isn't reachable from Teams/Copilot until step 5.
  5. **Configure networking for inbound + outbound traffic** — establish the public entry point, TLS termination, and outbound allowances (required only when PNA is disabled).
  - Python example for steps 1–4: [publish-agent notebook](https://github.com/mattfeltonma/azure-terraform-lab-base-azfw/blob/main/workloads/microsoft-foundry/sample-code/publish-agent-teams/publish-agent.ipynb). Internal deep-dive with Bicep/scripts: `publish-agent-byo-vnet.md`.

- **Authorization scheme vs. visibility** (set independently):
  - **Calling** — Bot Service auth scheme on the agent endpoint: `BotServiceRbac` (only identities with Azure permission to call the agent in Foundry) or `BotServiceTenant` (everyone in your tenant).
  - **Visibility** — `appPublishScope` in the publish request: `Shared` (just you; appears under *Your agents*, shared via link) or `Tenant` (whole org after Microsoft 365 admin approval; appears under *Built by your org*).
  - These can be mixed — e.g. publish `Tenant` for visibility but restrict calling with `BotServiceRbac`.

- **Inbound traffic flow** (Teams → Agent):
  - Teams Service → Bot Service Connector → **your public IP infrastructure** (App Gateway, Firewall, etc.) → APIM (optional, for JWT validation) → Foundry Private Endpoint → Agent compute.
  - The **response** from agent back to Bot Service egresses through the Microsoft-managed network, **not** through the customer VNet. Inbound and outbound are separate async TCP sessions — not symmetric routing.

- **Outbound for replies**: The agent's reply path must allow outbound to `smba.trafficmanager.net`, `login.microsoftonline.com`, and `login.botframework.com`. If outbound is blocked, the agent receives messages but never replies.

- **Inbound network requirements**:
  - **Public entry point**: At least one component with a public IP (App Gateway, Azure Firewall DNAT, load balancer) to accept traffic from the Bot Service Connector.
  - **TLS termination**: Must terminate TLS and present a valid certificate for the hostname.
  - **Messaging endpoint modification**: Update the Bot Service messaging endpoint FQDN to point to your proxy (e.g., `https://<your-appgw>/agents/api/projects/...`).
  - **Source IP restriction**: Lock inbound to Teams IP ranges `52.112.0.0/14` and `52.122.0.0/15` ([M365 IP ranges](https://learn.microsoft.com/en-us/microsoft-365/enterprise/urls-and-ip-address-ranges?view=o365-worldwide#microsoft-teams)).

- **Authentication & authorization**:
  - Bot Service Connector sends a **signed JWT** issued by `https://api.botframework.com`, audience = agent's principal ID, with a `serviceurl` claim containing your tenant ID.
  - **Foundry validates the JWT natively** — no extra config needed in most cases.
  - For defense-in-depth, validate the JWT at your proxy layer (APIM `validate-jwt` policy). See `publish-agent-byo-vnet.md` for the full APIM policy XML.
  - The `x-tenant-id` request header (set by the Bot Channel Adapter with the caller's tenant ID) can also be checked at the WAF level for lightweight tenant validation — reject any request whose tenant ID isn't your own.

- **Architecture patterns for inbound**:

  | Pattern | Description |
  |---------|-------------|
  | **App Gateway + APIM v2** (recommended) | WAF for source IP + tenant header validation, APIM v2 (VNet-injected or PE + VNet integration) for JWT validation. No public IP on APIM. |
  | **App Gateway + APIM classic** | Same but APIM classic in VNet injection mode. |
  | **APIM v2 public inbound** | APIM v2 with public inbound + regional VNet integration. Simpler, but APIM has a public IP. |
  | **APIM classic external mode** | APIM classic configured for external mode. |
  | **Firewall DNAT + APIM v2** | Azure Firewall DNAT rule, APIM v2 behind it. |
  | **Firewall DNAT + APIM classic** | Azure Firewall DNAT rule, APIM classic with VNet injection. |

- **End-user RBAC**: Users interacting with the agent in Teams must hold the **Foundry User** (formerly Azure AI User) RBAC role on the Foundry resource. Without it, they get an auth failure after sign-in. Teams App Catalog controls who *sees* the agent; Foundry RBAC controls who can *use* it.

- **Portal publish button limitations**:
  - Requires **Contributor or Owner** at the resource group/subscription level (auto-provisions Bot Service).
  - Requires **PNA enabled** on the Foundry resource (expected to change in a future update).
  - The programmatic approach (REST API) avoids both limitations.

- **Bot Service Private Link does NOT help here**: Bot Service Private Link only covers the Direct Line channel. The Teams channel always sends traffic from the Microsoft public backbone, so a publicly reachable entry point is required regardless.

- **Known open item**: Outbound traffic from the Foundry Agent subnet to `tenant.api.powerplatform.com` (with tenant ID in FQDN) has been observed. Purpose still being clarified with the product group.

- **Common questions**:
  - "Can I publish a VNet-isolated agent to Teams?" → Yes, but not via the portal button. Use the programmatic REST API approach and deploy inbound network infrastructure (App Gateway + APIM recommended).
  - "Do I need APIM?" → APIM is recommended for JWT validation (defense-in-depth). At minimum you need *something* with a public IP that can route to the Foundry PE. Header-level `x-tenant-id` validation at the WAF (paired with a source-IP restriction) is a lighter alternative if full JWT validation is too complex.
  - "Why can't I just enable Bot Service Private Link?" → Bot Service Private Link only covers Direct Line, not the Teams channel. Teams traffic always comes from the Microsoft public backbone.
  - "What permissions do Teams users need?" → Foundry User RBAC role on the Foundry resource.

- **References**:
  - [Publish a virtual network agent to Microsoft 365 and Teams](https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/publish-copilot-virtual-network) — **official Microsoft Learn doc** (manual REST API flow, Bicep, inbound/outbound networking, troubleshooting)
  - [Foundry Agents through the Corporate Firewall](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/foundry-agents-and-custom-engine-agents-through-the-corporate-firewall/4502218) — Graeme Foster (official recommendation)
  - [Publishing Agents to Teams Deep Dive — Part 1](https://journeyofthegeek.com/2026/05/20/microsoft-foundry-publishing-agents-to-teams-deep-dive-part-1/) — Matt Felton (portal walkthrough, Bot Service internals, JWT anatomy)
  - [Publishing Agents to Teams Deep Dive — Part 2](https://journeyofthegeek.com/2026/05/22/microsoft-foundry-publishing-agents-to-teams-deep-dive-part-2/) — Matt Felton (App Gateway + APIM architecture, APIM JWT policy, programmatic setup)
  - [Publish Agent Notebook (Python/Terraform)](https://github.com/mattfeltonma/azure-terraform-lab-base-azfw/blob/main/workloads/microsoft-foundry/sample-code/publish-agent-teams/publish-agent.ipynb) — Matt Felton
  - [Bot Framework REST API Authentication](https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-authentication?view=azure-bot-service-4.0)


### 9. Hosted Agents (preview) behind a VNET
- **What**: Hosted agents call models from the Foundry model catalog to perform reasoning while your custom code handles orchestration. By using this managed platform, you can deploy and operate AI agents securely and at scale. You can use your custom agent code or a preferred agent framework with streamlined deployment and management. 
- **Status**: Supported in preview with a public Azure Container Registry (ACR). Works with both custom VNET and managed VNET. **Private ACR is now in private preview** for hosted agents and should be described as allowlist/private-preview only.
- **Key behavior**: Hosted agents support deployment within network-isolated Foundry resources and can use a customer-provided Azure Virtual Network for outbound traffic. This enables agents in network-isolated Foundry deployments to reach private resources such as databases or internal APIs. The standard preview path still expects the ACR image source to be reachable over its public endpoint. Private-network-secured ACR requires the private preview path plus ACR private endpoint validation.
- **VNET support**: Hosted agents can be deployed in both BYO VNET and Managed VNET environments. In BYO VNET, the agent's outbound traffic routes through the customer's network. In Managed VNET, outbound traffic is controlled by Foundry-managed rules.  
- **Private ACR guidance**: If a customer asks for private ACR, do not say "unsupported" flatly anymore. Say: "Private ACR for hosted agents is in private preview; standard preview uses public ACR. We need private-preview enablement/allowlisting and validation with ACR private endpoint."

---

## Common Customer Scenarios

### Scenario A: "We need full network isolation for our AI workloads"
**Recommended pattern:**
1. Create Foundry workspace with managed VNET (Allow Only Approved Outbound)
2. Configure private endpoints for Storage, Key Vault, AI Search
3. Set up private DNS zones
4. Configure approved outbound rules for any external dependencies
5. Test agent tools within the isolated environment

### Scenario B: "We have existing on-prem infrastructure and need hybrid connectivity"
**Recommended pattern:**
1. VNET injection into customer-managed VNET
2. ExpressRoute or VPN gateway for on-prem connectivity
3. Private endpoints for all Azure PaaS services
4. UDR (User-Defined Routes) for traffic steering
5. NSG rules for east-west traffic control

### Scenario C: "We're migrating from AOAI with private endpoints to Foundry"
**Recommended pattern:**
1. Assess current AOAI PE configuration
2. Create Foundry workspace with matching network isolation level
3. Migrate model deployments (use AOAI→Foundry upgrade theme guidance)
4. Update DNS records and PE configurations
5. Validate inference works through new endpoints
6. Decommission old AOAI PE resources

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| "Connection refused" to model endpoint | Private endpoint DNS not resolving | Verify private DNS zone is linked to VNET, check `nslookup` |
| Agent tool calls timing out | Outbound rules blocking tool service access | Add approved outbound rule for the tool's service endpoint |
| "403 Forbidden" on storage access | Storage firewall blocking Foundry | Add Foundry workspace managed identity to storage network rules |
| Slow inference in isolated workspace | Traffic routing through unexpected path | Check UDR table, verify no hairpin routing through on-prem |
| Cannot create private endpoint | Subnet delegation conflict | Use a dedicated subnet without other delegations |
| Code Interpreter can't access files | File upload/download not supported in VNet-isolated environments | Use SDK to create a container with required files and pass `container_id` to Code Interpreter (not available in portal UI) |
| Data proxy returning HTTP 5xx | IP exhaustion — data proxy can't scale | Deploy new Foundry instance with fresh subnet. Monitor data proxy health as leading indicator. |
| Hosted agent session creation 4xx | IP exhaustion — can't allocate Micro-VM | Check subnet utilization (no portal metric yet). Deploy new instance if at capacity. |
| New project provisioning failures | No IPs available for new data proxy | Scale down existing projects or deploy new Foundry instance with fresh subnet |

> **Note**: The Azure portal does not currently expose IP utilization for delegated subnets. The signals above are the primary indicators of capacity issues.

---

## Reference Docs (External)

Fetch these when answering detailed technical questions:
- Private endpoints: `https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/configure-private-link?view=foundry`
- Managed VNET: `https://learn.microsoft.com/en-us/azure/foundry/how-to/managed-virtual-network?tabs=azure-cli`
- NSP: `https://learn.microsoft.com/en-us/azure/ai-foundry/how-to/add-foundry-to-network-security-perimeter?view=foundry`
- VNET integration overview: `https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/virtual-networks?view=foundry`
- Access on-prem resources: `https://learn.microsoft.com/en-us/azure/foundry/how-to/access-on-premises-resources?tabs=azure-cli`
- Deep dive networking for Agents: `https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/agents-networking-deep-dive`
- Networking for AI Gateway: `https://learn.microsoft.com/azure/api-management/virtual-network-concepts`


