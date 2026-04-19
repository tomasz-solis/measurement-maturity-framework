# Measurement Maturity Framework

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The Measurement Maturity Framework is a small Streamlit app and Python library for reviewing metric definitions before they are treated as decision-ready.

It does three things:
- validates the structure of a metric pack
- scores metric maturity and pack-level decision risk
- generates deterministic suggestions for the next improvement step

The point is simple: many metric problems are structural before they are analytical. If ownership is unclear, SQL is missing, or basic tests do not exist, the number can still look precise while being risky to use.

---

## Why This Exists

Most metric problems are structural before they are analytical. A team debating DAU methodology is often missing something more basic: nobody owns the metric, the SQL isn't written down anywhere, and the first time anyone notices the number is wrong is when it surfaces in a board deck.

This tool surfaces those gaps early, while they are still cheap to fix. It does not generate metrics, choose KPIs, or validate business logic. It checks whether a metric definition has the structural properties that make it safe to rely on.

---

## Evidence

Three side studies check whether the framework holds up beyond the unit tests.

**Bayesian robustness analysis** ([`analysis/bayesian_robustness.ipynb`](analysis/bayesian_robustness.ipynb)). The deduction weights in `mmf/config.py` are hand-set, not estimated from data. The notebook perturbs those weights within a plausible range and checks whether the pack scores move much. Across 27 synthetic packs spanning the realistic quality space, the Spearman rank correlation between rule-based scores and Bayesian posterior means is 0.9992, with maximum absolute score divergence of 0.43 points. In practice, the ranking barely moves under reasonable weight uncertainty.

**Weight calibration attempt** ([`analysis/weight_calibration.ipynb`](analysis/weight_calibration.ipynb)). The project author ranked the same 27 synthetic packs twice, a few minutes apart, and got test-retest reliability of 0.97. Claude ranked the same packs independently. A ridge regression then fit weights to match the average ranking. MMF's default weights agree with that small consensus at 0.95; fitted weights reach 0.99. The main signal is that `missing_sql` likely deserves more weight, `missing_owner` a bit more, and `tier_v0` a bit less. Because the study is still small and methodologically narrow, the magnitude changes have not shipped as defaults.

**Retrospective case studies** ([`case_studies/`](case_studies/README.md)). Three public metric failures (Netflix's 2019 "view" redefinition, Facebook's 2014-2016 video watch time inflation, and Uber's MAPC at IPO) are reconstructed as YAML packs and scored. Most of them are misses, and that is useful. They show the boundary of the framework: MMF audits structural gaps, not logic bugs or executive framing choices. The case-study work also helped motivate the current `missing_sql` split between `missing_sql_temporary` and `missing_sql_structural`.

All three pieces are reproducible: the notebooks regenerate via `python analysis/build_notebook.py` and `python analysis/build_calibration_notebook.py`, and each case study runs from its own YAML through the standard `score_pack()` path.

---

## Try The UI

> **Tip:** If you want a shareable link, this app is simple to deploy on [Streamlit Cloud](https://streamlit.io/cloud).

If you want a quick feel for the app:
- run `streamlit run app.py`
- upload `examples/generic_product_metric_pack.yaml`
- review the validation, scoring, suggestions, and strategy tree sections

---

## What It Is

- A review layer for YAML metric definitions
- A lightweight way to surface ownership, reproducibility, and guardrail gaps
- A decision-risk check before metrics reach dashboards, planning, or targets

## What It Is Not

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

Scores measure **definition maturity**, not business performance.

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
- [examples/generic_product_metric_pack.yaml](examples/generic_product_metric_pack.yaml)
- [templates/metric_template.yaml](templates/metric_template.yaml)
- [templates/metric_pack_template.yaml](templates/metric_pack_template.yaml)

---

## Philosophy

Metrics are never just numbers. They carry assumptions, ownership, and failure modes.

This repo exists to make those things visible early, while the cost of fixing them is still low.

## Contact

Tomasz Solis
- [LinkedIn](https://linkedin.com/in/tomaszsolis)
- [GitHub](https://github.com/tomasz-solis)
