"""Deploy the Network Isolation Expert agent to Microsoft Foundry."""

import os
import yaml
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

# Set the ENDPOINT environment variable to your own Foundry project endpoint.
# Falls back to the reference project if unset.
ENDPOINT = os.environ.get(
    "ENDPOINT",
    "https://mkurup-test-resource.services.ai.azure.com/api/projects/mkurup-test",
)
AGENT_YML = Path(__file__).parent / "agent.yml"


def main():
    # Parse agent.yml
    with open(AGENT_YML, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    instructions = spec["instructions"]
    model = spec["model"]
    name = spec["name"]
    description = spec.get("description", "")

    # Build the prompt agent definition
    definition = PromptAgentDefinition(
        model=model,
        instructions=instructions,
        tools=spec.get("tools", []),
    )

    # Connect to Foundry
    client = AIProjectClient(
        endpoint=ENDPOINT,
        credential=DefaultAzureCredential(),
    )

    # Create the agent version
    version = client.agents.create_version(
        agent_name=name,
        definition=definition,
        description=description,
    )

    print(f"Agent created: {name}")
    print(f"Version: {version}")

    # List the agent to confirm
    agent = client.agents.get(agent_name=name)
    print(f"\nAgent details: {agent}")
    print(f"\nAgent '{name}' is ready. Open the Foundry playground to test it.")


if __name__ == "__main__":
    main()
