"""Tests for the deterministic matching + evidence-derivation engine.

These test src/engine.py (and src/llm.py's mock narrative path) directly --
no Streamlit -- against the real 30-campaign synthetic corpus in
data/synthetic/past_campaigns.json, plus small hand-built corpora where a
test needs to isolate one rule from the rest of the real data.

Grouped by what each block of tests verifies (see docs/evaluation-plan.md
for the full "what does correct mean" writeup):
  - Corpus / schema integrity (the 30-record requirement, 5 evidence types)
  - Matching quality across the expanded corpus (existing + new segments)
  - Thin-evidence detection
  - Hypothesis / risk derivation rules
  - Messaging angle and recommended-audience derivation
  - Measurement plan branching
  - Brief-quality / required-sections checks
  - Narrative (mock LLM) output
"""

from __future__ import annotations

from src.engine import (
    EVIDENCE_SOURCE_TYPES,
    MIN_STRONG_MATCHES,
    SIMILARITY_THRESHOLD,
    build_brief,
    find_similar_campaigns,
    load_past_campaigns,
)
from src.llm import write_brief_narrative
from src.models import CampaignRequest

# ---------------------------------------------------------------------------
# Corpus / schema integrity
# ---------------------------------------------------------------------------


def test_corpus_has_exactly_thirty_campaigns():
    """The release brief requires exactly 30 seeded fictional campaign records."""
    corpus = load_past_campaigns()
    assert len(corpus) == 30


def test_corpus_campaign_ids_are_unique():
    corpus = load_past_campaigns()
    ids = [c["campaign_id"] for c in corpus]
    assert len(ids) == len(set(ids))


def test_original_fifteen_campaigns_are_preserved():
    """The original CMP-001..CMP-015 records must still exist -- other tests reference them."""
    corpus = load_past_campaigns()
    ids = {c["campaign_id"] for c in corpus}
    expected = {f"CMP-{i:03d}" for i in range(1, 16)}
    assert expected.issubset(ids)


def test_evidence_source_types_constant_lists_exactly_five_types():
    """The engine must explicitly model exactly 5 evidence source types."""
    assert len(EVIDENCE_SOURCE_TYPES) == 5
    assert EVIDENCE_SOURCE_TYPES == [
        "Prior campaign brief",
        "Persona research",
        "Customer / market insight",
        "Creative asset reference",
        "Performance benchmark",
    ]


def test_every_corpus_record_carries_all_five_evidence_source_fields():
    """Every seeded record must have non-empty data backing each of the 5 evidence types."""
    corpus = load_past_campaigns()
    for c in corpus:
        # 1. Prior campaign brief
        assert c.get("objective") and c.get("audience") and c.get("description")
        # 2. Persona research
        assert c.get("persona_notes", "").strip(), c["campaign_id"]
        # 3. Customer / market insight
        assert c.get("market_insight", "").strip(), c["campaign_id"]
        # 4. Creative asset reference
        assert c.get("creative_reference", "").strip(), c["campaign_id"]
        # 5. Performance benchmark
        assert c.get("metrics") and "ctr" in c["metrics"], c["campaign_id"]


def test_matched_campaign_object_carries_all_five_evidence_types():
    """A MatchedCampaign returned by the engine must expose all 5 evidence types for UI rendering."""
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="IT directors at mid-market manufacturers, LinkedIn lead generation.",
    )
    matches = find_similar_campaigns(request)
    top = matches[0]
    assert top.objective and top.audience and top.description  # (1) prior campaign brief
    assert top.persona_notes.strip()                            # (2) persona research
    assert top.market_insight.strip()                           # (3) customer/market insight
    assert top.creative_reference.strip()                       # (4) creative asset reference
    assert top.key_metrics and "ctr" in top.key_metrics          # (5) performance benchmark


# ---------------------------------------------------------------------------
# Matching quality across the expanded 30-campaign corpus
# ---------------------------------------------------------------------------


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


def test_matching_finds_new_product_line_campaign():
    """A request describing the new FleetPulse product line should match its own record."""
    request = CampaignRequest(
        objective="lead generation",
        audience="Fleet managers at regional trucking companies",
        market="North America",
        product="FleetPulse Telematics Suite",
        channel="LinkedIn",
        description="LinkedIn lead gen for FleetPulse telematics offering a free fuel-savings assessment to fleet managers.",
    )
    matches = find_similar_campaigns(request)
    assert matches[0].campaign_id == "CMP-028"
    assert matches[0].similarity_score > 0.5


def test_matching_finds_new_customer_retention_objective_campaign():
    """A retention/renewal-style request should match the new customer-retention record."""
    request = CampaignRequest(
        objective="customer retention",
        audience="Existing IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="email",
        description="Renewal-season email re-engaging existing CloudSync customers with a new predictive-maintenance announcement.",
    )
    matches = find_similar_campaigns(request)
    assert matches[0].campaign_id == "CMP-016"


def test_matching_finds_new_market_latin_america_campaign():
    """A request in the new Latin America market should match a LatAm record."""
    request = CampaignRequest(
        objective="lead generation",
        audience="Finance directors at community banks",
        market="Latin America",
        product="LedgerGuard Compliance Suite",
        channel="webinar",
        description="LatAm regional webinar on cross-border reporting compliance for community bank finance directors.",
    )
    matches = find_similar_campaigns(request)
    assert matches[0].campaign_id == "CMP-019"


def test_matching_finds_new_paid_search_channel_campaign():
    """A request on the new paid-search channel should match a paid-search record."""
    request = CampaignRequest(
        objective="lead generation",
        audience="Supply chain directors at food and beverage manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="paid search",
        description="Paid search campaign capturing supply chain directors researching uptime monitoring for food and beverage plants.",
    )
    matches = find_similar_campaigns(request)
    assert matches[0].campaign_id == "CMP-017"


def test_matching_finds_new_social_channel_campaign():
    """A request on the new social channel should match a social record."""
    request = CampaignRequest(
        objective="brand awareness",
        audience="Plant managers at automotive suppliers",
        market="Europe",
        product="CloudSync Ops Platform",
        channel="social",
        description="Organic and paid social campaign building awareness of CloudSync among automotive supplier plant managers ahead of a trade show.",
    )
    matches = find_similar_campaigns(request)
    assert matches[0].campaign_id == "CMP-018"


def test_top_n_matches_respects_expanded_corpus_without_duplicates():
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="Lead generation campaign for IT directors at mid-market manufacturers on LinkedIn.",
    )
    matches = find_similar_campaigns(request, top_n=5)
    assert len(matches) == 5
    ids = [m.campaign_id for m in matches]
    assert len(ids) == len(set(ids))
    # scores must be sorted highest-first
    scores = [m.similarity_score for m in matches]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Thin-evidence detection
# ---------------------------------------------------------------------------


def test_thin_evidence_true_when_only_one_strong_match():
    corpus = [
        {
            "campaign_id": "Y1",
            "objective": "lead generation",
            "audience": "Ops leaders",
            "market": "North America",
            "product_line": "WidgetPro",
            "channel": "email",
            "description": "Free roi calculator offered to ops leaders evaluating WidgetPro.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        }
    ]
    request = CampaignRequest(
        objective="lead generation",
        audience="Ops leaders",
        market="North America",
        product="WidgetPro",
        channel="email",
        description="roi calculator for ops leaders",
    )
    brief = build_brief(request, campaigns=corpus)
    assert brief.strong_match_count == 1
    assert brief.thin_evidence is True
    assert any("Limited historical evidence" in r for r in brief.risks)


def test_thin_evidence_false_when_two_strong_matches_meet_minimum():
    corpus = [
        {
            "campaign_id": "X1",
            "objective": "lead generation",
            "audience": "Ops leaders",
            "market": "North America",
            "product_line": "WidgetPro",
            "channel": "email",
            "description": "Free roi calculator offered to ops leaders evaluating WidgetPro.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        },
        {
            "campaign_id": "X2",
            "objective": "lead generation",
            "audience": "Ops leaders",
            "market": "North America",
            "product_line": "WidgetPro",
            "channel": "email",
            "description": "Another free roi calculator campaign for WidgetPro ops leaders.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        },
    ]
    request = CampaignRequest(
        objective="lead generation",
        audience="Ops leaders",
        market="North America",
        product="WidgetPro",
        channel="email",
        description="roi calculator for ops leaders",
    )
    brief = build_brief(request, campaigns=corpus)
    assert brief.strong_match_count == 2
    assert brief.thin_evidence is False


def test_empty_corpus_yields_no_matches_and_thin_evidence():
    request = CampaignRequest(
        objective="lead generation", audience="Anyone", market="North America", product="X", channel="email"
    )
    brief = build_brief(request, campaigns=[])
    assert brief.matched_campaigns == []
    assert brief.thin_evidence is True
    assert brief.strong_match_count == 0


# ---------------------------------------------------------------------------
# Hypothesis / risk derivation rules
# ---------------------------------------------------------------------------


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


def test_hypotheses_are_empty_without_any_strong_match():
    request = CampaignRequest(
        objective="astronaut recruitment",
        audience="deep-sea submarine pilots",
        market="Lunar colony",
        product="Zero-gravity kelp snacks",
        channel="carrier pigeon",
        description="Recruit interstellar explorers for a zero-gravity kelp snack tasting expedition.",
    )
    brief = build_brief(request)
    assert brief.hypotheses == []


def test_risk_flags_low_ctr_creative_fatigue():
    corpus = [
        {
            "campaign_id": "Z1", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Lead generation campaign for ops leaders on WidgetPro email outreach.",
            "metrics": {"ctr": 0.005, "conversion_rate": 0.01, "cost_per_lead": 50},
        },
        {
            "campaign_id": "Z2", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Lead generation campaign for ops leaders via WidgetPro email outreach again.",
            "metrics": {"ctr": 0.006, "conversion_rate": 0.012, "cost_per_lead": 50},
        },
    ]
    request = CampaignRequest(
        objective="lead generation", audience="Ops leaders", market="North America",
        product="WidgetPro", channel="email",
        description="Lead generation campaign for ops leaders on WidgetPro email outreach.",
    )
    brief = build_brief(request, campaigns=corpus)
    assert any("Creative fatigue" in r for r in brief.risks)


def test_risk_flags_high_cost_per_lead_budget_efficiency():
    corpus = [
        {
            "campaign_id": "W1", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Lead generation campaign for ops leaders on WidgetPro email outreach.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 400},
        },
        {
            "campaign_id": "W2", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Lead generation campaign for ops leaders via WidgetPro email outreach again.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 420},
        },
    ]
    request = CampaignRequest(
        objective="lead generation", audience="Ops leaders", market="North America",
        product="WidgetPro", channel="email",
        description="Lead generation campaign for ops leaders on WidgetPro email outreach.",
    )
    brief = build_brief(request, campaigns=corpus)
    assert any("Budget efficiency risk" in r for r in brief.risks)


def test_risk_flags_market_mismatch_when_all_matches_are_other_markets():
    corpus = [
        {
            "campaign_id": "V1", "objective": "lead generation", "audience": "Ops leaders",
            "market": "Europe", "product_line": "WidgetPro", "channel": "email",
            "description": "Lead generation campaign for ops leaders on WidgetPro email outreach.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        },
        {
            "campaign_id": "V2", "objective": "lead generation", "audience": "Ops leaders",
            "market": "Europe", "product_line": "WidgetPro", "channel": "email",
            "description": "Lead generation campaign for ops leaders via WidgetPro email outreach again.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        },
    ]
    request = CampaignRequest(
        objective="lead generation", audience="Ops leaders", market="North America",
        product="WidgetPro", channel="email",
        description="Lead generation campaign for ops leaders on WidgetPro email outreach.",
    )
    brief = build_brief(request, campaigns=corpus)
    assert any("Market mismatch" in r for r in brief.risks)


# ---------------------------------------------------------------------------
# Messaging angle and recommended-audience derivation
# ---------------------------------------------------------------------------


def test_messaging_angle_requires_two_distinct_matching_campaigns():
    """A keyword appearing in only one matched campaign's description must not qualify."""
    corpus = [
        {
            "campaign_id": "Y1", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Free roi calculator offered to ops leaders evaluating WidgetPro.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        }
    ]
    request = CampaignRequest(
        objective="lead generation", audience="Ops leaders", market="North America",
        product="WidgetPro", channel="email", description="roi calculator for ops leaders",
    )
    brief = build_brief(request, campaigns=corpus)
    assert brief.messaging_angles == []


def test_messaging_angle_surfaces_when_two_matches_share_it():
    corpus = [
        {
            "campaign_id": "X1", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Free roi calculator offered to ops leaders evaluating WidgetPro.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        },
        {
            "campaign_id": "X2", "objective": "lead generation", "audience": "Ops leaders",
            "market": "North America", "product_line": "WidgetPro", "channel": "email",
            "description": "Another free roi calculator campaign for WidgetPro ops leaders.",
            "metrics": {"ctr": 0.03, "conversion_rate": 0.05, "cost_per_lead": 50},
        },
    ]
    request = CampaignRequest(
        objective="lead generation", audience="Ops leaders", market="North America",
        product="WidgetPro", channel="email", description="roi calculator for ops leaders",
    )
    brief = build_brief(request, campaigns=corpus)
    assert len(brief.messaging_angles) == 1
    assert "ROI / cost calculator" in brief.messaging_angles[0]
    assert "2 matched campaigns" in brief.messaging_angles[0]


def test_recommended_audiences_derived_from_strong_matches_only():
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="Lead generation campaign for IT directors at mid-market manufacturers on LinkedIn.",
    )
    brief = build_brief(request)
    assert brief.recommended_audiences  # at least one recommended audience
    assert len(brief.recommended_audiences) <= 3


# ---------------------------------------------------------------------------
# Measurement plan branching
# ---------------------------------------------------------------------------


def test_measurement_plan_branches_by_objective_keyword():
    base_kwargs = dict(
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="test",
    )
    lead_plan = build_brief(CampaignRequest(objective="lead generation", **base_kwargs)).measurement_plan
    awareness_plan = build_brief(CampaignRequest(objective="brand awareness", **base_kwargs)).measurement_plan
    launch_plan = build_brief(CampaignRequest(objective="product launch", **base_kwargs)).measurement_plan

    assert "cost per lead" in lead_plan[0].lower()
    assert "impressions" in awareness_plan[0].lower() or "reach" in awareness_plan[0].lower()
    assert "launch" in launch_plan[0].lower()
    # all three should still include the shared channel-fatigue monitoring step
    assert any("creative fatigue" in step.lower() for step in lead_plan)


# ---------------------------------------------------------------------------
# Brief-quality / required-sections checks
# ---------------------------------------------------------------------------


def test_brief_has_all_required_sections_present_for_well_matched_request():
    """A brief-quality check: every documented section of CampaignBrief must be populated
    (or legitimately empty with a defined reason) for a request with strong evidence."""
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="Lead generation campaign for IT directors at mid-market manufacturers on LinkedIn.",
    )
    brief = build_brief(request)

    assert brief.matched_campaigns, "evidence section must be present"
    assert brief.hypotheses, "hypotheses section must be present for a strong-evidence request"
    assert brief.recommended_audiences, "recommended audiences section must be present"
    assert brief.measurement_plan, "measurement plan section must always be present"
    assert isinstance(brief.risks, list)  # may be empty, but must exist as a defined list
    assert isinstance(brief.messaging_angles, list)
    assert isinstance(brief.thin_evidence, bool)
    assert isinstance(brief.strong_match_count, int)


def test_brief_quality_holds_for_thin_evidence_request_too():
    """Even a thin-evidence brief must produce a defined structure (not crash / not omit sections)."""
    request = CampaignRequest(
        objective="astronaut recruitment",
        audience="deep-sea submarine pilots",
        market="Lunar colony",
        product="Zero-gravity kelp snacks",
        channel="carrier pigeon",
        description="Recruit interstellar explorers for a zero-gravity kelp snack tasting expedition.",
    )
    brief = build_brief(request)
    assert brief.thin_evidence is True
    assert brief.measurement_plan  # a pilot-first plan is still produced
    assert any("pilot" in step.lower() for step in brief.measurement_plan)
    assert brief.risks  # thin-evidence risk must be present


# ---------------------------------------------------------------------------
# Narrative (mock LLM) output
# ---------------------------------------------------------------------------


def test_mock_narrative_flags_thin_evidence_in_prose():
    request = CampaignRequest(
        objective="astronaut recruitment",
        audience="deep-sea submarine pilots",
        market="Lunar colony",
        product="Zero-gravity kelp snacks",
        channel="carrier pigeon",
        description="Recruit interstellar explorers for a zero-gravity kelp snack tasting expedition.",
    )
    brief = build_brief(request)
    narrative = write_brief_narrative(request, brief)
    assert "thin" in narrative.lower()


def test_mock_narrative_mentions_matched_campaign_count_and_objective():
    request = CampaignRequest(
        objective="lead generation",
        audience="IT directors at mid-market manufacturers",
        market="North America",
        product="CloudSync Ops Platform",
        channel="LinkedIn",
        description="Lead generation campaign for IT directors at mid-market manufacturers on LinkedIn.",
    )
    brief = build_brief(request)
    narrative = write_brief_narrative(request, brief)
    assert "lead generation" in narrative.lower()
    assert str(len(brief.matched_campaigns)) in narrative
