# My-Shazam

A tiny Foundry-based app for singing-to-song identification.

## What it does
- Upload a short audio clip.
- Transcribe it with the deployed Azure OpenAI transcription model (default: gpt-4o-mini-transcribe).
- Ask gpt-5.4-mini with web search to guess the song and artist.

## Run it

1. Create or update the repo-level `.env` with your Azure AI Foundry endpoint:
   `PROJECT_ENDPOINT=https://<your-resource>.services.ai.azure.com/api/projects/<your-project>`
2. Install dependencies:
   `python -m pip install -r my-shazam/requirements.txt`
3. Launch the UI:
   `python -m streamlit run my-shazam/app.py`

## Notes
- The app uses Azure `DefaultAzureCredential`, so your local login must already be set up.
- If the model does not return structured JSON, the app still shows the raw model output for debugging.
