# Architecture

The Campaign Intelligence Agent turns a new campaign request into an
evidence-backed brief by first retrieving similar historical campaigns with a
deterministic similarity engine, then deriving hypotheses and risks from
their real metrics, and only optionally handing the fixed evidence to Claude
to polish into prose.

```mermaid
flowchart TD
    A[Marketer submits campaign request\nobjective, audience, market, product, channel, description] --> B[TF-IDF similarity engine\nsrc/engine.py]
    C[(Synthetic campaign corpus\ndata/synthetic/past_campaigns.json)] --> B
    B --> D[Ranked past campaigns\ntop 3-5 + cosine similarity scores]
    D --> E[Evidence extraction\nmetrics + rule-based pattern detection]
    E --> F[Hypotheses]
    E --> G[Risks]
    E --> H[Messaging angles]
    E --> I[Recommended audiences]
    E --> J[Measurement plan]
    F --> K{MOCK_MODE?}
    G --> K
    H --> K
    I --> K
    J --> K
    D --> K
    K -->|true, default| L[Template narrative writer\nsrc/llm.py mock path]
    K -->|false + API key| M[Claude claude-sonnet-5\nsrc/llm.py live path]
    L --> N[Streamlit UI\napp.py]
    M --> N
    D --> O[Evidence panel\nlabeled: Observed data]
    F --> P[Recommendation panel\nlabeled: AI-assisted recommendation]
    G --> P
    H --> P
    I --> P
    J --> P
    O --> N
    P --> N
```

## Components

- **`src/models.py`** -- `CampaignRequest` (the form inputs), `MatchedCampaign`
  (one matched campaign carrying all 5 evidence source types -- see below),
  and `CampaignBrief` (the full output: matched campaigns, hypotheses,
  messaging angles, recommended audiences, risks, measurement plan, and
  coverage bookkeeping).
- **`src/engine.py`** -- the deterministic core. Builds a text
  representation of every past campaign and the new request, ranks past
  campaigns with `TfidfVectorizer` + `cosine_similarity` (scikit-learn, no
  LLM involved), and derives hypotheses/risks/messaging angles/recommended
  audiences/measurement plan from simple, auditable rules applied to the
  matched campaigns' real metrics. `EVIDENCE_SOURCE_TYPES` is the source of
  truth for the 5 evidence source types this engine models: prior campaign
  brief, persona research, customer/market insight, creative asset
  reference, and performance benchmark (see `docs/data-model.md`).
- **`src/llm.py`** -- takes the engine's fixed output (which campaigns
  matched, their metrics, the derived hypotheses/risks) and turns it into a
  narrative. In mock mode (default) this is a deterministic template -- no
  network call. In live mode it calls Claude (`claude-sonnet-5`) to write
  polished prose from the same fixed evidence; it cannot change which
  campaigns matched or invent new metrics.
- **`app.py`** -- Streamlit UI. Renders an **Evidence** panel (one expander
  per matched campaign with all 5 evidence source types labeled and
  displayed separately -- "Observed data") and a separate **Recommendation**
  panel (hypotheses, messaging angles, recommended audiences, risks,
  measurement plan -- labeled "AI-assisted recommendation, review before
  use"), a coverage indicator that flags when fewer than 2 matches clear the
  similarity threshold ("thin evidence"), a 3-metric transparency panel (30
  campaigns / 5 evidence types / verified test count), an explicit **human
  review checkpoint** (Approve brief / Request revision, in-session state
  only), and a **Reset state** control that clears the form and any
  generated brief.
