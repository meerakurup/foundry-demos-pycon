"""Create (or recreate) a Foundry vector store with the networking-agent knowledge files."""

import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Set the ENDPOINT environment variable to your own Foundry project endpoint.
# Falls back to the reference project if unset.
ENDPOINT = os.environ.get(
    "ENDPOINT",
    "https://mkurup-test-resource.services.ai.azure.com/api/projects/mkurup-test",
)
FILES = [
    "skills/SKILL.md",
    "skills/DIAGRAMS.md",
]

project = AIProjectClient(endpoint=ENDPOINT, credential=DefaultAzureCredential())
client = project.get_openai_client()

# Upload each file
file_ids = []
for path in FILES:
    print(f"Uploading {path} …")
    uploaded = client.files.create(file=open(path, "rb"), purpose="assistants")
    print(f"  File ID: {uploaded.id}")
    file_ids.append(uploaded.id)

# Create vector store with all files
print("Creating vector store …")
store = client.vector_stores.create(
    file_ids=file_ids,
    name="network-isolation-knowledge",
)
print(f"  Vector Store ID: {store.id}")
print()
print("Paste this ID into agent.yml under vector_store_ids:")
print(f'      - "{store.id}"')
