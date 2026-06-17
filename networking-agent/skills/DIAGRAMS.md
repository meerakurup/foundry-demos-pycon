# Network Isolation — Architecture Diagrams

> Visual reference for Microsoft Foundry network isolation patterns. These diagrams complement the domain knowledge in `SKILL.md`. Render with any Mermaid-compatible viewer.

---

## Architecture Overview — Three Traffic Paths

```mermaid
flowchart LR
    subgraph foundry["Microsoft Foundry Resource Boundary"]
        direction TB
        resource["Microsoft Foundry\nResource"]
        compute["Computing Resources\n(Agents, Evals,\nTracing, etc.)"]
    end

    inbound["1) INBOUND\nClient Access"] -->|"PNA Flag\n(Public Network Access\ndisable/enable)"| resource

    resource -->|"2) OUTBOUND — Service\nFoundry → Azure PaaS"| paas

    subgraph paas["Azure PaaS Resources"]
        direction TB
        storage["Storage"]
        kv["Key Vault"]
        search["AI Search"]
        cosmos["Cosmos DB"]
    end

    compute -->|"3) OUTBOUND — Compute\nManaged VNET rules"| ext["External / Internet"]

    inbound ~~~ sec1["🔒 Secured by:\nPNA flag on Foundry resource"]
    paas ~~~ sec2["🔒 Secured by:\nNSP or Private Endpoints"]
    ext ~~~ sec3["🔒 Secured by:\nManaged VNET\noutbound rules"]

    style foundry fill:#e8f4fd,stroke:#0078d4,stroke-width:2px
    style resource fill:#fff,stroke:#0078d4
    style compute fill:#fff,stroke:#0078d4
    style paas fill:#fff8e8,stroke:#d4a017,stroke-width:2px
    style sec1 fill:#e8ffe8,stroke:#2d8f2d
    style sec2 fill:#e8ffe8,stroke:#2d8f2d
    style sec3 fill:#e8ffe8,stroke:#2d8f2d
```

---

## Pattern 1: Custom (BYO) VNET Setup

```mermaid
flowchart TB
    subgraph azure_resources["Your Azure Resources for AI Agent Service"]
        direction LR
        storage["Azure\nStorage"]
        search["AI Search"]
        foundry["Foundry\nResource"]
        cosmos["CosmosDB"]
    end

    subgraph vnet["Your Azure VNet (Customer-Managed)"]
        subgraph pe_subnet["Private Endpoint Subnet"]
            pe1["⟨/⟩ PE"]
            pe2["⟨/⟩ PE"]
            pe3["⟨/⟩ PE"]
            pe4["⟨/⟩ PE"]
        end
        subgraph compute_subnet["Agents & Evaluations Subnet"]
            compute["Agents, Evaluations\n(VNET-injected compute)"]
        end
    end

    pe1 -->|Private Link| storage
    pe2 -->|Private Link| search
    pe3 -->|Private Link| foundry
    pe4 -->|Private Link| cosmos

    compute -->|"Outbound traffic\n(optional firewall)"| fw["🔒 Azure Firewall\n(optional — customer-controlled)"]

    subgraph onprem["On-Premises Network"]
        corp["Corporate\nNetwork"]
    end

    corp -->|"ExpressRoute /\nVPN Connection"| vnet
    corp -->|"Bastion +\nJump Box VM"| vnet

    style azure_resources fill:#e8e0f0,stroke:#6B4FA0,stroke-width:2px
    style vnet fill:#e0e8f8,stroke:#0078d4,stroke-width:2px,stroke-dasharray: 5 5
    style pe_subnet fill:#eef4ff,stroke:#0078d4
    style compute_subnet fill:#eef4ff,stroke:#0078d4
    style onprem fill:#f5f5f5,stroke:#333
    style fw fill:#fff0f0,stroke:#d43a0a,stroke-width:2px
```

---

## Pattern 2: Hub-and-Spoke BYO VNET Architecture

```mermaid
flowchart LR
    onprem["On-Premises\nNetwork"] -->|Inbound| hub
    hub -->|Outbound| internet["Internet"]

    subgraph hub["Hub Azure VNET"]
        fw["🔒 Azure Firewall\n(optional — controls\nagent outbound traffic)"]
    end

    hub <-->|"VNET\nPeering"| spoke
    hub <-->|"VNET\nPeering"| dns_vnet

    subgraph spoke["Spoke Azure VNET"]
        subgraph compute_sub["Agents & Evaluations Subnet"]
            agents["Agents, Evaluations\n(VNET-injected compute)"]
        end
        subgraph pe_sub["Private Endpoint Subnet"]
            pe1["⟨/⟩ PE"]
            pe2["⟨/⟩ PE"]
            pe3["⟨/⟩ PE"]
            pe4["⟨/⟩ PE"]
        end
    end

    pe1 --> storage["Azure\nStorage"]
    pe2 --> search["AI Search"]
    pe3 --> cosmos["CosmosDB"]
    pe4 --> foundry["Foundry\nResource"]

    subgraph paas["Your Azure Resources for Standard Agent Setup"]
        storage
        search
        cosmos
        foundry
    end

    subgraph dns_vnet["DNS Azure VNET"]
        dns["🌐 Private DNS Zones"]
        zones["privatelink.cognitiveservices.azure.com\nprivatelink.openai.azure.com\nprivatelink.services.ai.azure.com\nprivatelink.search.windows.net\nprivatelink.documents.azure.com\nprivatelink.blob.core.windows.net"]
    end

    style hub fill:#d8d0e8,stroke:#6B4FA0,stroke-width:2px,stroke-dasharray: 5 5
    style spoke fill:#d0d8f0,stroke:#0078d4,stroke-width:2px,stroke-dasharray: 5 5
    style dns_vnet fill:#d0d8f0,stroke:#0078d4,stroke-width:2px,stroke-dasharray: 5 5
    style compute_sub fill:#e8eeff,stroke:#0078d4
    style pe_sub fill:#e8eeff,stroke:#0078d4
    style paas fill:#f0e8ff,stroke:#6B4FA0,stroke-width:2px
    style fw fill:#fff0f0,stroke:#d43a0a
    style dns fill:#eef8ff,stroke:#0078d4
```

---

## Pattern 3: Managed VNET Setup

```mermaid
flowchart TB
    subgraph foundry_boundary["Microsoft Foundry"]
        direction TB
        foundry_icon["Microsoft\nFoundry"]

        subgraph managed_vnet["Managed Virtual Network (Microsoft-managed)"]
            subgraph resource["Resource"]
                subgraph project["Project"]
                    agent["Agent Service\n(Compute)"]
                end
                pe_internal1["⟨/⟩ PE"]
            end
            pe_outbound1["⟨/⟩ PE"]
            pe_outbound2["⟨/⟩ PE"]
            pe_outbound3["⟨/⟩ PE"]
        end
    end

    pe_internal1 -->|Private Link| foundry_icon

    subgraph customer_vnet["Your Azure VNet"]
        pe_cust1["⟨/⟩ PE"]
        pe_cust2["⟨/⟩ PE"]
    end

    pe_cust1 -->|Blob| storage
    pe_cust2 --> connected

    subgraph connected["Azure Connected Resources"]
        direction LR
        storage["Azure Storage\nAccount"]
        cosmos["Azure\nCosmosDB"]
        search["AI Search"]
    end

    pe_outbound1 --> storage
    pe_outbound2 --> cosmos
    pe_outbound3 --> search

    subgraph onprem["On-Premises Network"]
        corp["Corporate\nNetwork"]
    end

    corp -->|"ExpressRoute /\nVPN Connection"| customer_vnet
    corp -->|"Bastion +\nJump Box VM"| customer_vnet

    style foundry_boundary fill:#e8e0f0,stroke:#6B4FA0,stroke-width:2px
    style managed_vnet fill:#d0d8f0,stroke:#0078d4,stroke-width:2px,stroke-dasharray: 5 5
    style resource fill:#eef4ff,stroke:#0078d4
    style project fill:#fff,stroke:#0078d4
    style customer_vnet fill:#d0d8f0,stroke:#0078d4,stroke-width:2px,stroke-dasharray: 5 5
    style connected fill:#e8e0f0,stroke:#6B4FA0,stroke-width:2px
    style onprem fill:#f5f5f5,stroke:#333
```

---

## Platform-to-Customer VNet Architecture (BYO VNET Deep Dive)

```mermaid
flowchart LR
    client(["Client"]) -->|"HTTPS :443"| endpoint

    subgraph platform["Foundry Platform Network"]
        direction TB
        endpoint["Foundry Endpoint\nendpoint.services.ai.azure.com\n(Public IP / APIM Gateway)"]

        endpoint -->|"HOSTED path\nHTTPS /invoke\n(host-level)"| microvm_host["Micro-VM Host Layer\n(hidden platform NIC)"]
        endpoint -->|"PROMPT path\nTool calls (HTTPS)"| tools["Tools Service\n(Shared — both agent types)"]

        microvm_host -->|"Tool calls\n(HTTPS)"| tools
        tools -->|"HTTPS"| dataproxy["Data Proxy Host Layer\n(ACA, hidden platform NIC)\nEgress to customer resources"]
    end

    subgraph customer_vnet["Customer VNet — e.g. 10.0.1.0/24"]
        subgraph delegated["Delegated Subnet /26\nMicrosoft.App/environments"]
            vm1["Micro-VM 1\n(Hosted Agent only)"]
            vm2["Micro-VM 2\n(Hosted Agent only)"]
            dp1["Data Proxy\n(ACA)"]
            dp2["Data Proxy\n(ACA)"]
        end

        delegated -->|"TCP/HTTPS\nvia NSG"| pe_subnet

        subgraph pe_subnet["Private Endpoint Subnet /26"]
            pe_storage["PE: Storage"]
            pe_sql["PE: SQL DB"]
            pe_kv["PE: Key Vault"]
        end
    end

    microvm_host -.->|"/invoke\nhost-level"| vm1
    microvm_host -.->|"/invoke\nhost-level"| vm2
    dataproxy -.->|"Data access\nhost-level"| dp1
    dataproxy -.->|"Data access\nhost-level"| dp2

    style platform fill:#fff3e0,stroke:#e65100,stroke-width:2px
    style endpoint fill:#ffe0b2,stroke:#e65100
    style microvm_host fill:#c8e6c9,stroke:#2e7d32
    style tools fill:#bbdefb,stroke:#1565c0
    style dataproxy fill:#fff9c4,stroke:#f9a825
    style customer_vnet fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray: 5 5
    style delegated fill:#c8e6c9,stroke:#2e7d32
    style pe_subnet fill:#ffcdd2,stroke:#c62828
    style vm1 fill:#c8e6c9,stroke:#2e7d32
    style vm2 fill:#c8e6c9,stroke:#2e7d32
    style dp1 fill:#fff9c4,stroke:#f9a825
    style dp2 fill:#fff9c4,stroke:#f9a825
```
