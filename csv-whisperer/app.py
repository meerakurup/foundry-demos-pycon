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


# --- Sidebar: dataset picker ---
with st.sidebar:
    st.header("📂 Pick a Dataset")
    for key, info in SAMPLE_DATASETS.items():
        if st.button(info["description"], key=key, use_container_width=True):
            with st.spinner(f"Loading {key}..."):
                csv_text = load_csv_text(key)
                conversation = ["init"]  # placeholder; no previous_response_id yet

                initial_prompt = (
                    "Here is my CSV data:\n\n```csv\n"
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
                st.session_state.dataset_loaded = key
                st.session_state.messages = [{"role": "assistant", "content": summary, "images": images}]
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
    else:
        st.markdown("- *Pick a dataset to get started!*")


# --- Main chat area ---
if not st.session_state.dataset_loaded:
    st.info("👈 Pick a dataset from the sidebar to get started!")
else:
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
