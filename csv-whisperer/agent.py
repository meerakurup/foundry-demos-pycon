"""
CSV Whisperer — Agent setup module.
Uses the Responses API via Azure AI Foundry with code_interpreter for CSV analysis.
"""

import base64
import os
import httpx
from pathlib import Path
from openai import OpenAI
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

DEMO_DIR = Path(__file__).parent


def load_local_env(env_file: Path) -> None:
    """Load simple KEY=VALUE pairs from a local .env file without overwriting existing env vars."""
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env(DEMO_DIR / ".env")

PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
MODEL = os.getenv("FOUNDRY_MODEL", "gpt-5.4-mini")

SYSTEM_PROMPT = """You are the CSV Whisperer — a friendly data analyst agent.

Your job:
1. When given CSV data, inspect its schema (columns, types, row count, sample rows) and summarize it.
2. Answer the user's natural-language questions by writing and executing Python code (pandas, matplotlib).
3. When a question benefits from a visual answer, generate a chart (bar, line, scatter, pie) using matplotlib.
4. Always show the code you ran so the user can learn from it.
5. Be conversational and fun — this is a live demo at a Python convention!

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

DATA_DIR = DEMO_DIR / "data"

SAMPLE_DATASETS = {
    "pypi_downloads": {
        "file": DATA_DIR / "pypi_downloads.csv",
        "description": "🐍 PyPI Package Stats — Top 50 Python packages with download counts, stars, categories",
    },
    "coffee_sales": {
        "file": DATA_DIR / "coffee_sales.csv",
        "description": "☕ Coffee Shop Sales — Fictional café chain with dates, products, revenue, locations",
    },
    "movies": {
        "file": DATA_DIR / "movies.csv",
        "description": "🎬 Movie Ratings — 75 popular films with ratings, box office, budgets, and genres",
    },
}


def get_openai_client() -> OpenAI:
    """Get an OpenAI client wired to Azure AI Foundry."""
    if not PROJECT_ENDPOINT:
        raise RuntimeError(
            "Missing FOUNDRY_PROJECT_ENDPOINT. Create csv-whisperer/.env from "
            "csv-whisperer/.env.template and set your Foundry project endpoint."
        )

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    return project_client.get_openai_client()


def upload_file(client: OpenAI, dataset_key: str) -> str:
    """Upload a sample CSV to the Foundry file store, return the file ID."""
    dataset = SAMPLE_DATASETS[dataset_key]
    with open(dataset["file"], "rb") as f:
        uploaded = client.files.create(file=f, purpose="assistants")
    return uploaded.id


def build_initial_input(csv_text: str) -> list:
    """Build the first turn's input list with the system prompt and CSV data."""
    return [
        {"role": "developer", "content": SYSTEM_PROMPT},
    ]


def run_turn(client: OpenAI, conversation: list, user_message: str) -> tuple[str, list]:
    """
    Send a user message via the Responses API, return (response_text, images).
    `conversation` is mutated in-place to maintain multi-turn context via response IDs.
    """
    # Use previous_response_id for multi-turn instead of replaying the full list
    previous_id = conversation[-1] if len(conversation) > 1 else None

    kwargs = dict(
        model=MODEL,
        instructions=SYSTEM_PROMPT,
        input=[{"role": "user", "content": user_message}],
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
    )
    if previous_id and isinstance(previous_id, str) and previous_id.startswith("resp_"):
        kwargs["previous_response_id"] = previous_id

    response = client.responses.create(**kwargs)

    text_parts = []
    images = []

    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if block.type == "output_text":
                    text_parts.append(block.text)
                elif block.type == "refusal":
                    text_parts.append(f"⚠️ Refused: {block.refusal}")
        elif item.type == "code_interpreter_call":
            if item.outputs:
                for output in item.outputs:
                    if output.type == "image" and output.url:
                        # Download the image so we can display it inline
                        try:
                            img_resp = httpx.get(output.url, timeout=30)
                            img_resp.raise_for_status()
                            images.append(img_resp.content)
                        except Exception:
                            images.append(output.url)  # fallback to URL
                    elif output.type == "logs" and output.logs:
                        text_parts.append(f"```\n{output.logs}\n```")

    # Store the response ID for multi-turn chaining
    conversation.append(response.id)

    return "\n\n".join(text_parts), images


def load_csv_text(dataset_key: str) -> str:
    """Read a sample CSV file as text."""
    return SAMPLE_DATASETS[dataset_key]["file"].read_text(encoding="utf-8")
