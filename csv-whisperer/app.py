"""
CSV Whisperer — Streamlit UI
A natural-language CSV analysis agent powered by Azure AI Foundry.
"""

import streamlit as st
from agent import (
    get_openai_client,
    run_turn,
    load_csv_text,
    SAMPLE_DATASETS,
)

st.set_page_config(page_title="CSV Whisperer 🐍", page_icon="🐍", layout="wide")

st.title("🐍 CSV Whisperer")
st.caption("Ask questions about data in plain English — powered by Azure AI Foundry + gpt-5.4-mini")


# --- Session state initialization ---
if "client" not in st.session_state:
    st.session_state.client = get_openai_client()

if "conversation" not in st.session_state:
    st.session_state.conversation = []

if "messages" not in st.session_state:
    st.session_state.messages = []

if "dataset_loaded" not in st.session_state:
    st.session_state.dataset_loaded = None

if "dataset_label" not in st.session_state:
    st.session_state.dataset_label = None


def decode_uploaded_csv(uploaded_file) -> str:
    """Read an uploaded CSV as text, with a small fallback for common encodings."""
    contents = uploaded_file.getvalue()
    try:
        return contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contents.decode("latin-1")


def load_dataset_into_chat(csv_text: str, dataset_label: str, dataset_key: str) -> None:
    conversation = ["init"]  # placeholder; no previous_response_id yet

    initial_prompt = (
        f"Here is my CSV data from {dataset_label}:\n\n```csv\n"
        + csv_text
        + "\n```\n\n"
        + "Please inspect it and give me a summary of what's in this dataset. "
        + "Use code_interpreter to run pandas code to analyze it."
    )

    summary, images = run_turn(
        st.session_state.client,
        conversation,
        initial_prompt,
    )

    st.session_state.conversation = conversation
    st.session_state.dataset_loaded = dataset_key
    st.session_state.dataset_label = dataset_label
    st.session_state.messages = [{"role": "assistant", "content": summary, "images": images}]


# --- Sidebar: dataset picker ---
with st.sidebar:
    st.header("📂 Pick a Dataset")
    for key, info in SAMPLE_DATASETS.items():
        if st.button(info["description"], key=key, use_container_width=True):
            with st.spinner(f"Loading {key}..."):
                csv_text = load_csv_text(key)
                load_dataset_into_chat(csv_text, info["description"], key)
            st.rerun()

    st.divider()
    st.header("📤 Upload Your CSV")
    uploaded_csv = st.file_uploader("Choose a CSV file", type="csv")
    if uploaded_csv is not None:
        if st.button("Analyze uploaded CSV", use_container_width=True):
            with st.spinner(f"Loading {uploaded_csv.name}..."):
                csv_text = decode_uploaded_csv(uploaded_csv)
                load_dataset_into_chat(csv_text, uploaded_csv.name, f"uploaded:{uploaded_csv.name}")
            st.rerun()

    st.divider()
    st.markdown("**💡 Sample questions:**")
    if st.session_state.dataset_loaded == "coffee_sales":
        st.markdown("- Which location has the highest revenue?")
        st.markdown("- Show me monthly revenue trends")
        st.markdown("- What's the most popular product?")
    elif st.session_state.dataset_loaded == "pypi_downloads":
        st.markdown("- Which category has the most downloads?")
        st.markdown("- Top 10 packages by stars?")
        st.markdown("- Plot downloads vs stars")
    elif st.session_state.dataset_loaded == "movies":
        st.markdown("- Which director has the best avg rating?")
        st.markdown("- Show ROI by genre")
        st.markdown("- Best rated movies under $20M budget?")
    elif st.session_state.dataset_loaded and str(st.session_state.dataset_loaded).startswith("uploaded:"):
        st.markdown("- What columns are in this dataset?")
        st.markdown("- Are there missing values or outliers?")
        st.markdown("- Create a chart for the most important trend")
    else:
        st.markdown("- *Pick a dataset or upload a CSV to get started!*")


# --- Main chat area ---
if not st.session_state.dataset_loaded:
    st.info("👈 Pick a sample dataset or upload your own CSV from the sidebar to get started!")
else:
    st.caption(f"Current dataset: {st.session_state.dataset_label}")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            for img in msg.get("images", []):
                    st.image(img)

    # Chat input
    if prompt := st.chat_input("Ask a question about the data..."):
        # Show user message
        st.session_state.messages.append({"role": "user", "content": prompt, "images": []})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                response, images = run_turn(
                    st.session_state.client,
                    st.session_state.conversation,
                    prompt,
                )
            st.markdown(response)
            for img in images:
                    st.image(img)
            st.session_state.messages.append({"role": "assistant", "content": response, "images": images})
