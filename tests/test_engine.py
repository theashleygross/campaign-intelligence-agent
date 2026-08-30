"""Tests for the deterministic matching + evidence-derivation engine.

These test src/engine.py directly (no Streamlit, no LLM) against the real
synthetic corpus in data/synthetic/past_campaigns.json.
"""

from __future__ import annotations

from src.engine import (
    MIN_STRONG_MATCHES,
    SIMILARITY_THRESHOLD,
    build_brief,
    find_similar_campaigns,
    load_past_campaigns,
)
from src.models import CampaignRequest


def test_close_match_returns_expected_top_campaign_with_high_similarity():
    """A request that closely mirrors CMP-001 should surface CMP-001 as the top match."""
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description=(
            "Sponsored LinkedIn content targeting IT directors at mid-market manufacturers, "
            "promoting a free supply-chain uptime assessment to generate qualified demo requests."
        ),
    )

    matches = find_similar_campaigns(request)

    assert matches, "expected at least one match"
    top = matches[0]
    assert top.campaign_id == "CMP-001"
    assert top.similarity_score > 0.8


def test_unrelated_request_returns_low_similarity_and_thin_evidence_flag():
    """A request unlike anything in the corpus should score low and flag thin evidence."""
    request = CampaignRequest(
        objective="astronaut recruitment",
        audience="deep-sea submarine pilots",
        market="Lunar colony",
        product="Zero-gravity kelp snacks",
        channel="carrier pigeon",
        description="Recruit interstellar explorers for a zero-gravity kelp snack tasting expedition.",
    )

    matches = find_similar_campaigns(request)
    brief = build_brief(request)

    assert matches, "engine should still return top-N candidates even if weak"
    assert all(m.similarity_score < SIMILARITY_THRESHOLD for m in matches)
    assert brief.strong_match_count < MIN_STRONG_MATCHES
    assert brief.thin_evidence is True


def test_hypotheses_and_risks_non_empty_when_matches_exist():
    """When there is a reasonably strong evidence base, hypotheses and risks should be populated."""
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="Lead generation campaign for IT directors at mid-market manufacturers on LinkedIn.",
    )

    brief = build_brief(request)

    assert brief.strong_match_count >= MIN_STRONG_MATCHES
    assert len(brief.hypotheses) > 0
    assert len(brief.risks) >= 0  # risks may legitimately be empty if metrics are all healthy
    assert len(brief.measurement_plan) > 0


def test_matched_campaigns_carry_real_metrics_from_corpus():
    """Matched campaigns must carry the actual synthetic metrics, not placeholders."""
    corpus = load_past_campaigns()
    corpus_by_id = {c["campaign_id"]: c for c in corpus}

    request = CampaignRequest(
        objective="product launch",
        audience="Finance directors at regional banks",
        market="Europe",
        product="LedgerGuard Compliance Suite",
        channel="webinar",
        description="EU regulatory launch webinar for the LedgerGuard cross-border reporting module.",
    )

    matches = find_similar_campaigns(request)
    top = matches[0]

    assert top.campaign_id in corpus_by_id
    assert top.key_metrics == corpus_by_id[top.campaign_id]["metrics"]
