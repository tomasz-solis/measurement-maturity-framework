# Example Packs

These are the bundled sample packs for the Streamlit app. They are **all v2
vertical measurement packs** (`schema_version: "2.0"`) and all are fully
defined — every metric is source-controlled, tested, owned, and role-clear, so
each scores in the strong band on metric definition quality. They are fictional
and company-agnostic.

If another project needs to recreate the app's look and interaction pattern,
see the design handoff in [`streamlit_design_handoff.md`](streamlit_design_handoff.md).

## Decision-ready exemplars (what "good" looks like)

- **`onboarding_measurement_ready.yaml`** — Onboarding. A healthy,
  decision-ready system: clear primary metric, supporting + guardrail metrics,
  linked OKRs and decisions, a real operating rhythm.
- **`mobile_app_measurement.yaml`** — Mobile App. Engagement and reliability
  metrics with a crash-free guardrail on the launch decision.
- **`notifications_measurement.yaml`** — Notifications. Relevance and opt-out
  metrics wired to a rollout decision and its guardrail.
- **`support_experience_measurement.yaml`** — Support Experience. Resolution,
  response time, CSAT, and a reopen-rate guardrail linked to support decisions.

## Gap demonstrations (what the framework catches)

These have well-defined metrics too — the weakness is in the *system*, which is
the point: good metrics do not by themselves make a vertical decision-ready.

- **`collaboration_portfolio_design.yaml`** — Team Collaboration. *Portfolio
  role clarity* is weak: a metric has no role and two are orphaned (linked to no
  decision or OKR). Overall band: Usable with caution.
- **`search_decision_gap.yaml`** — Search & Discovery. *Decision coverage* is
  weak: a decision references an undefined metric and the decision model is
  thin. Overall band: Fragile.
- **`reporting_operating_gap.yaml`** — Reporting & Insights. *Operating rhythm*
  is weak: solid metrics but no review cadence. Used (with `search`) to make the
  cross-vertical "shared gaps" view meaningful.

## How to use

Run the app and load any pack:

```bash
streamlit run app.py
```

In **Review a pack**, upload a file and you get the vertical readiness scorecard,
decision map, measurement debt, strategy tree, and one-page brief. In **Compare
verticals**, the bundled packs are compared as a heatmap with a shared-gaps
summary.

Or score one directly from Python:

```python
import yaml
from mmf.vertical_scoring import score_vertical

with open("examples/onboarding_measurement_ready.yaml") as f:
    pack = yaml.safe_load(f)

score = score_vertical(pack)
print(score.overall_band, f"{score.decisions_ready}/{score.decisions_total}")
```

The v1 metric-pack path (`mmf.scoring.score_pack`) still works and powers the
metric-readiness layer inside the v2 score. See
[`docs/V2_SCHEMA.md`](../docs/V2_SCHEMA.md) for the schema and
[`templates/vertical_measurement_pack_template.yaml`](../templates/vertical_measurement_pack_template.yaml)
for a starting point.
