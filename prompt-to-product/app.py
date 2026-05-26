"""
Brief-to-Launch — Streamlit UI.
One enterprise product brief -> landing page, image, email, social, ads, sales blurb,
and structured JSON. Powered by GPT-5.4 + MAI-Image-2e on Azure AI Foundry.
"""

import json
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from jinja2 import Environment

from agent import generate_image, generate_launch_assets, get_openai_client

st.set_page_config(page_title="Brief-to-Launch", page_icon="✦", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    header[data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1320px; padding-top: 2.5rem; }

    .app-title {
        font-size: 2.4rem;
        font-weight: 800;
        color: white;
        letter-spacing: -0.04em;
        margin-bottom: 0.25rem;
    }
    .accent { color: #B667D8; }
    .app-subtitle {
        max-width: 760px;
        color: #BDB7C7;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 1.5rem;
    }
    .pipeline {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 1rem 0 2rem;
    }
    .pill {
        border: 1px solid rgba(182, 103, 216, 0.35);
        background: rgba(123, 45, 142, 0.18);
        color: #E8D7F2;
        border-radius: 999px;
        padding: 0.35rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .section-label {
        color: #BDB7C7;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin: 1rem 0 0.45rem;
    }
    .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
        border: 1.5px solid rgba(182, 103, 216, 0.35) !important;
        border-radius: 12px !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7B2D8E, #B667D8) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.25rem !important;
        font-weight: 700 !important;
    }
    .stButton > button:not([kind="primary"]) {
        white-space: normal !important;
        min-height: 3rem;
        border-radius: 12px !important;
    }
    div[data-testid="stTabs"] button {
        font-weight: 700;
    }
    .asset-card {
        border: 1px solid rgba(182, 103, 216, 0.22);
        border-radius: 16px;
        padding: 1.1rem;
        background: rgba(255, 255, 255, 0.03);
        margin-bottom: 0.85rem;
    }
    .asset-card h4 {
        color: white;
        margin: 0 0 0.35rem;
    }
    .muted {
        color: #BDB7C7;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_asset_card(title: str, body: str) -> None:
    safe_title = escape(title)
    safe_body = escape(body)
    st.markdown(
        f"""
        <div class="asset-card">
            <h4>{safe_title}</h4>
            <div class="muted">{safe_body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_lines(value: str) -> list[str]:
    return [line.strip("- •\t ") for line in value.splitlines() if line.strip("- •\t ")]


def assets_to_markdown(assets: dict) -> str:
    landing = assets.get("landing_page", {})
    ads = assets.get("ad_variants", [])
    email = assets.get("email", {})
    evidence = assets.get("evidence_map", [])
    checklist = assets.get("review_checklist", [])

    ad_lines = "\n".join(
        f"- **{ad.get('headline', '')}** — {ad.get('body', '')}" for ad in ads
    )
    benefit_lines = "\n".join(f"- {item}" for item in landing.get("benefits", []))
    proof_lines = "\n".join(
        f"- {item}" for item in landing.get("developer_proof_points", [])
    )
    evidence_lines = "\n".join(
        f"- **{item.get('generated_claim', '')}** — grounded by: {item.get('grounded_by', '')}"
        for item in evidence
    )
    checklist_lines = "\n".join(
        f"- **{item.get('check', '')}:** {item.get('status', '')} — {item.get('note', '')}"
        for item in checklist
    )

    return f"""# {assets.get("product_name", "Launch Kit")}

{assets.get("tagline", "")}

## Positioning
{assets.get("positioning", "")}

## Landing Page
**{landing.get("headline", "")}**

{landing.get("subheadline", "")}

### Benefits
{benefit_lines}

### Developer Proof Points
{proof_lines}

## Email
**Subject:** {email.get("subject", "")}

**Preview:** {email.get("preview", "")}

{email.get("body", "")}

## LinkedIn
{assets.get("linkedin_post", "")}

## Ads
{ad_lines}

## Sales Blurb
{assets.get("sales_blurb", "")}

## Compliance Note
{assets.get("compliance_note", "")}

## Evidence Map
{evidence_lines}

## Review Checklist
{checklist_lines}
"""


def render_launch_kit(assets: dict, image_url: str | None, audience: str, industry: str) -> None:
    landing = assets.get("landing_page", {})
    email = assets.get("email", {})

    tabs = st.tabs([
        "Landing Page",
        "Email",
        "Social",
        "Ads",
        "Sales Brief",
        "Evidence Map",
        "Review Checklist",
        "JSON",
    ])

    with tabs[0]:
        html = TEMPLATE.render(
            product_name=assets.get("product_name", "My Product"),
            tagline=assets.get("tagline", ""),
            positioning=assets.get("positioning", ""),
            audience=assets.get("target_audience", audience),
            industry=assets.get("industry", industry),
            eyebrow=landing.get("eyebrow", "Launch Kit"),
            headline=landing.get("headline", assets.get("product_name", "")),
            subheadline=landing.get("subheadline", ""),
            benefits=landing.get("benefits", []),
            developer_proof_points=landing.get("developer_proof_points", []),
            cta_primary=landing.get("cta_primary", "Get Started"),
            cta_secondary=landing.get("cta_secondary", "View Docs"),
            image_url=image_url,
        )
        components.html(html, height=980, scrolling=True)

    with tabs[1]:
        st.subheader(email.get("subject", "Email announcement"))
        st.caption(email.get("preview", ""))
        st.write(email.get("body", ""))

    with tabs[2]:
        st.subheader("LinkedIn post")
        st.write(assets.get("linkedin_post", ""))

    with tabs[3]:
        st.subheader("Ad variants")
        for idx, ad in enumerate(assets.get("ad_variants", []), start=1):
            render_asset_card(
                f"Ad {idx}: {ad.get('headline', '')}",
                ad.get("body", ""),
            )

    with tabs[4]:
        st.subheader("Sales enablement blurb")
        st.write(assets.get("sales_blurb", ""))
        st.subheader("Compliance note")
        st.info(assets.get("compliance_note", ""))

    with tabs[5]:
        st.subheader("Evidence map")
        st.caption("Shows which generated claims are grounded in the provided product facts.")
        evidence_rows = assets.get("evidence_map", [])
        if evidence_rows:
            st.table(evidence_rows)
        else:
            st.info("No evidence map was returned.")

    with tabs[6]:
        st.subheader("Review checklist")
        st.caption("Shows the quality and safety checks the model applied before generating assets.")
        checklist_rows = assets.get("review_checklist", [])
        if checklist_rows:
            st.table(checklist_rows)
        else:
            st.info("No review checklist was returned.")

    with tabs[7]:
        st.json(assets)
        st.download_button(
            "Download JSON",
            data=json.dumps(assets, indent=2),
            file_name="launch-kit.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Download Markdown",
            data=assets_to_markdown(assets),
            file_name="launch-kit.md",
            mime="text/markdown",
            use_container_width=True,
        )


if "client" not in st.session_state:
    st.session_state.client = get_openai_client()

if "brief" not in st.session_state:
    st.session_state.brief = ""
if "target_customer" not in st.session_state:
    st.session_state.target_customer = ""
if "proof_points" not in st.session_state:
    st.session_state.proof_points = ""
if "differentiators" not in st.session_state:
    st.session_state.differentiators = ""
if "claims_to_avoid" not in st.session_state:
    st.session_state.claims_to_avoid = ""
if "audience" not in st.session_state:
    st.session_state.audience = "Enterprise developers"
if "industry" not in st.session_state:
    st.session_state.industry = "Cross-industry"
if "tone" not in st.session_state:
    st.session_state.tone = "Technical and credible"

TEMPLATE_PATH = Path(__file__).parent / "templates" / "landing_page.html"
TEMPLATE = Environment(autoescape=True).from_string(
    TEMPLATE_PATH.read_text(encoding="utf-8")
)

st.markdown(
    '<div class="app-title">Brief <span class="accent">→</span> Launch</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="app-subtitle">
    Turn one product brief into a complete campaign launch kit. GPT-5.4 creates
    structured launch assets, MAI-Image-2e generates the hero visual, and the
    output is ready for downstream enterprise systems.
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="pipeline">
      <span class="pill">GPT-5.4 structured copy</span>
      <span class="pill">MAI-Image-2e hero image</span>
      <span class="pill">JSON for CMS / CRM</span>
      <span class="pill">Enterprise-ready channels</span>
    </div>
    """,
    unsafe_allow_html=True,
)

examples = [
    {
        "label": "Financial analyst assistant",
        "brief": "A secure AI assistant for financial analysts that summarizes earnings calls and flags risk signals.",
        "target_customer": "Equity research teams at large financial institutions",
        "audience": "Enterprise developers",
        "industry": "Financial services",
        "tone": "Technical and credible",
        "proof_points": [
            "Reduces earnings-call review time by 60% in pilot workflows",
            "Integrates with Teams, SharePoint, and internal research portals",
            "Supports role-based access controls, audit logging, and customer-managed data boundaries",
        ],
        "differentiators": [
            "Grounds summaries in approved transcripts and internal research notes",
            "Flags risk signals, open questions, and follow-up actions for analysts",
            "Exports structured analyst notes to existing research workflows",
        ],
        "claims_to_avoid": [
            "Do not claim SEC compliance",
            "Do not say it replaces analysts",
            "Do not provide investment advice or trading recommendations",
        ],
    },
    {
        "label": "Legacy Java migration platform",
        "brief": "A developer platform that helps teams migrate legacy Java services to Azure with automated code analysis.",
        "target_customer": "Platform engineering teams modernizing mission-critical enterprise apps",
        "audience": "Enterprise developers",
        "industry": "Cross-industry",
        "tone": "Technical and credible",
        "proof_points": [
            "Analyzes service dependencies, framework usage, and deployment configuration",
            "Generates prioritized modernization tasks with estimated engineering effort",
            "Exports GitHub issues and migration plans for platform teams",
        ],
        "differentiators": [
            "Combines code analysis, architecture guidance, and Azure target recommendations",
            "Keeps developers in their existing GitHub workflow",
            "Produces explainable migration plans instead of opaque code rewrites",
        ],
        "claims_to_avoid": [
            "Do not claim fully automated production migration",
            "Do not guarantee zero downtime",
            "Do not claim support for every Java framework",
        ],
    },
    {
        "label": "SOC alert copilot",
        "brief": "A cybersecurity copilot that triages SOC alerts, drafts incident summaries, and recommends next actions.",
        "target_customer": "Enterprise SOC teams handling high-volume alerts",
        "audience": "Security leaders",
        "industry": "Cross-industry",
        "tone": "Executive and concise",
        "proof_points": [
            "Clusters related alerts into incident narratives",
            "Generates analyst-ready summaries with recommended next actions",
            "Maintains audit trails for generated recommendations",
        ],
        "differentiators": [
            "Preserves human analyst review before escalation",
            "Connects alert context to playbook-driven response steps",
            "Supports security workflows without exposing sensitive telemetry outside Azure boundaries",
        ],
        "claims_to_avoid": [
            "Do not claim autonomous remediation",
            "Do not guarantee threat detection accuracy",
            "Do not say it replaces SOC analysts",
        ],
    },
    {
        "label": "Healthcare scheduling assistant",
        "brief": "A healthcare scheduling assistant that reduces call center workload while protecting patient privacy.",
        "target_customer": "Healthcare operations teams managing appointment scheduling",
        "audience": "IT decision makers",
        "industry": "Healthcare",
        "tone": "Friendly and practical",
        "proof_points": [
            "Answers common scheduling questions from approved clinic policies",
            "Escalates complex requests to human staff",
            "Supports audit logging and role-based access for operational teams",
        ],
        "differentiators": [
            "Designed for assisted scheduling workflows, not clinical diagnosis",
            "Uses approved content sources for patient-facing responses",
            "Helps reduce routine call volume while preserving staff oversight",
        ],
        "claims_to_avoid": [
            "Do not claim HIPAA compliance without customer validation",
            "Do not provide medical advice",
            "Do not imply the assistant can make clinical decisions",
        ],
    },
    {
        "label": "Supply chain risk dashboard",
        "brief": "A supply chain risk dashboard that predicts shipment delays and recommends mitigation plans.",
        "target_customer": "Global operations teams coordinating suppliers, carriers, and inventory",
        "audience": "Data and AI teams",
        "industry": "Manufacturing",
        "tone": "Bold and launch-ready",
        "proof_points": [
            "Combines ERP, logistics, weather, and supplier signals into one operational view",
            "Highlights high-risk lanes and affected customer orders",
            "Generates mitigation plans for rerouting, inventory allocation, and supplier communication",
        ],
        "differentiators": [
            "Turns predictive signals into operator-ready action plans",
            "Explains why a route or supplier is flagged as high risk",
            "Exports structured risk summaries to existing operations tools",
        ],
        "claims_to_avoid": [
            "Do not guarantee delivery dates",
            "Do not claim full supply chain autonomy",
            "Do not imply all disruptions are predictable",
        ],
    },
]

st.markdown('<div class="section-label">Start with a brief</div>', unsafe_allow_html=True)
for idx, example in enumerate(examples):
    button_label = f"{example['label']} — {example['brief']}"
    if st.button(button_label, key=f"example_{idx}", use_container_width=True):
        st.session_state.brief = example["brief"]
        st.session_state.target_customer = example["target_customer"]
        st.session_state.proof_points = "\n".join(example["proof_points"])
        st.session_state.differentiators = "\n".join(example["differentiators"])
        st.session_state.claims_to_avoid = "\n".join(example["claims_to_avoid"])
        st.session_state.audience = example["audience"]
        st.session_state.industry = example["industry"]
        st.session_state.tone = example["tone"]
        st.rerun()

product_brief = st.text_area(
    "Product brief",
    key="brief",
    height=180,
    placeholder="Describe the product, audience, use case, and why it matters...",
)

st.markdown('<div class="section-label">Grounding inputs</div>', unsafe_allow_html=True)
target_customer = st.text_input(
    "Target customer",
    key="target_customer",
    placeholder="Who specifically will use or buy this?",
)

ground_col1, ground_col2 = st.columns(2)
with ground_col1:
    proof_points_text = st.text_area(
        "Approved proof points",
        key="proof_points",
        height=135,
        placeholder="One fact per line. Example: Reduces review time by 60%.",
    )
    claims_to_avoid_text = st.text_area(
        "Claims to avoid",
        key="claims_to_avoid",
        height=110,
        placeholder="One constraint per line. Example: Do not claim regulatory compliance.",
    )
with ground_col2:
    differentiators_text = st.text_area(
        "Differentiators",
        key="differentiators",
        height=255,
        placeholder="One differentiator per line. Example: Grounds summaries in approved source docs.",
    )

st.caption(
    "These fields ground the launch kit so the model transforms approved facts instead of inventing claims."
)

col1, col2, col3 = st.columns(3)
with col1:
    audience = st.selectbox(
        "Audience",
        [
            "Enterprise developers",
            "IT decision makers",
            "Security leaders",
            "Data and AI teams",
            "Business executives",
        ],
        key="audience",
    )
with col2:
    industry = st.selectbox(
        "Industry",
        ["Cross-industry", "Financial services", "Healthcare", "Retail", "Manufacturing", "SaaS"],
        key="industry",
    )
with col3:
    tone = st.selectbox(
        "Tone",
        ["Technical and credible", "Executive and concise", "Bold and launch-ready", "Friendly and practical"],
        key="tone",
    )

channels = st.multiselect(
    "Channels",
    ["Landing page", "Email", "LinkedIn", "Ads", "Sales brief", "JSON"],
    default=["Landing page", "Email", "LinkedIn", "Ads", "Sales brief", "JSON"],
)

generate = st.button("Generate launch kit ✦", type="primary", use_container_width=True)

if generate and product_brief.strip():
    with st.status("Building your launch kit...", expanded=True) as status:
        proof_points = parse_lines(proof_points_text)
        differentiators = parse_lines(differentiators_text)
        claims_to_avoid = parse_lines(claims_to_avoid_text)

        st.write("Step 1/4: Reading the brief, proof points, differentiators, and claims to avoid.")
        st.write("Step 2/4: GPT-5.4 is creating grounded launch assets and an evidence map.")
        assets = generate_launch_assets(
            st.session_state.client,
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

        st.write("Step 3/4: MAI-Image-2e is generating the hero visual.")
        image_url, image_error = generate_image(assets.get("image_prompt", ""))

        st.write("Step 4/4: Rendering the landing page, channel assets, and downloads.")
        status.update(label="Launch kit ready", state="complete", expanded=False)

    if image_error:
        st.warning(image_error)

    st.session_state.launch_kit = {
        "assets": assets,
        "image_url": image_url,
        "audience": audience,
        "industry": industry,
    }
elif generate:
    st.warning("Add a product brief first.")

if "launch_kit" in st.session_state:
    st.markdown('<div class="section-label">Generated launch kit</div>', unsafe_allow_html=True)
    kit = st.session_state.launch_kit
    render_launch_kit(
        kit["assets"],
        kit["image_url"],
        kit["audience"],
        kit["industry"],
    )
else:
    st.info("Choose an example or enter your own product brief, then generate a launch kit.")
