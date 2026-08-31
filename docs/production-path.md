# Production path: prototype -> pilot -> production

Expands on the README's Roadmap section with concrete, staged detail.

## Stage 1: Prototype (this repo, current state)

- Synthetic 30-campaign corpus (`data/synthetic/past_campaigns.json`),
  covering 4 objectives, 4 markets, 6 channels, and 5 product lines.
- Deterministic TF-IDF matching + rule-based hypothesis/risk/messaging/
  audience/measurement-plan derivation (`src/engine.py`), with all 5
  evidence source types (prior brief, persona research, market insight,
  creative reference, performance benchmark) modeled per matched campaign.
- Streamlit demo (`app.py`) with a visible synthetic-data disclosure, a
  3-metric transparency panel, a coverage/uncertainty indicator, an explicit
  human-review checkpoint (Approve / Request revision), and a Reset-state
  control.
- Optional live Claude narration (`MOCK_MODE=false`), gated behind an API
  key, that only rewrites already-fixed evidence into prose.
- 31 automated tests (`pytest`) covering matching, evidence-type coverage,
  thin-evidence detection, rule derivation, and brief-quality structure.
- No persistence, no auth, no live data connections. Not deployed.

## Stage 2: Pilot

Goal: validate the approach with a real (small, non-critical) marketing
team before broadening scope.

- Connect to the real campaign-performance data source (whatever the
  marketing team already tracks -- a spreadsheet export, a BI table, or an
  ad-platform API), and replace the synthetic corpus with real, anonymized
  historical campaigns. Expand to hundreds of records rather than 30.
- Validate `SIMILARITY_THRESHOLD`, `MIN_STRONG_MATCHES`, `LOW_CTR_BASELINE`,
  and `HIGH_COST_PER_LEAD_BASELINE` against real outcomes with the
  marketing team -- these are currently illustrative defaults.
- Extend persona research, market insight, and creative reference from
  hand-written demo text to actual persona-research documents, market
  research summaries, and a real creative asset library (with links, not
  just text descriptions).
- Add lightweight persistence so a generated brief and its review decision
  (Approve / Request revision) survive a page refresh and can be revisited
  -- still single-team scale, not yet a full audit trail.
- Basic access control: a shared pilot-team login, not full RBAC yet.
- Start collecting outcome data on brief-to-campaign conversion so Stage 3's
  rollout metrics have a baseline.

## Stage 3: Production controls

Goal: make the system safe and accountable to run broadly inside the
organization.

- **Audit log** of every generated brief, its full evidence set (which
  campaigns matched, at what similarity, plus persona/market/creative
  evidence shown), and the reviewer's Approve/Request-revision decision
  with timestamp and reviewer identity.
- **Versioned rule thresholds** -- changes to `SIMILARITY_THRESHOLD` and the
  risk baselines are tracked, reviewable, and reversible, not silently
  edited in source.
- **Role-based access** so only approved brief authors can generate briefs
  and only approved reviewers can mark a brief Approved; a required
  reviewer sign-off gate before a brief can be exported or shared outside
  the tool.
- **Monitoring and rate limiting** on the live-Claude-narration path once
  it is used broadly, plus cost tracking.
- **Data governance** for the now-real campaign corpus: retention policy,
  PII scrubbing checks on any customer-facing text pulled into
  personas/insights, and a documented data-source lineage.

## Stage 4: Rollout & adoption measurement

- Track brief-to-campaign conversion rate (how many generated briefs turn
  into an actual launched campaign).
- Track time saved per brief vs. the prior manual research process.
- Track the reviewer override/revision-request rate from the human-review
  checkpoint added in this release -- a high revision-request rate signals
  the rules, corpus, or thresholds need retuning, not just anecdotal
  marketer feedback.
- Track thin-evidence rate over time as the real corpus grows -- it should
  trend down as more real campaigns accumulate in the matched segments.
