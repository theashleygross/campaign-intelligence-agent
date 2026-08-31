"""Campaign Intelligence Agent -- Streamlit demo entry point.

A marketer describes a new campaign. The deterministic engine (src/engine.py)
retrieves the most similar synthetic past campaigns via TF-IDF similarity and
derives hypotheses/risks/messaging angles/measurement plan from their real
metrics. The UI keeps "observed historical data" (the Evidence panel) clearly
separated from "AI-assisted recommendation" (the Recommendation panel), and
surfaces all 5 evidence source types the engine models for each match.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from src.engine import (
    EVIDENCE_SOURCE_TYPES,
    MIN_STRONG_MATCHES,
    SIMILARITY_THRESHOLD,
    build_brief,
    load_past_campaigns,
)
from src.llm import write_brief_narrative
from src.models import CampaignRequest

load_dotenv()

st.set_page_config(page_title="Campaign Intelligence Agent", page_icon="📣", layout="wide")

MOCK_MODE = os.environ.get("MOCK_MODE", "true").strip().lower() != "false"

OBJECTIVES = ["lead generation", "brand awareness", "product launch", "customer retention"]
CHANNELS = ["LinkedIn", "email", "webinar", "display", "paid search", "social"]

# Literal count of automated tests in tests/, verified via `pytest -v` at
# release time (see docs/evaluation-plan.md). Update this alongside the test
# suite -- it must always equal the real, currently-passing pytest count.
VERIFIED_TEST_COUNT = 31

FORM_KEYS = [
    "req_objective",
    "req_audience",
    "req_market",
    "req_product",
    "req_channel",
    "req_description",
]


def _mode_badge() -> None:
    if MOCK_MODE:
        st.sidebar.success("MOCK_MODE=true -- deterministic engine + templated narrative. No API key needed.")
    else:
        st.sidebar.info("MOCK_MODE=false -- deterministic engine + live Claude narrative (claude-sonnet-5).")


def _distinct_values(field: str) -> list[str]:
    campaigns = load_past_campaigns()
    return sorted({c.get(field, "") for c in campaigns if c.get(field)})


def _reset_state() -> None:
    """Clear the form inputs and any generated brief / review decision."""
    for key in FORM_KEYS + ["brief", "request", "narrative", "review_status"]:
        st.session_state.pop(key, None)


def main() -> None:
    st.title("📣 Campaign Intelligence Agent")
    st.caption(
        "**Public portfolio prototype · Synthetic data** -- describe a new campaign and the agent "
        "retrieves the most similar synthetic past campaigns, then drafts an evidence-backed brief for "
        "human review, separating what was actually observed from what the AI recommends."
    )
    _mode_badge()

    campaigns = load_past_campaigns()

    # --- 3-metric panel --------------------------------------------------------
    m1, m2, m3 = st.columns(3)
    m1.metric("Synthetic campaigns", len(campaigns), help="len(load_past_campaigns()) -- data/synthetic/past_campaigns.json")
    m2.metric("Evidence source types", len(EVIDENCE_SOURCE_TYPES), help="Prior campaign brief, persona research, customer/market insight, creative asset reference, performance benchmark (src/engine.py:EVIDENCE_SOURCE_TYPES)")
    m3.metric("Automated tests", VERIFIED_TEST_COUNT, help="Exact count from `pytest -v` at release time -- see docs/evaluation-plan.md")

    st.button("Reset state", on_click=_reset_state, help="Clears the form and any generated brief.")

    st.subheader("New campaign request")
    with st.form("campaign_request_form"):
        col1, col2 = st.columns(2)
        with col1:
            objective = st.selectbox("Objective", OBJECTIVES, key="req_objective")
            audience = st.text_input(
                "Audience", placeholder="e.g. IT directors at mid-market manufacturers", key="req_audience"
            )
            market = st.selectbox("Market / region", _distinct_values("market") or ["North America"], key="req_market")
        with col2:
            product = st.text_input(
                "Product / product line", placeholder="e.g. CloudSync Ops Platform", key="req_product"
            )
            channel = st.selectbox("Channel", CHANNELS, key="req_channel")
        description = st.text_area(
            "Free-text description",
            placeholder="Describe the campaign concept, offer, and angle in a sentence or two.",
            key="req_description",
        )
        submitted = st.form_submit_button("Generate brief")

    if submitted:
        if not audience.strip() or not product.strip():
            st.error("Audience and product are required.")
        else:
            request = CampaignRequest(
                objective=objective,
                audience=audience.strip(),
                market=market,
                product=product.strip(),
                channel=channel,
                description=description.strip(),
            )
            st.session_state["request"] = request
            st.session_state["brief"] = build_brief(request)
            st.session_state["narrative"] = write_brief_narrative(request, st.session_state["brief"])
            st.session_state["review_status"] = None  # a newly generated brief always starts un-reviewed

    if "brief" not in st.session_state:
        st.info("Fill out the form above and click **Generate brief** to see matched evidence and recommendations.")
        return

    request = st.session_state["request"]
    brief = st.session_state["brief"]

    # --- Coverage / uncertainty indicator --------------------------------------
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

    # --- Evidence panel (observed data, all 5 evidence source types) ----------
    with evidence_col:
        st.subheader("Evidence")
        st.caption("Observed data -- 5 distinct evidence source types per matched campaign.")
        if not brief.matched_campaigns:
            st.write("No past campaigns found in the corpus.")
        for m in brief.matched_campaigns:
            strong = m.similarity_score >= SIMILARITY_THRESHOLD
            label = f"{m.campaign_id} -- similarity {m.similarity_score:.2f}" + (" (strong match)" if strong else " (weak match)")
            with st.expander(label, expanded=strong):
                st.markdown("**① Prior campaign brief**")
                st.markdown(
                    f"**Objective:** {m.objective}  \n**Audience:** {m.audience}  \n"
                    f"**Market:** {m.market}  \n**Product line:** {m.product_line}  \n"
                    f"**Channel:** {m.channel}"
                )
                st.markdown(f"*{m.description}*")

                st.markdown("**② Persona research**")
                st.write(m.persona_notes or "No persona research recorded for this campaign.")

                st.markdown("**③ Customer / market insight**")
                st.write(m.market_insight or "No market insight recorded for this campaign.")

                st.markdown("**④ Creative asset reference**")
                st.write(m.creative_reference or "No creative reference recorded for this campaign.")

                st.markdown("**⑤ Performance benchmark**")
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
    st.write(st.session_state["narrative"])

    # --- Human review checkpoint -----------------------------------------------
    st.subheader("Human review")
    st.caption(
        "This brief is a draft for a marketer/strategist to review, not a final campaign plan. "
        "Record your decision below (in-session only -- nothing is persisted)."
    )
    review_col1, review_col2, _ = st.columns([1, 1, 3])
    with review_col1:
        if st.button("✅ Approve brief"):
            st.session_state["review_status"] = "approved"
    with review_col2:
        if st.button("✏️ Request revision"):
            st.session_state["review_status"] = "revision_requested"

    review_status = st.session_state.get("review_status")
    if review_status == "approved":
        st.success("Brief approved by reviewer. Ready to move to creative and media planning.")
    elif review_status == "revision_requested":
        st.warning("Revision requested. Adjust the campaign request above and click **Generate brief** again.")
    else:
        st.info("Awaiting reviewer decision -- approve or request a revision before acting on this brief.")


if __name__ == "__main__":
    main()
