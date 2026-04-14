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
| missing SQL | -5 |
| missing tests | -5 |

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
pip install -r requirements.txt
```

### 2. Run the app

```bash
streamlit run app.py
```

### 3. Open a pack

- Download the generic example pack from the sidebar
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
- [docs/README.md](docs/README.md)
- [docs/SCORING_METHODOLOGY.md](docs/SCORING_METHODOLOGY.md)
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
