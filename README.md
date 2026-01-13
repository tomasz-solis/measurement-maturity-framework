# Measurement Maturity Framework — YAML Auditor

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains a small, opinionated tool for reviewing metric definitions before they are treated as decision-ready.

This framework was built to support repeated decisions, not one-off analyses.

The core idea:  
**most metric failures are structural, not analytical** — missing context, unclear ownership, unstable definitions, or hidden assumptions.

The auditor makes those issues visible early, while they are still inexpensive to fix.

---

## What this is (and what it isn’t)

**This is:**
- A structured review tool for metric definitions
- A way to surface ownership gaps, weak proxies, and missing guardrails
- A pre-flight check before metrics reach dashboards, experiments, or planning decks

**This is not:**
- An automated decision engine
- A BI framework or metrics catalog
- A replacement for human judgment

**Non-goals:**
- This is not meant to standardize metrics across teams
- This does not prevent bad decisions, only makes risk visible

**When not to use:**
- One-off exploratory analysis
- Pure research metrics with no downstream decisions

The framework is intentionally conservative. 

It rewards clarity and discipline over completeness.

---

## Core concepts

### Metric packs

Metrics are defined in YAML packs, not ad-hoc SQL files.

Each metric is expected to state:
- what it measures
- why it exists
- how it is computed (or why it isn’t yet)
- who owns it
- what depends on it

This makes the *shape* of the metric explicit before anyone argues about the number.

---

### Validation

The validator checks for predictable failure modes, such as:
- missing descriptions
- unclear ownership
- absent tests
- undefined dependencies
- early-stage proxies without guardrails

Validation is explicit and non-blocking. Issues remain visible even when scoring proceeds.

---

### Scoring

Each metric receives a score from **0–100**, representing how safe it is to use for decisions.

Scores do **not** measure business performance.  
They measure **definition maturity**.

Observed patterns in practice:
- V0 proxy metrics score lower by design
- Scores increase as ownership, tests, and stability are added
- Missing context hurts more than missing SQL

---

### Suggestions

Suggestions are deterministic and rule-based.

They explain:
- what is missing
- why it matters
- what a reasonable next step looks like

Nothing is auto-fixed. All changes remain human decisions.

---

### Strategy tree

When multiple metrics compete for attention, local optimizations become hard to see.

Metrics are rendered into a strategy tree to show:
- how product levers connect
- where metrics overlap or compete
- how local signals roll up into broader outcomes

This makes trade-offs visible instead of implicit.

---

## Optional AI helper (deliberately constrained)

The project includes an **optional AI helper** for drafting text only:
- rewriting metric descriptions
- suggesting test ideas
- clarifying validation warnings in plain language

If AI-generated content is used, the metric can be flagged with:

```yaml
ai: true
```

This lowers the score until a human review removes the flag.

AI never:
- changes scores
- alters YAML automatically
- invents sources, dependencies, or ownership

The framework must remain useful with AI fully disabled.

---

## How to read the score

Think of the score as a **decision risk signal**, not a quality grade.

It answers one question:
> *How safe is it to base decisions on this metric today?*

### Interpretation guide
- **80–100** - Decision-ready. Clear definition, ownership, and basic guardrails are in place.

- **60–79** - Usable with caution. The metric is mostly stable but still missing structure (tests, dependencies, or clarity around change).

- **40–59** - Early or fragile. Useful for exploration, risky for commitments or targets.

- **Below 40** - Not safe for decisions. Definition gaps dominate.

A low score does not mean the metric is wrong.  
It means the risk of misinterpretation is high.

---

## One-page example: metric pack walkthrough

Below is a minimal end-to-end example showing how a single metric moves from definition to decision readiness.


### Step 1: Pack metadata
```yaml
id: accounting_pilot
name: Accounting & Ecosystem Pilot
version: 0.2.0
```
Pack-level metadata anchors the scope.
Missing this makes trend tracking and governance impossible later.

### Step 2: A V0 proxy metric
```yaml
- id: support_ticket_ratio
  name: Support Ticket Ratio (V0 proxy)
  tier: V0
  description: >
    Weekly ratio of support tickets related to accounting integrations
    relative to active connected accounts.
```
At this stage:
- SQL may be missing
- the definition may still evolve

That’s acceptable — as long as it is explicit.

### Step 3: Ownership and expectations
```yaml
  responsible: CS Ops / Support
  grain: weekly
  unit: ratio
```
Ownership matters more than precision early on.
Someone must be accountable when the metric moves.

### Step 4: Guardrails (optional early)
```yaml
  tests:
    - test: freshness
    - test: range_check
```
Even basic tests reduce silent failure risk.

### Step 5: Result
The auditor will:

- validate structure
- assign a maturity score
- explain what limits decision safety
- suggest the next improvement step

The output is a clear signal:
- whether the metric is safe to use
- what is missing
- what the next concrete improvement should be

The goal is not perfection.
It is honest readiness.

---

## Why YAML

YAML is not about configuration.

It forces decisions to be written down:
- what matters
- what is assumed
- what is still unknown

If a metric cannot be described clearly in YAML, it is usually not ready to be trusted in a dashboard or planning discussion.

---

## Typical use cases
- Reviewing new metrics before shipping dashboards
- Sanity-checking experiment success metrics
- Aligning product, data, and engineering on ownership
- Making metric trade-offs explicit in planning discussions
- Teaching teams what “good enough” looks like at each stage

---

## How to run

The app runs locally via a small Streamlit UI.
 
### Requirements
- Python 3.10+

### Setup

```bash
pip install -r requirements.txt
```

### Run
```bash
streamlit run app.py
```

Then open the URL shown in the terminal and upload a metric-pack YAML (built from the template provided - also downloadable in the webapp).

---

## Project structure
```yaml
├── app.py
├── mmf/
│   ├── validator.py
│   ├── scoring.py
│   ├── suggestions.py
│   ├── mermaid.py
│   └── streamlit_mermaid.py
└── templates/
    ├── metric_pack_template.yaml
    └── metric_template.yaml
```

---

## Philosophy

This tool sits upstream of any decision process that relies on metrics.

Metrics are not neutral.

They encode assumptions, incentives, and risk.

This tool exists to surface those things early —
before they quietly shape decisions.

---

## Contact

Tomasz Solis
- [LinkedIn](https://linkedin.com/in/tomaszsolis)
- [GitHub](https://github.com/tomasz-solis)