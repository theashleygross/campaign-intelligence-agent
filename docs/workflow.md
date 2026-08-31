# Workflow

Step-by-step user flow through the Streamlit app (`app.py`), matching the
actual UI exactly as implemented.

1. **Landing view.** The marketer opens the app and sees:
   - The title, the "Public portfolio prototype · Synthetic data" disclosure
     line, and a mode badge in the sidebar (`MOCK_MODE=true` or `false`).
   - A 3-metric panel: synthetic campaigns (30), evidence source types (5),
     automated tests (the verified `pytest` count).
   - A **Reset state** button.
   - The empty campaign-request form.

2. **Fill out the campaign request form.** Objective (select), audience
   (free text, required), market/region (select, populated from the
   corpus's distinct markets), product/product line (free text, required),
   channel (select), and an optional free-text description.

3. **Submit -> "Generate brief".** On submit:
   - If audience or product is blank, the form shows a validation error and
     stops (empty/validation state).
   - Otherwise `src/engine.py:build_brief()` runs the full deterministic
     pipeline (match -> derive evidence) and `src/llm.py:write_brief_narrative()`
     produces the narrative paragraph. Both results are stored in
     `st.session_state` so they persist across the reruns triggered by the
     review buttons in step 6.

4. **Coverage indicator.** Immediately below the form, a colored banner
   states how many of the top matches are "strong" (at/above the 0.20
   similarity threshold) vs. total matches, and shows a warning when
   `thin_evidence` is `True` (fewer than 2 strong matches) -- the
   coverage/uncertainty signal a human reviewer should weigh before trusting
   the brief.

5. **Two side-by-side panels:**
   - **Evidence** (left, "Observed data"): one expander per matched
     campaign, showing all 5 evidence source types in labeled sub-sections:
     ① Prior campaign brief, ② Persona research, ③ Customer/market insight,
     ④ Creative asset reference, ⑤ Performance benchmark (raw JSON metrics).
   - **Recommendation** (right, "AI-assisted recommendation -- review before
     use"): hypotheses, messaging angles, recommended audiences, risks, and
     measurement plan, each with its own empty-state message if the rules
     engine produced nothing for that section.

6. **Narrative brief.** A single paragraph (template-written in mock mode,
   Claude-written in live mode) synthesizing the evidence and
   recommendations above it -- never introducing new facts beyond what the
   two panels already show.

7. **Human review checkpoint.** Below the narrative, two buttons:
   **✅ Approve brief** and **✏️ Request revision**. Clicking either records
   an in-session-only decision (`st.session_state["review_status"]`, no
   persistence) and displays a corresponding status message. This makes the
   human-in-the-loop checkpoint an explicit UI state rather than something
   only described in prose.

8. **Reset state.** Clicking **Reset state** (available at any point) clears
   the form fields, the generated brief, the narrative, and the review
   decision, returning the app to the landing view.

## Empty / loading / validation / success / error states present in the UI

| State | Where |
|---|---|
| Empty | Landing view before first submission ("Fill out the form above...") |
| Validation | Missing audience or product -> `st.error(...)`, form does not proceed |
| Loading | Streamlit's native spinner while `build_brief()` / `write_brief_narrative()` run (sub-second in mock mode) |
| Success | Coverage banner in green when evidence is not thin; review-approved banner |
| Warning / thin coverage | Coverage banner in yellow when `thin_evidence` is `True` |
| Error | Form validation error (see Validation above); no other error paths exist in mock mode since there is no network call |
