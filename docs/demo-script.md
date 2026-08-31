# Demo script (60-90 seconds)

A guided walkthrough a reader can follow verbatim, using the app's own
default widget values wherever possible.

---

**0:00 -- Orient.**
"This is the Campaign Intelligence Agent -- a marketer describes a new
campaign, and the agent retrieves similar synthetic past campaigns and
drafts an evidence-backed brief for human review." Point out the
**"Public portfolio prototype · Synthetic data"** line under the title, and
the 3-metric panel: **30 synthetic campaigns, 5 evidence source types,** and
the verified automated-test count.

**0:10 -- Fill out the request.**
In the New campaign request form, set:
- Objective: **lead generation**
- Audience: **IT directors at mid-market manufacturers**
- Market / region: **North America**
- Product / product line: **CloudSync Ops Platform**
- Channel: **LinkedIn**
- Description: *"Sponsored LinkedIn content promoting a free supply-chain
  uptime assessment to generate qualified demo requests."*

Click **Generate brief**.

**0:20 -- Coverage indicator.**
Point out the green coverage banner: most matched campaigns clear the
0.20 similarity threshold, so this is not flagged as thin evidence. Mention
that if evidence were thin, this banner turns into a yellow warning
recommending a small pilot instead of a full-budget bet.

**0:30 -- Evidence panel: all 5 source types.**
Expand the top match (`CMP-001`, similarity ~1.0). Walk through its five
labeled sub-sections in order: ① Prior campaign brief (objective, audience,
market, product, channel, description), ② Persona research, ③ Customer /
market insight, ④ Creative asset reference, ⑤ Performance benchmark (the
raw metrics JSON: CTR 2.1%, conversion 3.4%, cost per lead $88.50). Note
that everything here is "observed data" -- nothing in this panel came from
an LLM.

**0:50 -- Recommendation panel.**
Move to the right-hand panel: hypotheses (CTR/conversion benchmarks derived
from the matched campaigns' real metrics), a candidate messaging angle
("ROI / cost calculator... seen in N matched campaigns"), recommended
audiences, any risks the rules engine flagged, and the measurement plan.
Emphasize the "AI-assisted recommendation -- review before use" label --
this panel is clearly, visually separated from the Evidence panel at left.

**1:05 -- Narrative + human review.**
Scroll to the narrative paragraph (template-written in mock mode). Then
point out the **Human review** section: **✅ Approve brief** and
**✏️ Request revision** buttons. Click one and show the resulting status
message -- this is the explicit human-in-the-loop checkpoint, not just a
sentence in the README.

**1:15 -- Reset.**
Click **Reset state** and show the form and results clearing back to the
empty landing view, ready for the next request.

**1:25 -- Wrap.**
"Every number in the Recommendation panel traces back to a real metric in
the Evidence panel at left -- that traceability, plus the explicit
human-review step, is the core of what this prototype demonstrates."
