"""
Brief-to-Launch agent module.
Uses GPT-5.4 for structured campaign assets and MAI-Image-2e for hero imagery,
both on Azure AI Foundry.
"""

import json
import os
from typing import Any

import requests as http_requests
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT")
TEXT_MODEL = "gpt-5.4"
IMAGE_MODEL = "MAI-Image-2e"

_resource_endpoint = PROJECT_ENDPOINT.split("/api/projects")[0] if PROJECT_ENDPOINT else ""
_credential = DefaultAzureCredential()
_token_provider = get_bearer_token_provider(
    _credential, "https://cognitiveservices.azure.com/.default"
)

CAMPAIGN_PROMPT = """You are a senior enterprise product marketer and developer advocate.

Create a complete launch kit from the user's product brief. Optimize for a Build conference demo:
the output should feel practical, enterprise-ready, developer-relevant, and easy to plug into a CMS,
CRM, sales enablement tool, or marketing automation workflow.

Rules:
- Return valid JSON only. No markdown. No code fences.
- Keep copy specific and credible; avoid generic AI buzzwords.
- Make the technical value proposition clear for enterprise developers.
- Include a compliance-safe note for regulated or enterprise customers.
- Generate an image_prompt suitable for a simple product hero visual. The image must contain no text, logos, UI text, or watermarks.
- Keep image_prompt visually calm: one clear central subject or metaphor, plenty of whitespace, soft studio lighting, minimal background, no collages, no dashboards, no busy scenes, no crowds, no small UI details.
- Respect the requested channels. If a channel is not requested, still return its key with a useful concise fallback.
- Ground every concrete claim in the supplied proof_points or differentiators.
- Do not make claims listed in claims_to_avoid.
- If a proof point is not strong enough to support a claim, soften the claim instead of inventing evidence.
- The evidence_map should show the user exactly which input facts support the strongest generated claims.

Return this exact JSON shape:
{
  "product_name": "...",
  "tagline": "...",
  "positioning": "...",
  "target_audience": "...",
  "target_customer": "...",
  "industry": "...",
  "tone": "...",
  "grounding_summary": "...",
  "landing_page": {
    "eyebrow": "...",
    "headline": "...",
    "subheadline": "...",
    "benefits": ["...", "...", "..."],
    "developer_proof_points": ["...", "...", "..."],
    "cta_primary": "...",
    "cta_secondary": "..."
  },
  "email": {
    "subject": "...",
    "preview": "...",
    "body": "..."
  },
  "linkedin_post": "...",
  "ad_variants": [
    {"headline": "...", "body": "..."},
    {"headline": "...", "body": "..."},
    {"headline": "...", "body": "..."}
  ],
  "sales_blurb": "...",
  "compliance_note": "...",
  "evidence_map": [
    {"generated_claim": "...", "grounded_by": "..."},
    {"generated_claim": "...", "grounded_by": "..."},
    {"generated_claim": "...", "grounded_by": "..."}
  ],
  "review_checklist": [
    {"check": "Unsupported claims avoided", "status": "pass", "note": "..."},
    {"check": "Claims to avoid respected", "status": "pass", "note": "..."},
    {"check": "Enterprise/regulatory language softened", "status": "pass", "note": "..."},
    {"check": "Developer value proposition preserved", "status": "pass", "note": "..."}
  ],
  "image_prompt": "..."
}
"""


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


def _extract_response_text(response: Any) -> str:
    text = ""
    for item in response.output:
        if item.type == "message":
            for block in item.content:
                if block.type == "output_text":
                    text += block.text
    return text.strip()


def _parse_json_response(text: str) -> dict:
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text)


def generate_launch_assets(
    client: OpenAI,
    product_brief: str,
    audience: str,
    industry: str,
    tone: str,
    channels: list[str],
    target_customer: str,
    proof_points: list[str],
    differentiators: list[str],
    claims_to_avoid: list[str],
) -> dict:
    """Generate a structured campaign launch kit using GPT-5.4."""
    request_payload = {
        "product_brief": product_brief,
        "target_audience": audience,
        "target_customer": target_customer,
        "industry": industry,
        "tone": tone,
        "requested_channels": channels,
        "proof_points": proof_points,
        "differentiators": differentiators,
        "claims_to_avoid": claims_to_avoid,
    }

    response = client.responses.create(
        model=TEXT_MODEL,
        instructions=CAMPAIGN_PROMPT,
        input=[
            {
                "role": "user",
                "content": json.dumps(request_payload, indent=2),
            }
        ],
    )

    return _parse_json_response(_extract_response_text(response))


def generate_image(image_prompt: str) -> tuple[str | None, str | None]:
    """Generate a hero image via the MAI /mai/v1/ endpoint."""
    if not _resource_endpoint:
        return None, "Missing PROJECT_ENDPOINT; cannot determine MAI resource endpoint."

    try:
        simplified_prompt = (
            f"{image_prompt}\n\n"
            "Create a simple, premium enterprise product hero image. Use one central visual "
            "metaphor only, with a clean uncluttered composition, soft gradient or white "
            "background, generous negative space, subtle depth, and no more than three visual "
            "elements. Avoid collages, multiple panels, complex workflows, dashboards, "
            "screenshots, tiny icons, crowds, text, logos, labels, or watermarks."
        )
        resp = http_requests.post(
            f"{_resource_endpoint}/mai/v1/images/generations",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_token_provider()}",
            },
            json={
                "model": IMAGE_MODEL,
                "prompt": simplified_prompt,
                "width": 1024,
                "height": 1024,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data or "b64_json" not in data[0]:
            return None, f"Unexpected MAI response format: {resp.text[:300]}"
        return f"data:image/png;base64,{data[0]['b64_json']}", None
    except http_requests.RequestException as exc:
        return None, f"MAI image generation request failed: {exc}"
    except (KeyError, ValueError, TypeError) as exc:
        return None, f"MAI image generation response parsing failed: {exc}"


def generate_launch_kit(
    client: OpenAI,
    product_brief: str,
    audience: str,
    industry: str,
    tone: str,
    channels: list[str],
    target_customer: str,
    proof_points: list[str],
    differentiators: list[str],
    claims_to_avoid: list[str],
) -> tuple[dict, str | None, str | None]:
    """
    Full pipeline: product brief -> structured launch assets -> MAI hero image.
    Returns (assets, image_data_uri_or_none, image_error_or_none).
    """
    assets = generate_launch_assets(
        client,
        product_brief,
        audience,
        industry,
        tone,
        channels,
        target_customer,
        proof_points,
        differentiators,
        claims_to_avoid,
    )
    image_data_uri, image_error = generate_image(assets.get("image_prompt", ""))
    return assets, image_data_uri, image_error
