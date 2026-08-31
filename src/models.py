"""Domain data models for the Campaign Intelligence Agent.

Plain dataclasses (no ORM, no framework) describing the shape of a new
campaign request and the evidence-backed brief the engine produces. Keeping
these typed keeps `src/engine.py` testable and keeps `app.py` from passing
loose dicts around.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CampaignRequest:
    """Everything the Streamlit form collects for a proposed new campaign."""

    objective: str          # e.g. "lead generation", "brand awareness", "product launch"
    audience: str            # e.g. "IT directors at mid-market manufacturers"
    market: str               # e.g. "North America", "Europe", "Asia-Pacific"
    product: str              # product line name
    channel: str              # e.g. "LinkedIn", "email", "webinar", "display"
    description: str = ""     # free-text notes on the campaign concept

    def to_text(self) -> str:
        """Concatenate all fields into one text blob for TF-IDF comparison."""
        parts = [
            self.objective,
            self.audience,
            self.market,
            self.product,
            self.channel,
            self.description,
        ]
        return " ".join(p.strip() for p in parts if p and p.strip())


@dataclass
class MatchedCampaign:
    """One past campaign matched against a new request, with its evidence.

    Carries all 5 evidence source types the engine models for this campaign:
    1. Prior campaign brief    -- objective/audience/market/product_line/channel/description
    2. Persona research        -- `persona_notes`
    3. Customer/market insight -- `market_insight`
    4. Creative asset reference-- `creative_reference`
    5. Performance benchmark   -- `key_metrics`
    """

    campaign_id: str
    similarity_score: float          # cosine similarity, 0-1
    key_metrics: dict                # ctr, conversion_rate, cost_per_lead, etc. (evidence type 5)
    objective: str = ""
    audience: str = ""
    market: str = ""
    product_line: str = ""
    channel: str = ""
    description: str = ""
    persona_notes: str = ""          # evidence type 2: persona research
    market_insight: str = ""         # evidence type 3: customer/market insight
    creative_reference: str = ""     # evidence type 4: creative asset reference


@dataclass
class CampaignBrief:
    """Full output bundle the app renders: matched evidence + recommendation."""

    matched_campaigns: List[MatchedCampaign] = field(default_factory=list)
    hypotheses: List[str] = field(default_factory=list)
    messaging_angles: List[str] = field(default_factory=list)
    recommended_audiences: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    measurement_plan: List[str] = field(default_factory=list)

    # Evidence coverage bookkeeping (set by the engine, read by the UI).
    strong_match_count: int = 0        # matches at/above the similarity threshold
    thin_evidence: bool = False        # True if strong_match_count < 2
    narrative: str = ""                # optional LLM-polished narrative (live mode only)
