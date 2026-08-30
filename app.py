"""Campaign Intelligence Agent -- Streamlit demo entry point.

A marketer describes a new campaign. The deterministic engine (src/engine.py)
retrieves the most similar synthetic past campaigns via TF-IDF similarity and
derives hypotheses/risks/messaging angles/measurement plan from their real
metrics. The UI keeps "observed historical data" (the Evidence panel) clearly
separated from "AI-assisted recommendation" (the Recommendation panel).
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.engine import MIN_STRONG_MATCHES, SIMILARITY_THRESHOLD, build_brief, load_past_campaigns
from src.llm import write_brief_narrative
from src.models import CampaignRequest

load_dotenv()

st.set_page_config(page_title="Campaign Intelligence Agent", page_icon="📣", layout="wide")

MOCK_MODE = os.environ.get("MOCK_MODE", "true").strip().lower() != "false"

OBJECTIVES = ["lead generation", "brand awareness", "product launch"]
CHANNELS = ["LinkedIn", "email", "webinar", "display"]


def _mode_badge() -> None:
    if MOCK_MODE:
        st.sidebar.success("MOCK_MODE=true -- deterministic engine + templated narrative. No API key needed.")
    else:
        st.sidebar.info("MOCK_MODE=false -- deterministic engine + live Claude narrative (claude-sonnet-5).")


def _distinct_values(field: str) -> list[str]:
    campaigns = load_past_campaigns()
    return sorted({c.get(field, "") for c in campaigns if c.get(field)})


def main() -> None:
    st.title("📣 Campaign Intelligence Agent")
    st.caption(
        "Describe a new campaign. The agent retrieves the most similar synthetic past campaigns "
        "and drafts an evidence-backed brief -- separating what was actually observed from what "
        "the AI recommends."
    )
    _mode_badge()

    st.subheader("New campaign request")
    with st.form("campaign_request_form"):
        col1, col2 = st.columns(2)
        with col1:
            objective = st.selectbox("Objective", OBJECTIVES)
            audience = st.text_input("Audience", placeholder="e.g. IT directors at mid-market manufacturers")
            market = st.selectbox("Market / region", _distinct_values("market") or ["North America"])
        with col2:
            product = st.text_input("Product / product line", placeholder="e.g. CloudSync Ops Platform")
            channel = st.selectbox("Channel", CHANNELS)
        description = st.text_area(
            "Free-text description",
            placeholder="Describe the campaign concept, offer, and angle in a sentence or two.",
        )
        submitted = st.form_submit_button("Generate brief")

    if not submitted:
        st.info("Fill out the form above and click **Generate brief** to see matched evidence and recommendations.")
        return

    if not audience.strip() or not product.strip():
        st.error("Audience and product are required.")
        return

    request = CampaignRequest(
        objective=objective,
        audience=audience.strip(),
        market=market,
        product=product.strip(),
        channel=channel,
        description=description.strip(),
    )

    brief = build_brief(request)

    # --- Coverage indicator ---------------------------------------------------
    st.subheader("Coverage")
    total_matches = len(brief.matched_campaigns)
    if brief.thin_evidence:
        st.warning(
            f"⚠️ Thin evidence: only {brief.strong_match_count} of {total_matches} matched campaigns "
            f"meet the similarity threshold ({SIMILARITY_THRESHOLD}). At least {MIN_STRONG_MATCHES} strong "
            "matches are recommended before treating this brief as a reliable benchmark."
        )
    else:
        st.success(
            f"✅ {brief.strong_match_count} of {total_matches} matched campaigns meet the similarity "
            f"threshold ({SIMILARITY_THRESHOLD}) -- reasonable evidence coverage."
        )

    evidence_col, recommendation_col = st.columns(2)

    # --- Evidence panel (observed data) ---------------------------------------
    with evidence_col:
        st.subheader("Evidence")
        st.caption("Observed data -- real synthetic historical campaigns and their actual metrics.")
        if not brief.matched_campaigns:
            st.write("No past campaigns found in the corpus.")
        for m in brief.matched_campaigns:
            strong = m.similarity_score >= SIMILARITY_THRESHOLD
            label = f"{m.campaign_id} -- similarity {m.similarity_score:.2f}" + (" (strong match)" if strong else " (weak match)")
            with st.expander(label, expanded=strong):
                st.markdown(f"**Objective:** {m.objective}  \n**Audience:** {m.audience}  \n"
                            f"**Market:** {m.market}  \n**Product line:** {m.product_line}  \n"
                            f"**Channel:** {m.channel}")
                st.markdown(f"*{m.description}*")
                st.markdown("**Observed metrics:**")
                st.json(m.key_metrics)

    # --- Recommendation panel (AI-assisted) -----------------------------------
    with recommendation_col:
        st.subheader("Recommendation")
        st.caption("AI-assisted recommendation -- review before use. Derived from the evidence at left.")

        st.markdown("**Hypotheses**")
        if brief.hypotheses:
            for h in brief.hypotheses:
                st.markdown(f"- {h}")
        else:
            st.write("No hypotheses could be derived -- insufficient matching evidence.")

        st.markdown("**Messaging angles**")
        if brief.messaging_angles:
            for a in brief.messaging_angles:
                st.markdown(f"- {a}")
        else:
            st.write("No repeated messaging angle detected across matched campaigns.")

        st.markdown("**Recommended audiences**")
        if brief.recommended_audiences:
            for a in brief.recommended_audiences:
                st.markdown(f"- {a}")
        else:
            st.write("No audience recommendation available.")

        st.markdown("**Risks**")
        if brief.risks:
            for r in brief.risks:
                st.markdown(f"- {r}")
        else:
            st.write("No specific risks flagged by the rules engine.")

        st.markdown("**Measurement plan**")
        for step in brief.measurement_plan:
            st.markdown(f"- {step}")

    st.subheader("Narrative brief")
    st.caption("AI-assisted recommendation -- review before use. Template-written in mock mode, Claude-written in live mode.")
    narrative = write_brief_narrative(request, brief)
    st.write(narrative)


if __name__ == "__main__":
    main()
