# Evaluation plan

What "correct" means for this agent, and how the automated test suite
(`tests/test_engine.py`) checks it.

**Verified test count: 31/31 passed** (`pytest -v`, run at release time).
This document is the "how" behind that number -- README.md's Test and
evaluation approach section links here and states the count; this file
explains what each group of tests is actually checking.

## 1. Corpus / schema integrity

*Correctness claim:* the seeded data meets the release's exact scale and
evidence-type requirements, and nothing was silently dropped when the
corpus was expanded.

- `test_corpus_has_exactly_thirty_campaigns` -- literal `len()` check against
  the 30-record requirement.
- `test_corpus_campaign_ids_are_unique` -- no duplicate IDs after expansion.
- `test_original_fifteen_campaigns_are_preserved` -- `CMP-001`-`CMP-015` still
  exist unchanged (other tests and the demo narrative depend on them).
- `test_evidence_source_types_constant_lists_exactly_five_types` -- the
  engine's `EVIDENCE_SOURCE_TYPES` constant literally lists the 5 required
  types, in the exact wording used in the UI.
- `test_every_corpus_record_carries_all_five_evidence_source_fields` -- every
  one of the 30 seeded records has non-empty data for all 5 evidence types,
  not just the original 2 (prior brief + benchmark).
- `test_matched_campaign_object_carries_all_five_evidence_types` -- the
  engine's output object (`MatchedCampaign`), not just the raw JSON, exposes
  all 5 types, which is what the UI actually renders from.

## 2. Matching quality across the expanded 30-campaign corpus

*Correctness claim:* TF-IDF cosine similarity retrieval still works
correctly at 2x corpus scale, including for the newly added
objectives/markets/channels/product line.

- `test_close_match_returns_expected_top_campaign_with_high_similarity` /
  `test_matched_campaigns_carry_real_metrics_from_corpus` -- pre-existing
  checks, re-verified against the 30-record corpus.
- `test_unrelated_request_returns_low_similarity_and_thin_evidence_flag` --
  a request with zero vocabulary overlap scores low across the board.
- `test_matching_finds_new_product_line_campaign` (FleetPulse),
  `test_matching_finds_new_customer_retention_objective_campaign`,
  `test_matching_finds_new_market_latin_america_campaign`,
  `test_matching_finds_new_paid_search_channel_campaign`,
  `test_matching_finds_new_social_channel_campaign` -- each of the newly
  added corpus dimensions (product line, objective, market, and two
  channels) is independently retrievable as a top match by a matching
  request, proving the added records were seeded correctly and are not
  dead weight.
- `test_top_n_matches_respects_expanded_corpus_without_duplicates` -- ranking
  invariants (correct count, no duplicate IDs, descending score order) hold
  at the larger corpus size.

## 3. Thin-evidence detection

*Correctness claim:* the coverage/uncertainty signal fires exactly at the
documented threshold, in both directions.

- `test_thin_evidence_true_when_only_one_strong_match` / `..._false_when_two_strong_matches_meet_minimum`
  -- boundary test at `MIN_STRONG_MATCHES = 2` using a hand-built 1-record vs.
  2-record corpus, isolated from the real data so the boundary is exact.
- `test_empty_corpus_yields_no_matches_and_thin_evidence` -- the degenerate
  empty-corpus case doesn't crash and correctly reports thin evidence.

## 4. Hypothesis / risk derivation rules

*Correctness claim:* every hypothesis and risk statement is a deterministic,
traceable function of the matched campaigns' real metrics -- never an
invented number, and never present when the underlying condition isn't met.

- `test_hypotheses_and_risks_non_empty_when_matches_exist` /
  `test_hypotheses_are_empty_without_any_strong_match` -- hypotheses appear
  if and only if there is at least one strong match.
- `test_risk_flags_low_ctr_creative_fatigue`,
  `test_risk_flags_high_cost_per_lead_budget_efficiency`,
  `test_risk_flags_market_mismatch_when_all_matches_are_other_markets` --
  each of the three metric-driven risk rules is exercised with a hand-built
  corpus engineered to cross (or not cross) that rule's exact baseline
  constant, confirming the rule fires on real, traceable input rather than
  being coincidentally triggered by the demo corpus.

## 5. Messaging angle and recommended-audience derivation

*Correctness claim:* a messaging angle is only surfaced when it is
genuinely repeated across matched campaigns (the "2+ distinct campaigns"
rule), not on a single coincidental keyword hit.

- `test_messaging_angle_requires_two_distinct_matching_campaigns` -- a
  keyword present in only one matched campaign does not qualify.
- `test_messaging_angle_surfaces_when_two_matches_share_it` -- the same
  keyword across two matched campaigns does qualify, with the correct
  count in the surfaced phrase.
- `test_recommended_audiences_derived_from_strong_matches_only` -- audiences
  are non-empty and correctly capped at 3.

## 6. Measurement plan branching

*Correctness claim:* the measurement plan's first recommendation actually
changes based on the requested objective (lead gen vs. awareness vs.
launch), rather than being a static list.

- `test_measurement_plan_branches_by_objective_keyword` -- checks the
  objective-specific first line for 3 objectives, plus the always-present
  channel-fatigue monitoring step.

## 7. Brief-quality checks (all required sections present)

*Correctness claim:* the full `CampaignBrief` structure -- the shape a human
reviewer sees -- is well-formed both when evidence is strong and when it is
thin, with every field either populated or a well-defined empty list (never
missing or `None`).

- `test_brief_has_all_required_sections_present_for_well_matched_request` --
  every section of a strong-evidence brief is present and non-empty where
  the rules guarantee non-emptiness.
- `test_brief_quality_holds_for_thin_evidence_request_too` -- a thin-evidence
  brief still has a defined measurement plan (pilot-first) and a
  thin-evidence risk statement; it degrades gracefully rather than
  returning an incomplete structure.

## 8. Narrative (mock LLM) output

*Correctness claim:* the deterministic mock narrative (the default,
zero-API-key path) actually reflects the evidence it was built from.

- `test_mock_narrative_flags_thin_evidence_in_prose` -- thin evidence is
  called out in the narrative text itself.
- `test_mock_narrative_mentions_matched_campaign_count_and_objective` -- the
  narrative's stated match count and objective match the brief's actual
  values, not hardcoded placeholder text.

## What is explicitly out of scope for this test suite

- The live Claude narration path (`src/llm.py:_live_narrative`) is not unit
  tested here -- it requires a real `ANTHROPIC_API_KEY` and a network call,
  which this prototype's test suite does not perform (see
  `docs/limitations.md`). Its prompt construction is reviewed by inspection.
- Streamlit UI rendering itself (`app.py`) is not unit tested; it is
  verified by booting the app and confirming HTTP 200, plus manual
  inspection of each state during the release pass.
