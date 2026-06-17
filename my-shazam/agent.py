"""
My-Shazam — speech-to-song identification helper.

Uses Azure AI Foundry for the text path and the Azure OpenAI endpoint for audio transcription.
"""

import json
import os
import re
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

DEMO_DIR = Path(__file__).resolve().parent


def load_local_env(env_file: Path) -> None:
    """Load KEY=VALUE pairs from a local .env file without overwriting existing env vars."""
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env(DEMO_DIR / ".env")
load_local_env(Path(__file__).resolve().parents[1] / ".env")

PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_PROJECT_ENDPOINT")
TRANSCRIPTION_MODEL = os.getenv("TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
IDENTIFICATION_MODEL = os.getenv("IDENTIFICATION_MODEL", "gpt-5.4-mini")


def _derive_azure_openai_endpoint(project_endpoint: str) -> str:
    """Convert a Foundry project endpoint into the matching Azure OpenAI account endpoint."""
    if not project_endpoint:
        raise RuntimeError("Missing PROJECT_ENDPOINT for Azure OpenAI transcription auth.")

    resource_name = project_endpoint.split("//", 1)[1].split(".services.ai.azure.com", 1)[0]
    return f"https://{resource_name}.openai.azure.com/"


def get_openai_client() -> OpenAI:
    """Create an OpenAI-compatible client from Azure AI Foundry."""
    if not PROJECT_ENDPOINT:
        raise RuntimeError(
            "Missing PROJECT_ENDPOINT. Create my-shazam/.env from my-shazam/.env.template "
            "or set PROJECT_ENDPOINT in the repo root .env."
        )

    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    return project_client.get_openai_client()


def _extract_response_text(response: Any) -> str:
    """Extract plain text from OpenAI Responses output."""
    parts: list[str] = []

    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) == "message":
            for block in getattr(item, "content", []) or []:
                if getattr(block, "type", None) == "output_text":
                    parts.append(block.text)
                elif getattr(block, "type", None) == "refusal":
                    parts.append(f"Refusal: {getattr(block, 'refusal', 'Unknown refusal')}")

    return "\n".join(parts).strip()


def _parse_song_guess(raw_text: str) -> dict[str, Any]:
    """Parse a plain-English song identification into the app's expected JSON shape."""
    cleaned = raw_text.strip()

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    title = None
    artist = None

    patterns = [
        r'“?(?P<title>[A-Za-z0-9&\'’ .\-]+?)”?\s+by\s+(?P<artist>[A-Za-z0-9&\'’ .\-]+)',
        r'(?i)from\s+“?(?P<title>[A-Za-z0-9&\'’ .\-]+?)”?\s+by\s+(?P<artist>[A-Za-z0-9&\'’ .\-]+)',
        r'(?i)the\s+song\s+is\s+“?(?P<title>[A-Za-z0-9&\'’ .\-]+?)”?\s+by\s+(?P<artist>[A-Za-z0-9&\'’ .\-]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            title = match.group('title').strip("\"'“”")
            artist = match.group('artist').strip("\"'“”")
            break

    if not title and not artist:
        return {
            'title': None,
            'artist': None,
            'confidence': 'low',
            'why_it_matches': cleaned or 'No structured result was returned.',
            'evidence_links': [],
            'raw_response': cleaned,
        }

    return {
        'title': title,
        'artist': artist,
        'confidence': 'medium',
        'why_it_matches': cleaned,
        'evidence_links': [],
        'raw_response': cleaned,
    }


def get_azure_openai_client() -> AzureOpenAI:
    """Create an Azure OpenAI client for audio transcription using AAD auth."""
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or _derive_azure_openai_endpoint(PROJECT_ENDPOINT)
    credential = DefaultAzureCredential()

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if api_key:
        return AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_version="2024-10-21",
            api_key=api_key,
        )

    return AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_version="2024-10-21",
        azure_ad_token_provider=lambda: credential.get_token("https://cognitiveservices.azure.com/.default").token,
    )


def transcribe_audio(audio_path: str | os.PathLike[str]) -> str:
    """Transcribe uploaded audio with the deployed Azure OpenAI speech model."""
    client = get_azure_openai_client()

    with open(audio_path, "rb") as handle:
        response = client.audio.transcriptions.create(
            model=TRANSCRIPTION_MODEL,
            file=handle,
            response_format="text",
        )

    if isinstance(response, str):
        return response.strip()
    if hasattr(response, "text"):
        return str(response.text).strip()
    return str(response).strip()


def identify_song(transcript: str) -> dict[str, Any]:
    """Ask the deployed reasoning model to identify the song and cite evidence from web search."""
    if not transcript.strip():
        return {
            "title": None,
            "artist": None,
            "confidence": "low",
            "why_it_matches": "The transcript is empty, so there is not enough evidence to guess the song.",
            "evidence_links": [],
            "raw_response": "",
        }

    client = get_openai_client()
    prompt = (
        "Use this short music excerpt to identify the likely song and artist. "
        "Keep the answer brief, and if you’re confident, mention the title and artist. "
        f"Excerpt: {transcript}"
    )

    try:
        response = client.responses.create(
            model=IDENTIFICATION_MODEL,
            input=[{"role": "user", "content": prompt}],
            tools=[{"type": "web_search_preview"}],
            temperature=0.2,
        )
        raw_text = _extract_response_text(response)
        data = _parse_song_guess(raw_text)
    except Exception:
        response = client.responses.create(
            model=IDENTIFICATION_MODEL,
            input=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw_text = _extract_response_text(response)
        data = _parse_song_guess(raw_text)

    if not data.get("title") and not data.get("artist") and isinstance(raw_text, str) and "cannot assist" in raw_text.lower():
        data = {
            "title": None,
            "artist": None,
            "confidence": "low",
            "why_it_matches": raw_text or "No structured result was returned.",
            "evidence_links": [],
            "raw_response": raw_text,
        }

    return {
        "title": data.get("title"),
        "artist": data.get("artist"),
        "confidence": data.get("confidence", "low"),
        "why_it_matches": data.get("why_it_matches", ""),
        "evidence_links": data.get("evidence_links", []),
        "raw_response": raw_text,
    }
