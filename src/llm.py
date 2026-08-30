"""LLM adapter: deterministic mock narrative writer + optional live Claude call.

Non-negotiable per the portfolio standard: the LLM never decides which past
campaigns matched, what their metrics are, or what the derived
hypotheses/risks are -- that all comes from `src/engine.py`. This module
only turns that already-decided evidence into readable prose.

- MOCK_MODE=true (default): `write_brief_narrative` assembles a real,
  useful narrative from the brief using string templates -- no network call,
  no API key required.
- MOCK_MODE=false + ANTHROPIC_API_KEY set: `write_brief_narrative` sends the
  matched campaigns + derived hypotheses/risks to Claude (model
  `claude-sonnet-5`) and asks it to write a polished brief narrative from
  that fixed evidence, without inventing new numbers or matches.
"""

from __future__ import annotations

import os

from src.models import CampaignBrief, CampaignRequest


def _is_mock_mode() -> bool:
    return os.environ.get("MOCK_MODE", "true").strip().lower() != "false"


def _mock_narrative(request: CampaignRequest, brief: CampaignBrief) -> str:
    """Deterministic, template-based narrative -- fully functional with zero setup."""
    lines: list[str] = []

    lines.append(
        f"For this {request.objective} campaign targeting {request.audience} "
        f"in {request.market} via {request.channel}, we found "
        f"{len(brief.matched_campaigns)} comparable past campaign(s), "
        f"{brief.strong_match_count} of which are strong matches "
        f"(similarity >= threshold)."
    )

    if brief.thin_evidence:
        lines.append(
            "Evidence is thin for this profile -- treat the points below as directional "
            "hypotheses rather than proven benchmarks, and validate with a small pilot."
        )

    if brief.hypotheses:
        lines.append("Historical evidence suggests: " + " ".join(brief.hypotheses))

    if brief.messaging_angles:
        lines.append(
            "Candidate messaging angles worth testing, based on repeated use in similar past "
            "campaigns: " + "; ".join(brief.messaging_angles) + "."
        )

    if brief.recommended_audiences:
        lines.append(
            "Audiences that responded well to similar campaigns: "
            + ", ".join(brief.recommended_audiences) + "."
        )

    if brief.risks:
        lines.append("Key risks to plan for: " + " ".join(brief.risks))

    if brief.measurement_plan:
        lines.append("Recommended measurement plan: " + " ".join(brief.measurement_plan))

    return " ".join(lines)


def _live_narrative(request: CampaignRequest, brief: CampaignBrief) -> str:
    """Ask Claude to polish the deterministic evidence into prose. Live mode only."""
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only in live mode
        raise RuntimeError(
            "The 'anthropic' package is required for live mode. Install it via "
            "requirements.txt, or set MOCK_MODE=true."
        ) from exc

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set; cannot run in live mode.")

    client = anthropic.Anthropic(api_key=api_key)

    matches_summary = "\n".join(
        f"- {m.campaign_id} (similarity {m.similarity_score}): {m.objective} / {m.audience} / "
        f"{m.market} / {m.channel} -- metrics: {m.key_metrics}"
        for m in brief.matched_campaigns
    )

    prompt = f"""You are a marketing strategist writing a short campaign brief narrative.

New campaign request:
- Objective: {request.objective}
- Audience: {request.audience}
- Market: {request.market}
- Product: {request.product}
- Channel: {request.channel}
- Description: {request.description}

Matched historical campaigns (ground truth -- do not invent or alter these):
{matches_summary}

Deterministically derived hypotheses (ground truth): {brief.hypotheses}
Deterministically derived risks (ground truth): {brief.risks}
Deterministically derived messaging angles (ground truth): {brief.messaging_angles}
Deterministically derived recommended audiences (ground truth): {brief.recommended_audiences}
Deterministically derived measurement plan (ground truth): {brief.measurement_plan}

Write a concise (150-250 word) narrative brief for a marketer, in prose, that
weaves together the evidence above. Do not invent new campaign matches,
metrics, or numbers beyond what is listed. Clearly note where a point is
"observed" from past campaigns vs. an "AI recommendation" built on top of it.
"""

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if hasattr(block, "text"))


def write_brief_narrative(request: CampaignRequest, brief: CampaignBrief) -> str:
    """Produce a narrative for the brief -- deterministic mock, or live Claude call."""
    if _is_mock_mode():
        return _mock_narrative(request, brief)
    return _live_narrative(request, brief)
