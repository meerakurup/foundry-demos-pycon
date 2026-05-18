"""
Prompt-to-Product — Agent module.
Uses GPT-5.4 for marketing copy and MAI-Image-2e for hero image generation,
both on Azure AI Foundry.
"""

import os
import json
import base64
import hashlib
import requests as http_requests
from openai import OpenAI
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
TEXT_MODEL = "gpt-5.4"
IMAGE_MODEL = "MAI-Image-2e"

# Extract resource endpoint for MAI API (strip /api/projects/...)
_resource_endpoint = PROJECT_ENDPOINT.split("/api/projects")[0] if PROJECT_ENDPOINT else ""

_credential = DefaultAzureCredential()
_token_provider = get_bearer_token_provider(
    _credential, "https://cognitiveservices.azure.com/.default"
)

COPYWRITER_PROMPT = """You are a world-class product marketing copywriter.

Given a product description from the user, generate:
1. **Product Name** — a catchy, memorable name
2. **Tagline** — one punchy sentence
3. **Description** — 2-3 sentences of compelling marketing copy
4. **Key Features** — exactly 3 bullet points
5. **Call to Action** — a button label (e.g., "Get Started Free")

Respond in this exact JSON format (no markdown, no code fences):
{
  "product_name": "...",
  "tagline": "...",
  "description": "...",
  "features": ["...", "...", "..."],
  "cta": "..."
}
"""

IMAGE_PROMPT_TEMPLATE = (
    "A clean, modern product hero image for: {product_name}. "
    "{tagline}. Minimalist design, studio lighting, white background, "
    "professional product photography style. No text or watermarks."
)


def get_openai_client() -> OpenAI:
    """Get an OpenAI client wired to Azure AI Foundry."""
    if not PROJECT_ENDPOINT:
        raise ValueError(
            "Missing PROJECT_ENDPOINT. Create a .env file from "
            ".env.template and set your Foundry project endpoint."
        )
    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=_credential,
    )
    return project_client.get_openai_client()


def generate_copy(client: OpenAI, product_description: str) -> dict:
    """Generate marketing copy for a product using GPT-5.4."""
    response = client.responses.create(
        model=TEXT_MODEL,
        instructions=COPYWRITER_PROMPT,
        input=[{"role": "user", "content": product_description}],
    )

    text = ""
    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if block.type == "output_text":
                    text += block.text

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(text)


def generate_image(product_name: str, tagline: str) -> str | None:
    """Generate a hero image via the MAI /mai/v1/ endpoint. Returns a data URI or None."""
    try:
        prompt = IMAGE_PROMPT_TEMPLATE.format(
            product_name=product_name,
            tagline=tagline,
        )
        url = f"{_resource_endpoint}/mai/v1/images/generations"
        resp = http_requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_token_provider()}",
            },
            json={
                "model": IMAGE_MODEL,
                "prompt": prompt,
                "width": 1024,
                "height": 1024,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data and "b64_json" in data[0]:
            return f"data:image/png;base64,{data[0]['b64_json']}"
    except Exception as e:
        print(f"MAI image generation error: {e}")
    return None


def generate_product_page(
    client: OpenAI, product_description: str
) -> tuple[dict, str | None]:
    """
    Full pipeline: product description → marketing copy + hero image.
    Returns (copy_dict, image_data_uri_or_none).
    """
    copy = generate_copy(client, product_description)
    image_data_uri = generate_image(
        copy.get("product_name", "Product"),
        copy.get("tagline", ""),
    )
    return copy, image_data_uri
