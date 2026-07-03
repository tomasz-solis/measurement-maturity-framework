# Measurement Maturity Framework

The Measurement Maturity Framework is a small Streamlit app and Python library for
reviewing metric definitions before they are treated as decision-ready.

It does three things:
- validates the structure of a metric pack
- scores metric maturity and pack-level decision risk
- generates deterministic suggestions for the next improvement step

The point is simple: many metric problems are structural before they are analytical. If ownership is unclear, SQL is missing, or basic tests do not exist, the number can still look precise while being risky to use.

---

## Purpose

Most metric problems are structural before they are analytical. A team debating DAU methodology is often missing something more basic: nobody owns the metric, the SQL isn't written down anywhere, and the first time anyone notices the number is wrong is when it surfaces in a board deck.

This tool surfaces those gaps early, while they are still cheap to fix. It does not generate metrics, choose KPIs, or validate business logic. It checks whether a metric definition has the structural properties that make it safe to rely on.

---

## Version 2: Vertical Measurement Readiness (in progress)

v1 answers *is this individual metric structurally ready?* v2 adds a larger
question: *can this product area use its measurement system to make reliable
recurring decisions?*

A v2 **vertical measurement pack** models one product area as a measurement
graph — metrics, the decisions they feed, the OKRs they ladder to, the
guardrails that protect them, the instrumentation they depend on, and the
ownership and review rhythm that keep them alive. The headline result is
decision-centric: *how many of the vertical's key decisions are backed by
trusted, owned, instrumented, guardrailed metrics*, reported as a band rather
than a falsely-precise number.

> MetricReady does not judge whether a team has too many or too few metrics. It
> assesses whether the metric portfolio is structured well enough to support
> recurring product decisions.

Metric count is never a scoring input. Operating concerns are expressed as
*counts of problems* — orphaned metrics, missing roles, decisions with no
metric — never counts of metrics.

The framework is **dual-use**: this public repo is fully company-agnostic
(engine plus sample packs); a private deployment maps real OKRs, KPIs, and
metric definitions into the same schema using local packs that never enter a
public repo.

Three sample packs show the core idea — all three have well-defined metrics, but
only one is decision-ready:

- [examples/onboarding_measurement_ready.yaml](examples/onboarding_measurement_ready.yaml) — a healthy, decision-ready system
- [examples/collaboration_portfolio_design.yaml](examples/collaboration_portfolio_design.yaml) — good metrics, unclear roles and linkage
- [examples/search_decision_gap.yaml](examples/search_decision_gap.yaml) — good metrics, weak decision model

Docs: [PRD](docs/PRD_v2_product_measurement_readiness.md) · [V2 schema](docs/V2_SCHEMA.md) · [V2 scoring methodology](docs/V2_SCORING_METHODOLOGY.md). v1 metric packs continue to validate and score unchanged.

---

## Evidence

Three side studies check whether the framework holds up beyond the unit tests.

Bayesian weight sensitivity ([`analysis/bayesian_robustness.ipynb`](analysis/bayesian_robustness.ipynb)). The deduction weights in `mmf/config.py` are hand-set, not estimated from data. The notebook perturbs those weights within a plausible range and checks whether the pack rankings move. Across 27 synthetic packs, the Spearman rank correlation between rule-based scores and Bayesian posterior means is 0.9992, with maximum absolute score divergence of 0.43 points. The rank order barely moves under reasonable weight uncertainty.

Weight calibration attempt ([`analysis/weight_calibration.ipynb`](analysis/weight_calibration.ipynb)). The same 27 synthetic packs were ranked twice by the project author and once by an independent model rater. A ridge regression then fit weights to match the average ranking. MMF's default weights correlate with that small consensus at 0.95; fitted weights reach 0.99. The useful signal is directional: `missing_sql` likely deserves more weight, `missing_owner` a bit more, and `tier_v0` a bit less. Because the study is small and methodologically narrow, those magnitude changes have not shipped as defaults.

Retrospective case studies ([`case_studies/`](case_studies/README.md)). Three public metric failures are reconstructed as YAML packs and scored: Netflix's 2019 "view" redefinition, Facebook's 2014-2016 video watch-time inflation, and Uber's MAPC at IPO. Most of them are misses, and that is the point. MMF audits structural gaps; it does not catch every logic bug or executive framing issue. The case studies helped motivate the current `missing_sql_temporary` vs `missing_sql_structural` split.

All three pieces are reproducible: the notebooks regenerate via `python analysis/build_notebook.py` and `python analysis/build_calibration_notebook.py`, and each case study runs from its own YAML through the standard `score_pack()` path.

---

## Running The UI

- run `streamlit run app.py`
- pick **Review a pack** and upload `examples/onboarding_measurement_ready.yaml` (a v2 vertical pack)
- review the vertical readiness, decision map, measurement debt, strategy tree, and brief sections
- or pick **Compare verticals** to see the cross-vertical heatmap across the bundled packs

---

## Boundaries

What it is:

- A review layer for YAML metric definitions
- A lightweight way to surface ownership, reproducibility, and guardrail gaps
- A decision-risk check before metrics reach dashboards, planning, or targets

What it is not:

- A BI framework
- A metrics catalog
- A replacement for judgment
- A system that auto-fixes or auto-approves metrics

---

## Pack Shape

The app expects a top-level YAML mapping with a `metrics` list and optional pack metadata.

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

`strategy_board` and `impact_graph` are optional. They are only used for the strategy visualization.

---

## What The Validator Checks

Validation is explicit and non-blocking. Structural errors stop a pack from being considered clean, but scoring still runs so you can inspect the rest of the pack.

Current checks:
- top-level YAML must be a mapping
- `metrics` must exist and be a list
- every metric needs a unique `id`
- every metric needs a `name`
- missing `accountable` or `responsible` produces a warning
- missing SQL produces a warning
- missing tests produces a warning
- missing `requires` produces an info message
- missing `pack.schema_version` produces an info message
- unknown `schema_version` produces a warning
- if `sqlparse` is installed, defined SQL gets a lightweight syntax check

What validation does not do today:
- it does not enforce `description`, `grain`, or `unit`
- it does not execute SQL
- it does not check warehouse objects or schemas

---

## How Scoring Works

Scores measure definition maturity, not business performance.

### Metric score

Every metric starts at `100`, then loses points for specific structural gaps:

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

The three `missing SQL` rows are mutually exclusive. A metric with missing SQL fires exactly one of them, selected by the optional `implementation_type` field. The split exists because "SQL will come soon for this V0 proxy" and "this metric is implemented in a spreadsheet" are different problems that happen to look the same at the surface. See [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md) for the full rationale.

The score is clamped to `0-100`.

### Pack score

The pack score is a composite:

```text
pack_score = (1 - pack_floor_weight) * average_metric_score
           + pack_floor_weight * min_metric_score
```

Default `pack_floor_weight` is `0.3`, so the weakest metric still pulls the pack down.

### Score interpretation

| Range | Meaning |
|---|---|
| `80-100` | Decision-ready |
| `60-79` | Usable with caution |
| `40-59` | Early/fragile |
| `0-39` | Not safe for decisions |

This is conservative on purpose. A polished chart is not the same thing as a reliable metric.

---

## Suggestions

Suggestions are deterministic. Nothing is generated from hidden prompts or silent edits.

They combine:
- positive signals, like clear naming or strong maturity
- gap-based actions, like adding ownership, SQL, or tests
- a small amount of tier-aware prioritization

The current scorer emits gaps for:
- V0 tier
- missing ownership
- missing SQL
- missing tests
- missing description
- missing grain
- missing unit

The suggestion layer can also handle richer gap types if future scoring rules add them, but those are not part of the current scoring contract.

---

## Strategy Tree

If a pack includes `strategy_board` and `impact_graph`, the app renders a Mermaid strategy tree. This gives you a simple way to see:
- which KPI anchors each pillar
- which levers connect to the team success node
- how success rolls up into company goals

The visualization is optional. Packs without strategy metadata still validate, score, and generate suggestions.

---

## Quick Start

### 1. Install dependencies

```bash
# Runtime (pinned for reproducibility)
pip install -r requirements.txt

# Dev tools (formatters, linters, test runner)
pip install -r requirements-dev.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

### 3. Open a pack

- Download one of the example packs from the sidebar
- Or use the templates in `templates/`
- Or upload your own YAML

### 4. Review the output

- `Validation`: structural issues and metadata gaps
- `Scoring`: pack score, weakest metric, and metric-level scores
- `Suggestions`: deterministic next steps per metric
- `Strategy Tree`: optional Mermaid visualization

---

## Files Worth Knowing

- [app.py](app.py): Streamlit app
- [mmf/validator.py](mmf/validator.py): validation logic
- [mmf/scoring.py](mmf/scoring.py): metric and pack scoring
- [mmf/suggestions.py](mmf/suggestions.py): deterministic suggestions
- [mmf/mermaid.py](mmf/mermaid.py): strategy diagram generation

Documentation:
- [SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md)
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
- [examples/README.md](examples/README.md)

Working assets:
- [examples/onboarding_measurement_ready.yaml](examples/onboarding_measurement_ready.yaml)
- [templates/vertical_measurement_pack_template.yaml](templates/vertical_measurement_pack_template.yaml)
- [templates/metric_template.yaml](templates/metric_template.yaml)
- [templates/metric_pack_template.yaml](templates/metric_pack_template.yaml)

---

## Operating View

Metrics are never just numbers. They carry assumptions, ownership, and failure modes.

This repo exists to make those things visible early, while the cost of fixing them is still low.

## Part of the Product Decision Lab

The Measurement Maturity Framework is one of three headline projects in my
[Product Decision Lab](https://github.com/tomasz-solis/product-decision-lab) —
measurement readiness, experimentation, and decision analysis for product teams deciding
under uncertainty.

Tomasz Solis — [LinkedIn](https://www.linkedin.com/in/tomaszsolis) · [GitHub](https://github.com/tomasz-solis)
