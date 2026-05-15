# Legacy Inventory API Demo

This is a second intentionally stale demo app for the PyPI Dependency Auditor. It uses a FastAPI-style stack instead of the Flask scraper stack in `demo_app`, giving the advisor a different set of packages to inspect.

## Audit it

From the repository root:

```bash
python audit_agent.py demo_legacy_api/requirements.txt
```

## Run it locally

```bash
cd demo_legacy_api
pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000` or `http://127.0.0.1:8000/docs`.

The pinned versions are deliberately old so the advisor can recommend upgrades and flag security/staleness issues.