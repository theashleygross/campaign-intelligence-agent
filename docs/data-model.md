# Data model

This document describes the dataclasses in `src/models.py` and the shape of
the seeded synthetic records in `data/synthetic/past_campaigns.json`.

## Seeded corpus: `data/synthetic/past_campaigns.json`

**Exactly 30 fictional campaign records** (`CMP-001` through `CMP-030`).
`CMP-001`-`CMP-015` are the original 15 records (kept unchanged so existing
tests that reference them by ID and metrics still pass); `CMP-016`-`CMP-030`
are 15 additional records added for scale and variety, spanning:

- **Objectives:** lead generation, brand awareness, product launch, and the
  newly added *customer retention*.
- **Markets:** North America, Europe, Asia-Pacific, and the newly added
  *Latin America*.
- **Channels:** LinkedIn, display, email, webinar, and the newly added
  *paid search* and *social*.
- **Product lines:** CloudSync Ops Platform, LedgerGuard Compliance Suite,
  StaffWell Scheduling, ShelfSense Inventory AI, and the newly added
  *FleetPulse Telematics Suite*.

Each record is a flat JSON object with this shape:

```jsonc
{
  "campaign_id": "CMP-001",
  "objective": "lead generation",
  "audience": "IT directors at mid-market manufacturers",
  "market": "North America",
  "product_line": "CloudSync Ops Platform",
  "channel": "LinkedIn",
  "description": "Sponsored LinkedIn content targeting IT directors ...",

  "persona_notes": "IT Director, 40-55, manages plant-floor systems uptime ...",
  "market_insight": "Mid-market manufacturers report downtime costs averaging $260/minute ...",
  "creative_reference": "LinkedIn carousel ad, headline 'What does an hour of downtime really cost you?' ...",

  "metrics": {
    "ctr": 0.021,
    "conversion_rate": 0.034,
    "cost_per_lead": 88.5,
    "impressions": 210000,
    "leads": 145
  }
}
```

### Field -> evidence-source-type mapping

The release brief requires the engine to explicitly model **5 evidence
source types**. Every seeded record carries the data for all 5, and every
field maps to exactly one type:

| # | Evidence source type | Backing field(s) |
|---|---|---|
| 1 | Prior campaign brief | `objective`, `audience`, `market`, `product_line`, `channel`, `description` |
| 2 | Persona research | `persona_notes` |
| 3 | Customer / market insight | `market_insight` |
| 4 | Creative asset reference | `creative_reference` |
| 5 | Performance benchmark | `metrics` (`ctr`, `conversion_rate`, `cost_per_lead`, `impressions`, `leads`) |

`src/engine.py:EVIDENCE_SOURCE_TYPES` is the single source of truth for the
list of 5 labels (used by both the app's metrics panel and this doc).

Note: TF-IDF matching (`_campaign_to_text` in `src/engine.py`) is
deliberately unchanged by this release pass -- it still concatenates only
`objective`, `audience`, `market`, `product_line`, `channel`, `description`
(evidence type 1). `persona_notes`, `market_insight`, and
`creative_reference` are carried through for **display** in the evidence
panel; they are not inputs to the similarity score. This keeps the
independently-audited matching logic in `src/engine.py` untouched.

## `src/models.py` dataclasses

### `CampaignRequest`

The Streamlit form's inputs, and the query object passed into the engine.

| Field | Type | Notes |
|---|---|---|
| `objective` | `str` | e.g. "lead generation", "brand awareness", "product launch", "customer retention" |
| `audience` | `str` | free text |
| `market` | `str` | e.g. "North America", "Europe", "Asia-Pacific", "Latin America" |
| `product` | `str` | free text product/product-line name |
| `channel` | `str` | e.g. "LinkedIn", "email", "webinar", "display", "paid search", "social" |
| `description` | `str` | optional free-text campaign concept, default `""` |

`to_text()` concatenates all fields into one string for TF-IDF comparison
against the corpus.

### `MatchedCampaign`

One past campaign matched against a request, carrying all 5 evidence types.

| Field | Type | Evidence type |
|---|---|---|
| `campaign_id` | `str` | -- |
| `similarity_score` | `float` (0-1, cosine similarity) | -- |
| `key_metrics` | `dict` | 5. Performance benchmark |
| `objective`, `audience`, `market`, `product_line`, `channel`, `description` | `str` | 1. Prior campaign brief |
| `persona_notes` | `str` | 2. Persona research |
| `market_insight` | `str` | 3. Customer/market insight |
| `creative_reference` | `str` | 4. Creative asset reference |

### `CampaignBrief`

The full output bundle the app renders.

| Field | Type | Notes |
|---|---|---|
| `matched_campaigns` | `List[MatchedCampaign]` | top-N ranked matches (evidence panel) |
| `hypotheses` | `List[str]` | derived from strong matches' metrics |
| `messaging_angles` | `List[str]` | keyword-based, requires 2+ matching campaigns |
| `recommended_audiences` | `List[str]` | ranked by match count + similarity |
| `risks` | `List[str]` | rule-based flags (thin evidence, low CTR, high cost/lead, market mismatch) |
| `measurement_plan` | `List[str]` | branches by request objective |
| `strong_match_count` | `int` | matches at/above `SIMILARITY_THRESHOLD` |
| `thin_evidence` | `bool` | `True` when `strong_match_count < MIN_STRONG_MATCHES` |
| `narrative` | `str` | unused placeholder field; the actual narrative is returned separately by `write_brief_narrative()` and held in `st.session_state["narrative"]` in `app.py` |

## Tuning constants (`src/engine.py`)

| Constant | Value | Meaning |
|---|---|---|
| `TOP_N_MATCHES` | 5 | number of ranked matches returned |
| `SIMILARITY_THRESHOLD` | 0.20 | minimum cosine similarity to count as a "strong" match |
| `MIN_STRONG_MATCHES` | 2 | fewer strong matches than this triggers `thin_evidence` |
| `LOW_CTR_BASELINE` | 0.015 | below this average CTR, flag creative-fatigue risk |
| `HIGH_COST_PER_LEAD_BASELINE` | 150.0 | above this average cost/lead, flag budget-efficiency risk |

These are illustrative defaults for a synthetic demo corpus, not values
validated against real campaign outcomes (see `docs/limitations.md`).
