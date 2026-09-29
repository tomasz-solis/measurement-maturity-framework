# Example packs

The sample packs bundled with the app. All are v2 vertical measurement packs (`schema_version: "2.0"`), fictional and company-agnostic. Every metric is source-controlled, tested, owned and has a clear role, so each pack scores in the strong band on metric quality.

To recreate the app's look and interaction pattern in another project, see [`streamlit_design_handoff.md`](streamlit_design_handoff.md).

## Decision-ready packs (what good looks like)

| Pack | Area | What it shows |
|---|---|---|
| `onboarding_measurement_ready.yaml` | Onboarding | A healthy system: clear primary metric, supporting and guardrail metrics, linked OKRs and decisions, a real review rhythm |
| `mobile_app_measurement.yaml` | Mobile App | Engagement and reliability metrics, with a crash-free guardrail on the launch decision |
| `notifications_measurement.yaml` | Notifications | Relevance and opt-out metrics tied to a rollout decision and its guardrail |
| `support_experience_measurement.yaml` | Support Experience | Resolution, response time, CSAT and a reopen-rate guardrail tied to support decisions |

## Gap packs (what the framework catches)

These have well-defined metrics too. The weakness is in the system around them, which is the point: good metrics alone don't make an area decision-ready.

| Pack | Area | Weak dimension | Overall band |
|---|---|---|---|
| `collaboration_portfolio_design.yaml` | Team Collaboration | Portfolio role clarity: one metric has no role and two are orphaned (linked to no decision or OKR) | Usable with caution |
| `search_decision_gap.yaml` | Search & Discovery | Decision coverage: a decision points to an undefined metric and the decision model is thin | Fragile |
| `reporting_operating_gap.yaml` | Reporting & Insights | Operating rhythm: solid metrics, no review cadence. Used with `search` to make the cross-vertical shared-gaps view meaningful | |

## How to use them

```bash
streamlit run app.py
```

In **Review a pack**, upload a file to get the readiness scorecard, decision map, measurement debt, strategy tree and one-page brief. In **Compare verticals**, the bundled packs appear as a heatmap with a shared-gaps summary.

Or score one from Python:

```python
import yaml
from mmf.vertical_scoring import score_vertical

with open("examples/onboarding_measurement_ready.yaml") as f:
    pack = yaml.safe_load(f)

score = score_vertical(pack)
print(score.overall_band, f"{score.decisions_ready}/{score.decisions_total}")
```

The v1 path (`mmf.scoring.score_pack`) still works and powers the metric-readiness layer inside the v2 score. The schema is in [`docs/V2_SCHEMA.md`](../docs/V2_SCHEMA.md), and [`templates/vertical_measurement_pack_template.yaml`](../templates/vertical_measurement_pack_template.yaml) is a starting point.
