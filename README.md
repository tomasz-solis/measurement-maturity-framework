# Measurement Maturity Framework

A Streamlit app and Python library that checks whether metric definitions are ready to drive decisions.

Live app: [metricready.streamlit.app](https://metricready.streamlit.app/)

It does three things:

1. Validates the structure of a metric pack.
2. Scores metric maturity and pack-level decision risk.
3. Suggests the next improvement step, deterministically.

Most metric problems are structural before they are analytical. A team debating DAU methodology is often missing something more basic: nobody owns the metric, the SQL isn't written down, and the first time anyone notices the number is wrong is in a board deck. This tool finds those gaps while they are cheap to fix. It doesn't generate metrics, choose KPIs or validate business logic.

## Version 2: vertical measurement readiness (in progress)

v1 asks whether one metric is structurally ready. v2 asks whether a product area can use its measurement system to make reliable recurring decisions.

A v2 vertical measurement pack models one product area as a graph: metrics, the decisions they feed, the OKRs they ladder to, the guardrails that protect them, the instrumentation they depend on, and the owners and review rhythm that keep them alive. The headline result is how many of the area's key decisions are backed by trusted, owned, instrumented, guardrailed metrics, reported as a band and not a falsely precise number.

MetricReady doesn't judge whether a team has too many or too few metrics. Metric count is never a scoring input. Problems are counted instead: orphaned metrics, missing roles, decisions with no metric.

The public repo is company-agnostic (engine and sample packs). A private deployment maps real OKRs, KPIs and metric definitions into the same schema, using local packs that never enter a public repo.

Three sample packs. All have well-defined metrics, but only one is decision-ready:

| Pack | What it shows |
|---|---|
| [onboarding_measurement_ready.yaml](examples/onboarding_measurement_ready.yaml) | A healthy, decision-ready system |
| [collaboration_portfolio_design.yaml](examples/collaboration_portfolio_design.yaml) | Good metrics, unclear roles and links |
| [search_decision_gap.yaml](examples/search_decision_gap.yaml) | Good metrics, weak decision model |

Docs: [PRD](docs/PRD_v2_product_measurement_readiness.md) · [V2 schema](docs/V2_SCHEMA.md) · [V2 scoring methodology](docs/V2_SCORING_METHODOLOGY.md). v1 packs still validate and score as before.

## Evidence

Three side studies check whether the framework holds up beyond the unit tests.

Bayesian weight sensitivity ([`analysis/bayesian_robustness.ipynb`](analysis/bayesian_robustness.ipynb)). The deduction weights in `mmf/config.py` are set by hand, not estimated. The notebook perturbs them within a plausible range and checks whether pack rankings move. Across 27 synthetic packs, the Spearman correlation between rule-based scores and Bayesian posterior means is 0.9992, and the largest score gap is 0.43 points. The ranking barely moves.

Weight calibration ([`analysis/weight_calibration.ipynb`](analysis/weight_calibration.ipynb)). The same 27 packs were ranked twice by me and once by an independent model rater, and a ridge regression fit weights to the average ranking. The default weights correlate with that consensus at 0.95; fitted weights reach 0.99. The direction is the useful part: `missing_sql` probably deserves more weight, `missing_owner` slightly more, `tier_v0` slightly less. The study is small, so the new magnitudes haven't shipped as defaults.

Retrospective case studies ([`case_studies/`](case_studies/README.md)). Three public metric failures rebuilt as YAML packs and scored: Netflix's 2019 "view" redefinition, Facebook's 2014 to 2016 video watch-time inflation, and Uber's MAPC at IPO. Most are misses, and that's the point: MMF audits structural gaps, not every logic bug or executive framing choice. The case studies led to the `missing_sql_temporary` vs `missing_sql_structural` split.

All three are reproducible. The notebooks rebuild with `python analysis/build_notebook.py` and `python analysis/build_calibration_notebook.py`, and each case study runs from its own YAML through `score_pack()`.

## Quick start

```bash
pip install -r requirements.txt        # runtime, pinned
pip install -r requirements-dev.txt    # formatters, linters, tests
streamlit run app.py
```

In the app:

1. Pick **Review a pack** and upload `examples/onboarding_measurement_ready.yaml` (a v2 vertical pack), or download an example from the sidebar, or start from `templates/`.
2. Review the vertical readiness, decision map, measurement debt, strategy tree and brief.
3. Or pick **Compare verticals** for the heatmap across the bundled packs.

## Scope

| It is | It isn't |
|---|---|
| A review layer for YAML metric definitions | A BI framework |
| A quick way to find ownership, reproducibility and guardrail gaps | A metrics catalog |
| A decision-risk check before metrics reach dashboards, planning or targets | A replacement for judgment, or a system that auto-fixes or auto-approves metrics |

## Pack shape

A top-level YAML mapping with a `metrics` list and optional pack metadata.

```yaml
pack:
  id: product_pilot
  name: Product Pilot Metrics
  version: 0.1.0
  schema_version: "1.0"

strategy_board:
  title: TEAM SUCCESS
  success_node_id: team_success
  company_goals_box:
    title: Company Goals
    goals:
      - id: revenue_growth
  levers: []

impact_graph:
  nodes:
    - id: revenue_growth
      type: goal
      label: Revenue Growth
  edges:
    - from: team_success
      to: revenue_growth

metrics:
  - id: feature_activation_rate
    name: Feature Activation Rate
    description: Percentage of accounts that finish setup within 14 days.
    tier: V1
    status: active
    accountable: Growth Team
    unit: percent
    grain: account_week
    requires:
      - warehouse.product.setup_events
    sql:
      numerator: |
        SELECT COUNT(DISTINCT account_id) FROM warehouse.product.setup_events
      denominator: |
        SELECT COUNT(DISTINCT account_id) FROM warehouse.product.accounts
    tests:
      - type: not_null
      - type: range
        field: value
        min: 0
        max: 100
```

`strategy_board` and `impact_graph` are optional and only feed the strategy diagram.

## What the validator checks

Validation never blocks. Structural errors mark a pack as not clean, but scoring still runs so you can inspect the rest.

| Check | Result |
|---|---|
| Top-level YAML is not a mapping | Error |
| `metrics` missing or not a list | Error |
| Metric `id` missing or duplicated | Error |
| Metric `name` missing | Error |
| `accountable` or `responsible` missing | Warning |
| SQL missing | Warning |
| Tests missing | Warning |
| Unknown `schema_version` | Warning |
| `requires` missing | Info |
| `pack.schema_version` missing | Info |
| SQL syntax error (checked only if `sqlparse` is installed) | Warning |

It doesn't enforce `description`, `grain` or `unit`, run SQL, or check warehouse objects.

## How scoring works

Scores measure how mature a definition is, not business performance.

### Metric score

Every metric starts at `100` and loses points for specific gaps:

| Check | Deduction |
|---|---:|
| `tier: V0` | -10 |
| missing `accountable` / `responsible` | -5 |
| missing SQL (default) | -5 |
| missing SQL with `implementation_type: v0_proxy` | -3 |
| missing SQL with `implementation_type: spreadsheet`/`notebook`/`dashboard`/`other` | -12 |
| missing tests | -5 |
| missing `description` | -3 |
| missing `grain` | -2 |
| missing `unit` | -2 |

Only one of the three missing-SQL rows fires, chosen by the optional `implementation_type` field. "SQL is coming for this V0 proxy" and "this metric lives in a spreadsheet" are different problems that look the same on the surface. [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md) has the reasoning.

The score is clamped to `0-100`.

### Pack score

```text
pack_score = (1 - pack_floor_weight) * average_metric_score
           + pack_floor_weight * min_metric_score
```

The default `pack_floor_weight` is `0.3`, so the weakest metric still pulls the pack down.

### Reading the score

| Range | Meaning |
|---|---|
| `80-100` | Decision-ready |
| `60-79` | Usable with caution |
| `40-59` | Early or fragile |
| `0-39` | Not safe for decisions |

Conservative on purpose. A polished chart isn't a reliable metric.

## Suggestions

Suggestions are deterministic: no hidden prompts, no silent edits. They combine positive signals (clear naming, strong maturity), actions for each gap (add an owner, SQL or tests) and some tier-aware prioritisation.

The scorer emits gaps for V0 tier, missing owner, missing SQL, missing tests, missing description, missing grain and missing unit. The suggestion layer can handle more gap types if future rules add them, but those aren't part of the scoring contract today.

## Strategy tree

If a pack has `strategy_board` and `impact_graph`, the app draws a Mermaid strategy tree showing which KPI anchors each pillar, which levers connect to the team success node, and how success rolls up to company goals. Packs without it still validate, score and get suggestions.

## Files

| File | Role |
|---|---|
| [app.py](app.py) | Streamlit app |
| [mmf/validator.py](mmf/validator.py) | Validation |
| [mmf/scoring.py](mmf/scoring.py) | Metric and pack scoring |
| [mmf/suggestions.py](mmf/suggestions.py) | Suggestions |
| [mmf/mermaid.py](mmf/mermaid.py) | Strategy diagram |

Docs: [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md), [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md), [examples/README.md](examples/README.md).

Templates: [vertical_measurement_pack_template.yaml](templates/vertical_measurement_pack_template.yaml), [metric_template.yaml](templates/metric_template.yaml), [metric_pack_template.yaml](templates/metric_pack_template.yaml).

## Part of the Product Decision Lab

One of three headline projects in my [Product Decision Lab](https://github.com/tomasz-solis/product-decision-lab): tools for product teams deciding with incomplete evidence.

Tomasz Solis · [LinkedIn](https://www.linkedin.com/in/tomaszsolis) · [GitHub](https://github.com/tomasz-solis)
