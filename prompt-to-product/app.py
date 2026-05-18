"""
Prompt-to-Product — Streamlit UI
Describe a product → get marketing copy + hero image → rendered as a landing page.
Powered by GPT-5.4 + MAI-Image-2e on Azure AI Foundry.
"""

import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
from jinja2 import Template
from agent import get_openai_client, generate_product_page

# ── Page config ──
st.set_page_config(page_title="Prompt → Product", page_icon="✦", layout="centered")

# ── Custom theme: clean white + metallic purple accent ──
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .block-container { max-width: 720px; padding-top: 3rem; }

    /* Hide default Streamlit header decoration */
    header[data-testid="stHeader"] { background: transparent; }

    /* Title area */
    .app-title {
        font-size: 2rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.15rem;
    }
    .app-subtitle {
        font-size: 0.85rem;
        color: #888;
        margin-bottom: 2rem;
    }
    .accent { color: #7B2D8E; }

    /* Text area */
    .stTextArea textarea {
        border: 2px solid #e8e0f0 !important;
        border-radius: 12px !important;
        font-size: 0.95rem !important;
        padding: 1rem !important;
        transition: border-color 0.2s;
    }
    .stTextArea textarea:focus {
        border-color: #7B2D8E !important;
        box-shadow: 0 0 0 2px rgba(123, 45, 142, 0.15) !important;
    }

    /* Primary button */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7B2D8E, #9B59B6) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.02em;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(123, 45, 142, 0.35) !important;
    }

    /* Example chip buttons */
    .example-chip {
        display: inline-block;
        border: 1.5px solid #e8e0f0;
        border-radius: 20px;
        padding: 0.4rem 1rem;
        font-size: 0.8rem;
        color: #555;
        cursor: pointer;
        transition: all 0.15s;
        background: white;
        margin: 0.2rem 0.15rem;
    }
    .example-chip:hover {
        border-color: #7B2D8E;
        color: #7B2D8E;
        background: #f9f5fc;
    }

    /* Spinner */
    .stSpinner > div { color: #7B2D8E !important; }

    /* Expander */
    .streamlit-expanderHeader { font-size: 0.85rem; color: #666; }

    /* Divider */
    hr { border-color: #f0ebf5 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ──
st.markdown('<div class="app-title">Prompt <span class="accent">→</span> Product</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Describe a product idea. Get a landing page — copy, image, and all.</div>',
    unsafe_allow_html=True,
)

# ── Session state ──
if "client" not in st.session_state:
    st.session_state.client = get_openai_client()

TEMPLATE_PATH = Path(__file__).parent / "templates" / "landing_page.html"
TEMPLATE = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))

# ── Example chips ──
examples = [
    "A smart water bottle that tracks hydration",
    "AI recipe app using fridge contents",
    "Sustainable sneakers from ocean plastic",
    "Dev CLI that generates API docs from code",
    "Focus lamp with ambient light therapy",
]

prefill = st.session_state.pop("prefill", "")
auto_generate = st.session_state.pop("auto_generate", False)

st.markdown('<p style="font-size:0.8rem; color:#999; margin-bottom:0.25rem;">Try one of these ideas:</p>', unsafe_allow_html=True)
for ex in examples:
    if st.button(ex, key=f"ex_{ex}", use_container_width=True):
        st.session_state["prefill"] = ex
        st.session_state["auto_generate"] = True
        st.rerun()

# ── Input ──
product_desc = st.text_area(
    "What's your product idea?",
    value=prefill,
    height=100,
    placeholder="A noise-canceling desk lamp for remote workers that adapts to your focus state…",
    label_visibility="collapsed",
)

generate = st.button("Generate landing page ✦", type="primary", use_container_width=True)

# ── Generate ──
if (generate or auto_generate) and product_desc.strip():
    with st.spinner("Creating your landing page…"):
        copy, image_url = generate_product_page(st.session_state.client, product_desc)

    st.divider()

    # Render the landing page
    html = TEMPLATE.render(
        product_name=copy.get("product_name", "My Product"),
        tagline=copy.get("tagline", ""),
        description=copy.get("description", ""),
        features=copy.get("features", []),
        cta=copy.get("cta", "Learn More"),
        image_url=image_url,
    )

    components.html(html, height=900, scrolling=True)

    # Collapsible details
    with st.expander("View raw marketing copy"):
        st.json(copy)

elif generate:
    st.warning("Type a product idea above to get started.")
