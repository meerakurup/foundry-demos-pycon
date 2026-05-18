# CSV Whisperer

A Streamlit data-analysis agent powered by **Microsoft Foundry** and the OpenAI Responses API with **Code Interpreter**. Pick a sample CSV or upload your own, ask questions in plain English, and let the agent inspect the data, run pandas code, and generate charts.

**What it does:** Given a CSV dataset, CSV Whisperer summarizes the schema and answers follow-up questions with executable Python analysis. When a visual answer helps, it creates matplotlib charts inline in the Streamlit app.

### Key components

- **Streamlit app** (`app.py`) - chat-style UI with a sidebar dataset picker and CSV uploader
- **Foundry agent helper** (`agent.py`) - configures the model, prompt, Responses API call, and Code Interpreter tool
- **Sample datasets** (`data/`) - PyPI downloads, coffee sales, and movie ratings CSV files

```
csv-whisperer/
├── data/
│   ├── coffee_sales.csv       ← Fictional cafe sales data
│   ├── movies.csv             ← Movie ratings and box office data
│   └── pypi_downloads.csv     ← Python package popularity data
├── agent.py                   ← Foundry/OpenAI Responses API helper
├── app.py                     ← Streamlit UI
├── .env.template              ← Local configuration template
├── requirements.txt           ← Demo dependencies
└── README.md
```

---

## Prerequisites

- Python 3.10+
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- A Microsoft Foundry project with a deployed model
- Access to the project endpoint configured in `.env`

---

## Getting started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the Foundry project

Create a local `.env` file from the template:

```bash
cp .env.template .env
```

Edit `.env` with your Foundry project values:

```env
FOUNDRY_PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
FOUNDRY_MODEL=gpt-5.4-mini
```

Get your project endpoint from the AI Toolkit sidebar in VS Code or from the [Microsoft Foundry portal](https://ai.azure.com).

The real `.env` file is intentionally ignored by Git. Commit `.env.template`, but keep `.env` local.

### 3. Authenticate

```bash
az login
```

The demo uses `DefaultAzureCredential`, so your Azure CLI sign-in should have access to the Foundry project.

### 4. Run the app

From the repository root:

```bash
python -m streamlit run csv-whisperer/app.py
```

Then choose one of the sample datasets from the sidebar or upload your own CSV file and start asking questions.

---

## Sample questions

### Any uploaded CSV

- What columns are in this dataset?
- Are there missing values or outliers?
- Create a chart for the most important trend.

### Coffee sales

- Which location has the highest revenue?
- Show me monthly revenue trends.
- What is the most popular product?

### PyPI downloads

- Which category has the most downloads?
- Show the top 10 packages by stars.
- Plot downloads vs stars.

### Movie ratings

- Which director has the best average rating?
- Show ROI by genre.
- What are the best-rated movies under a $20M budget?

---

## How it works

1. The Streamlit sidebar loads a sample CSV from `data/` or reads an uploaded CSV file.
2. The app sends the CSV text to the model with instructions to inspect it using pandas.
3. The Responses API invokes Code Interpreter when computation or charting is useful.
4. The Streamlit chat displays the response text and any generated charts.

The system prompt asks the agent to show the code it ran so the audience can learn from the analysis during the demo.