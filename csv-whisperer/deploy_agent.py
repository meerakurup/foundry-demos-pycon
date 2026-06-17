"""Deploy the CSV Whisperer agent to Microsoft Foundry."""

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

ENDPOINT = "https://mkurup-test-resource.services.ai.azure.com/api/projects/mkurup-test"

SYSTEM_PROMPT = """You are the CSV Whisperer -- a friendly data analyst agent.

Your job:
1. When given CSV data, inspect its schema (columns, types, row count, sample rows) and summarize it.
2. Answer the user's natural-language questions by writing and executing Python code (pandas, matplotlib).
3. When a question benefits from a visual answer, generate a chart (bar, line, scatter, pie) using matplotlib.
4. Always show the code you ran so the user can learn from it.
5. Be conversational and fun -- this is a live demo at a Python convention!

Rules:
- Use pandas for data manipulation.
- For charts, ALWAYS start your code with:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
  This ensures charts render correctly in the sandboxed environment.
- Always call plt.tight_layout() then plt.show() to display charts. NEVER use plt.savefig().
- NEVER tell the user to "download" a file. All charts are displayed inline automatically.
- If the user's question is ambiguous, ask a clarifying question.
- Keep explanations concise but insightful.
"""


def main():
    client = AIProjectClient(
        endpoint=ENDPOINT,
        credential=DefaultAzureCredential(),
    )

    definition = PromptAgentDefinition(
        model="gpt-5.4-mini",
        instructions=SYSTEM_PROMPT,
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
    )

    version = client.agents.create_version(
        agent_name="csv-whisperer",
        definition=definition,
        description="Friendly data analyst agent -- upload CSV data and ask questions in plain English. Uses code_interpreter for pandas + matplotlib.",
    )

    print(f"Agent created: csv-whisperer")
    print(f"Version: {version['version']}")
    print(f"Status: {version['status']}")

    agent = client.agents.get(agent_name="csv-whisperer")
    print(f"Agent ID: {agent['id']}")
    print("Ready -- open the Foundry playground to test.")


if __name__ == "__main__":
    main()
