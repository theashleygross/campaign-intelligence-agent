# Known limitations

These are **prototype limitations** -- intentional scope boundaries for a
public portfolio demo -- not defects. The independent build+audit pass and
this release pass found no defects in `src/engine.py`'s matching or
evidence-derivation logic (31/31 tests pass; see `docs/evaluation-plan.md`).

## Data

- **Synthetic 30-campaign corpus only.** Every company name, persona note,
  market insight, creative reference, and metric in
  `data/synthetic/past_campaigns.json` is fictional, generated for this
  demo. None of it is real historical campaign performance data.
- **Illustrative rule thresholds.** `SIMILARITY_THRESHOLD` (0.20),
  `MIN_STRONG_MATCHES` (2), `LOW_CTR_BASELINE` (0.015), and
  `HIGH_COST_PER_LEAD_BASELINE` ($150) in `src/engine.py` are reasonable
  defaults chosen for demo purposes, not values tuned or validated against
  real campaign outcomes.
- **No persistence.** Nothing a user submits through the form is saved
  anywhere; there is no database. A page refresh (or the in-app "Reset
  state" button) discards the current session's request and brief.

## Matching and evidence

- **Persona research, market insight, and creative reference are
  display-only evidence.** They are carried through to the Evidence panel
  for every matched campaign, but (by design, to avoid touching the
  independently audited core matching logic) they are not inputs to the
  TF-IDF similarity score -- only `objective`, `audience`, `market`,
  `product_line`, `channel`, and `description` participate in matching.
- **Not a predictive/ML model.** Campaign matching is TF-IDF cosine
  similarity over text fields (a classic information-retrieval technique),
  not a trained forecasting or machine-learning model. It cannot generalize
  beyond vocabulary overlap with the seeded corpus.
- **Keyword-based messaging angles.** `ANGLE_KEYWORDS` in `src/engine.py` is
  a small, hand-curated dictionary. It will miss genuinely repeated angles
  phrased with different words, and a coincidental keyword match in a
  single campaign is filtered out only by the "2+ campaigns" rule, not by
  any semantic check.

## Human review

- **The Approve / Request revision decision is in-session only.** It is not
  written to any store, audit log, or downstream system -- refreshing the
  page discards it. This release pass makes the human-in-the-loop
  checkpoint an explicit, visible UI state; it does not add a persistence
  or workflow-routing layer around that decision.

## Application

- **No real authentication or authorization.** There is no login, no user
  accounts, and no access control of any kind -- anyone who runs the app
  sees and can use everything.
- **No audit logging, rate limiting, or monitoring.**
- **No live integration beyond the optional Claude narration call.** With
  `MOCK_MODE=false` and a valid `ANTHROPIC_API_KEY`, `src/llm.py` calls
  Claude to polish already-fixed evidence into prose. Every other part of
  the pipeline (matching, metrics, hypotheses, risks) is local deterministic
  logic -- there is no live campaign-performance data warehouse, CRM, or
  ad-platform connection.
- **No hosted deployment as of this pass.** See the main README's Maturity
  line and Deployment instructions section.

See `docs/production-path.md` for how each of these would be addressed on
the path from prototype to pilot to production.
