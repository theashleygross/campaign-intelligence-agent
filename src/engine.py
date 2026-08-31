"""Core matching + evidence-derivation logic for the Campaign Intelligence Agent.

This module is the deterministic "brain" of the demo. Given a new campaign
request, it:

1. Builds a text representation of every synthetic past campaign and of the
   new request, and ranks past campaigns by TF-IDF cosine similarity
   (`find_similar_campaigns`). No LLM call happens here.
2. Derives hypotheses, messaging angles, recommended audiences, risks, and a
   measurement plan purely from the metrics/patterns of the matched
   campaigns (`build_brief`). Every derived statement can be traced back to
   a rule applied to the matched data.

`src/llm.py` may later take this deterministic output and polish it into
prose, but it never changes which campaigns matched or what the metrics are.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.models import CampaignBrief, CampaignRequest, MatchedCampaign

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "past_campaigns.json"

# Tuning constants -- deliberately simple and named so they're easy to reason
# about and to exercise from tests.
TOP_N_MATCHES = 5
SIMILARITY_THRESHOLD = 0.20      # a match counts as "strong evidence" at/above this score
MIN_STRONG_MATCHES = 2           # fewer strong matches than this => thin evidence
LOW_CTR_BASELINE = 0.015         # below this, flag creative fatigue / engagement risk
HIGH_COST_PER_LEAD_BASELINE = 150.0  # above this, flag budget efficiency risk

# The 5 evidence source types this engine explicitly models for every matched
# campaign. Each maps to a concrete field carried on `MatchedCampaign` so the
# UI can render one clearly labeled block per source type in the Evidence
# panel. This list is also the source of truth for the "5 evidence sources"
# figure shown in the app's metrics panel and README.
EVIDENCE_SOURCE_TYPES: List[str] = [
    "Prior campaign brief",
    "Persona research",
    "Customer / market insight",
    "Creative asset reference",
    "Performance benchmark",
]

# Candidate messaging-angle keywords found in past campaign descriptions,
# mapped to a human-readable angle. A keyword must show up in the
# description of 2+ distinct matched campaigns to be surfaced (see
# `_derive_messaging_angles`).
ANGLE_KEYWORDS: Dict[str, str] = {
    "calculator": "ROI / cost calculator as the lead magnet",
    "roi": "ROI / cost calculator as the lead magnet",
    "assessment": "Free assessment or audit as the lead magnet",
    "audit": "Free assessment or audit as the lead magnet",
    "webinar": "Live educational webinar format",
    "compliance": "Regulatory / compliance angle",
    "regulatory": "Regulatory / compliance angle",
    "forecasting": "Predictive / forecasting capability angle",
    "predictive": "Predictive / forecasting capability angle",
    "downtime": "Uptime / downtime cost-reduction angle",
    "shrinkage": "Loss / shrinkage reduction angle",
    "launch": "New-feature launch announcement",
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "on", "in", "at", "with",
    "new", "this", "that", "into", "among", "across", "featuring", "targeting",
}


@lru_cache(maxsize=1)
def load_past_campaigns(path: Optional[str] = None) -> List[dict]:
    """Load the synthetic past-campaign corpus from JSON.

    Cached because the corpus is static demo data; pass a `path` override
    (e.g. in tests) to bypass the cache and load a different file.
    """
    target = Path(path) if path else DATA_PATH
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def _campaign_to_text(campaign: dict) -> str:
    """Concatenate a past campaign's fields into one text blob for TF-IDF."""
    parts = [
        campaign.get("objective", ""),
        campaign.get("audience", ""),
        campaign.get("market", ""),
        campaign.get("product_line", ""),
        campaign.get("channel", ""),
        campaign.get("description", ""),
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def find_similar_campaigns(
    request: CampaignRequest,
    campaigns: Optional[List[dict]] = None,
    top_n: int = TOP_N_MATCHES,
) -> List[MatchedCampaign]:
    """Rank past campaigns against `request` by TF-IDF cosine similarity.

    Returns the top `top_n` matches (highest similarity first) regardless of
    how weak the similarity is -- callers use `SIMILARITY_THRESHOLD` to
    decide which of those are "strong" evidence vs. thin evidence.
    """
    corpus = campaigns if campaigns is not None else load_past_campaigns()
    if not corpus:
        return []

    documents = [_campaign_to_text(c) for c in corpus]
    query_text = request.to_text()

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(documents + [query_text])

    corpus_vectors = tfidf_matrix[:-1]
    query_vector = tfidf_matrix[-1]

    scores = cosine_similarity(query_vector, corpus_vectors)[0]

    ranked_indices = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    top_indices = ranked_indices[:top_n]

    matches: List[MatchedCampaign] = []
    for i in top_indices:
        campaign = corpus[i]
        matches.append(
            MatchedCampaign(
                campaign_id=campaign.get("campaign_id", f"CMP-{i}"),
                similarity_score=round(float(scores[i]), 4),
                key_metrics=dict(campaign.get("metrics", {})),
                objective=campaign.get("objective", ""),
                audience=campaign.get("audience", ""),
                market=campaign.get("market", ""),
                product_line=campaign.get("product_line", ""),
                channel=campaign.get("channel", ""),
                description=campaign.get("description", ""),
                persona_notes=campaign.get("persona_notes", ""),
                market_insight=campaign.get("market_insight", ""),
                creative_reference=campaign.get("creative_reference", ""),
            )
        )
    return matches


def _strong_matches(matches: List[MatchedCampaign]) -> List[MatchedCampaign]:
    return [m for m in matches if m.similarity_score >= SIMILARITY_THRESHOLD]


def _avg(values: List[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _derive_hypotheses(request: CampaignRequest, matches: List[MatchedCampaign]) -> List[str]:
    strong = _strong_matches(matches)
    if not strong:
        return []

    hypotheses: List[str] = []

    all_ctr = [m.key_metrics.get("ctr", 0.0) for m in strong if "ctr" in m.key_metrics]
    all_conv = [m.key_metrics.get("conversion_rate", 0.0) for m in strong if "conversion_rate" in m.key_metrics]
    all_cpl = [m.key_metrics.get("cost_per_lead", 0.0) for m in strong if "cost_per_lead" in m.key_metrics]

    if all_ctr and all_conv:
        hypotheses.append(
            f"Based on {len(strong)} similar past campaign(s), expect a CTR around "
            f"{_avg(all_ctr) * 100:.1f}% and a conversion rate around {_avg(all_conv) * 100:.1f}%."
        )

    # Channel-specific hypothesis.
    channel_matches = [m for m in strong if m.channel.lower() == request.channel.lower()]
    if channel_matches:
        cpl_values = [m.key_metrics.get("cost_per_lead", 0.0) for m in channel_matches if "cost_per_lead" in m.key_metrics]
        if cpl_values:
            hypotheses.append(
                f"On {request.channel}, {len(channel_matches)} matched campaign(s) averaged "
                f"${_avg(cpl_values):.2f} cost per lead -- use this as the initial budget benchmark."
            )

    # Objective-specific hypothesis.
    objective_matches = [m for m in strong if m.objective.lower() == request.objective.lower()]
    if objective_matches and objective_matches != channel_matches:
        conv_values = [m.key_metrics.get("conversion_rate", 0.0) for m in objective_matches if "conversion_rate" in m.key_metrics]
        if conv_values:
            hypotheses.append(
                f"Past '{request.objective}' campaigns in this dataset converted at "
                f"{_avg(conv_values) * 100:.1f}% on average -- a reasonable target for this campaign."
            )

    if all_cpl and not channel_matches:
        hypotheses.append(
            f"Across all {len(strong)} matched campaign(s), average cost per lead was "
            f"${_avg(all_cpl):.2f}, offering a rough budget anchor even without a same-channel match."
        )

    return hypotheses


def _derive_risks(request: CampaignRequest, matches: List[MatchedCampaign], thin_evidence: bool) -> List[str]:
    risks: List[str] = []
    strong = _strong_matches(matches)

    if thin_evidence:
        risks.append(
            "Limited historical evidence: fewer than "
            f"{MIN_STRONG_MATCHES} closely similar past campaigns were found "
            f"(similarity >= {SIMILARITY_THRESHOLD}). Treat recommendations as low-confidence "
            "and validate with a small pilot before scaling spend."
        )

    if not strong:
        return risks

    channel_matches = [m for m in strong if m.channel.lower() == request.channel.lower()]
    ctr_pool = channel_matches or strong
    ctr_values = [m.key_metrics.get("ctr", 0.0) for m in ctr_pool if "ctr" in m.key_metrics]
    if ctr_values and _avg(ctr_values) < LOW_CTR_BASELINE:
        scope = f"on {request.channel}" if channel_matches else "across matched campaigns"
        risks.append(
            f"Creative fatigue / low engagement risk: historical CTR {scope} averaged "
            f"{_avg(ctr_values) * 100:.2f}%, below the {LOW_CTR_BASELINE * 100:.1f}% baseline. "
            "Plan for creative refresh and A/B testing from launch."
        )

    cpl_values = [m.key_metrics.get("cost_per_lead", 0.0) for m in strong if "cost_per_lead" in m.key_metrics]
    if cpl_values and _avg(cpl_values) > HIGH_COST_PER_LEAD_BASELINE:
        risks.append(
            f"Budget efficiency risk: matched campaigns averaged ${_avg(cpl_values):.2f} cost per lead, "
            f"above the ${HIGH_COST_PER_LEAD_BASELINE:.0f} baseline. Confirm budget expectations with stakeholders."
        )

    other_market_matches = [m for m in strong if m.market.lower() != request.market.lower()]
    if len(other_market_matches) == len(strong) and strong:
        markets = sorted({m.market for m in strong})
        risks.append(
            f"Market mismatch: all matched historical campaigns ran in a different market "
            f"({', '.join(markets)}) than the requested {request.market}. Regional response may vary "
            "and local market research is recommended."
        )

    return risks


def _derive_messaging_angles(matches: List[MatchedCampaign]) -> List[str]:
    strong = _strong_matches(matches)
    if not strong:
        return []

    # For each matched campaign, find which angle phrases its description
    # triggers (as a set, so a repeated keyword in one description only
    # counts once toward that campaign's contribution).
    phrase_campaign_counts: Dict[str, int] = {}
    for m in strong:
        text = m.description.lower()
        triggered_phrases = {phrase for kw, phrase in ANGLE_KEYWORDS.items() if kw in text}
        for phrase in triggered_phrases:
            phrase_campaign_counts[phrase] = phrase_campaign_counts.get(phrase, 0) + 1

    # Only surface an angle when 2+ distinct matched campaigns used it.
    qualifying = [(phrase, count) for phrase, count in phrase_campaign_counts.items() if count >= 2]
    qualifying.sort(key=lambda pair: (-pair[1], pair[0]))

    return [f"{phrase} (seen in {count} matched campaigns)" for phrase, count in qualifying]


def _derive_recommended_audiences(request: CampaignRequest, matches: List[MatchedCampaign]) -> List[str]:
    strong = _strong_matches(matches)
    if not strong:
        return []

    # Rank distinct audiences from matches by (count of matches, total similarity),
    # excluding an exact restatement of the requested audience unless nothing else exists.
    scores: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for m in strong:
        scores[m.audience] = scores.get(m.audience, 0.0) + m.similarity_score
        counts[m.audience] = counts.get(m.audience, 0) + 1

    ranked = sorted(scores.keys(), key=lambda a: (-counts[a], -scores[a], a))
    return ranked[:3]


def _derive_measurement_plan(request: CampaignRequest, matches: List[MatchedCampaign], thin_evidence: bool) -> List[str]:
    strong = _strong_matches(matches)
    plan: List[str] = []

    objective = request.objective.lower()
    if "lead" in objective:
        plan.append("Track leads generated and cost per lead weekly against the historical benchmark above.")
        plan.append("Set up funnel tracking from click -> form fill -> marketing-qualified lead (MQL).")
    elif "awareness" in objective:
        plan.append("Track impressions, reach, and frequency; pair with a brand-lift or aided-awareness survey.")
        plan.append("Monitor branded search volume before/after flight as a directional awareness signal.")
    elif "launch" in objective:
        plan.append("Track launch-week engagement (CTR, webinar/email opens) plus pipeline sourced in the 30 days post-launch.")
        plan.append("Compare early conversion rate against the historical benchmark above to gauge launch resonance.")
    else:
        plan.append("Track CTR and conversion rate weekly against the historical benchmark above.")

    plan.append(f"Monitor CTR specifically on {request.channel} for early signs of creative fatigue.")

    if thin_evidence or not strong:
        plan.append(
            "Run a small-budget pilot first and re-run this matching engine once fresh results are "
            "available, since current historical evidence is thin."
        )
    else:
        plan.append(
            f"Re-forecast after the first {min(4, max(2, len(strong)))} weeks of live data and compare "
            "actuals against the matched campaigns' metrics."
        )

    return plan


def build_brief(request: CampaignRequest, campaigns: Optional[List[dict]] = None) -> CampaignBrief:
    """Run the full deterministic pipeline: match -> derive evidence -> assemble brief."""
    matches = find_similar_campaigns(request, campaigns=campaigns, top_n=TOP_N_MATCHES)
    strong = _strong_matches(matches)
    thin_evidence = len(strong) < MIN_STRONG_MATCHES

    brief = CampaignBrief(
        matched_campaigns=matches,
        hypotheses=_derive_hypotheses(request, matches),
        messaging_angles=_derive_messaging_angles(matches),
        recommended_audiences=_derive_recommended_audiences(request, matches),
        risks=_derive_risks(request, matches, thin_evidence),
        measurement_plan=_derive_measurement_plan(request, matches, thin_evidence),
        strong_match_count=len(strong),
        thin_evidence=thin_evidence,
    )
    return brief
