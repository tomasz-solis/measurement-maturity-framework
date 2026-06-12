# V2 Scoring Methodology — Vertical Measurement Readiness

Status: Draft
Companion: [V2_SCHEMA.md](V2_SCHEMA.md), [PRD](PRD_v2_product_measurement_readiness.md), [SCORING_METHODOLOGY.md](../SCORING_METHODOLOGY.md) (v1)

This document specifies the v2 scoring logic precisely enough that the result is reproducible by hand. As in v1, **if this doc and the code disagree, the code is the source of truth.**

---

## Scope and what it does *not* claim

v2 reasons over a measurement graph (metrics ↔ decisions ↔ OKRs ↔ guardrails ↔ instrumentation) and reports how ready a vertical's measurement system is to support recurring decisions.

It measures whether a measurement system is **documented and structured** to support decisions — not whether decisions are actually made that way (PRD P4). Wherever evidence fields exist (`decision_log_exists`, `last_reviewed`), they are weighted above self-declared links. The product never claims to observe behavior from a static pack.

**Count is never an input** (PRD P1). No rule in this document reads the number of OKRs, KPIs, or metrics. Operating concerns are expressed as *counts of problems* (orphans, missing roles, unlinked decisions).

---

## Two layers

| Layer | Question | Output |
|---|---|---|
| **L1 — Metric readiness** | Is this individual metric structurally ready? | per-metric 0–100 (unchanged from v1) |
| **L2 — Vertical readiness** | Can this vertical support recurring decisions? | decision-ready fraction + 8 dimension bands + overall band |

### Layer 1 (unchanged)

Exactly the v1 model: each metric starts at 100 and loses points for structural gaps (tier V0, missing owner/SQL/tests/description/grain/unit), blended into a pack score via `pack_floor_weight`. See the v1 [SCORING_METHODOLOGY.md](../SCORING_METHODOLOGY.md). v2 metrics are scored by the same code path.

---

## Layer 2 — Vertical readiness

Built **bottom-up from decisions**, not as a weighted average of dimensions.

### Step 1 — Decision readiness

A metric is **trusted** for decision-gating if its L1 score ≥ **80** (the v1 "decision-ready" cutoff — a deliberately higher bar than the 60 "usable" cutoff; resolves PRD open Q3).

A decision is **risk-bearing** if `decision_type ∈ {rollout, launch, ranking_change, pricing_change, default_change, deprecation}`. Others (`prioritization`, `investment`, `monitoring`, …) are not risk-bearing and do not require a guardrail.

For each decision `d`, evaluate in order:

```
missing_ref     = any id in d.required_metrics ∪ d.guardrails not defined in metrics[]
untrusted       = any required metric undefined, unowned, or L1 < 80
blocking_debt   = any high|critical debt whose affected_metrics ∩ d.required_metrics ≠ ∅
missing_guard   = d is risk-bearing and d.guardrails is empty

status(d):
  NOT_READY          if missing_ref or untrusted or blocking_debt
  USABLE_WITH_CAUTION else if missing_guard or (a guardrail exists but operating rhythm is Weak)
  READY              otherwise
```

### Step 2 — Headline

> **N of M key decisions are decision-ready.**

This is the primary number. It counts decisions (permitted by P1), never metrics. The decision-ready **fraction** `R = N/M` maps to a fraction-band:

| `R` | fraction-band |
|---|---|
| `R = 1.0` | Decision-ready |
| `0.5 ≤ R < 1.0` | Usable with caution |
| `0 < R < 0.5` | Fragile |
| `R = 0` or no decisions defined | Not ready *(or Not assessed if L<2)* |

### Step 3 — Dimension profile (8 grounded dimensions)

Each dimension is an **ordinal band** — `Strong / Partial / Weak / Not assessed` — with an explicit, documented driver. No 0–5 averaging. A dimension whose inputs are absent is **Not assessed** (P5), never scored 0.

| # | Dimension | Rule |
|---|---|---|
| 1 | **Decision coverage & linkage** | `Strong` if `R ≥ 0.8` and no decision has a missing ref; `Partial` if `R ≥ 0.5`; `Weak` if `R < 0.5` **or** any decision references an undefined metric. *Not assessed if no `decisions`.* |
| 2 | **Metric definition quality** | From the L1 pack score: `Strong ≥ 80`, `Partial ≥ 60`, else `Weak`. |
| 3 | **Portfolio role clarity** | `Strong` if every metric has a `role`, zero orphans, and ≥1 `primary_metric`; `Partial` if ≥80% have roles and ≤20% orphaned; else `Weak`. An **orphan** = linked to no decision and no OKR. *Not assessed if no roles present (L0).* |
| 4 | **Guardrail coverage** | Over risk-bearing decisions: `Strong` if all have ≥1 guardrail, `Partial` if ≥50%, else `Weak`. *Not assessed if no risk-bearing decisions.* |
| 5 | **Instrumentation readiness** | `Weak` if any `instrumentation.status == missing`, or any high/critical instrumentation debt affecting a **defined** metric on a decision path; `Partial` if any `partial`; else `Strong`. *Not assessed if no `instrumentation` and no `depends_on`.* |
| 6 | **Ownership clarity** | `Strong` if all metrics owned and all decisions owned; `Partial` if ≥80%; else `Weak`. |
| 7 | **Operating rhythm** | `Strong` if `review_cadence` present and (`decision_log_exists` or recent `last_reviewed`); `Partial` if cadence only; `Weak` if no cadence and no evidence. *Not assessed if no `operating_model`.* |
| 8 | **Strategy / OKR linkage** | `Strong` if most primary/supporting metrics link to an OKR and most key results resolve to a defined metric; `Partial` if one side holds; else `Weak`. *Not assessed if no `okrs`.* |

Debt is deliberately **not** its own dimension: that would double-count and would penalize honest disclosure (P4). Debt instead informs dimensions 1, 4, and 5.

### Step 4 — Overall band

Band order (best → worst): `Decision-ready > Usable with caution > Fragile > Not ready for recurring decisions`. This vocabulary is **distinct from the metric-level bands** to prevent conflating a metric score with a vertical score.

The overall band is the **worst (lowest)** of the fraction-band and every dimension cap:

| Weak dimension | caps overall at |
|---|---|
| Decision coverage & linkage | Fragile |
| Metric definition quality | Fragile |
| Instrumentation readiness (blocking) | Fragile |
| Portfolio role clarity | Usable with caution |
| Guardrail coverage | Usable with caution |
| Operating rhythm | Usable with caution |
| Ownership clarity | Usable with caution |
| Strategy / OKR linkage | Usable with caution |

`Strong`/`Partial`/`Not assessed` dimensions impose no cap.

```
overall_band = min( fraction_band, *[cap(dim) for dim in dimensions if band(dim) == Weak] )
```

### Optional 0–100 composite (deferred)

A single 0–100 number may be offered later, explicitly labelled *directional*, and only once it ships with a sensitivity check (in `analysis/`) proving the band ordering is stable under reasonable threshold variation — the same bar v1 set with its Bayesian study. It is never the headline. Until then, the headline is the fraction + bands.

---

## Measurement debt

### Derived (default — PRD P2)

Derived from the graph, not authored:

| Condition | Debt type | Default severity |
|---|---|---|
| Metric linked to no decision and no OKR (orphan) | `decision_linkage` | medium |
| Metric OKR-linked but in no decision | `decision_linkage` | low |
| Decision references an undefined metric | `decision_linkage` | high |
| Metric missing SQL / tests | `definition` / `testing` | from L1 |
| Metric missing owner | `ownership` | medium |
| `instrumentation.status != complete` | `instrumentation` | medium (missing → high) |
| Risk-bearing decision with no guardrail | `operating_rhythm` | medium |
| Guardrail metric in no reviewed forum | `operating_rhythm` | low |
| OKR key result with no resolvable metric | `strategy_linkage` | low |

### Authored

Only for what the graph cannot see. **Authored debt never lowers a dimension below the derived baseline** — disclosing a known problem must not score worse than hiding it (P4).

### Ordering (determinism)

Debt is sorted by `(severity desc, type asc, id asc)` — a total order, so the same input always yields the same top-N (PRD P6). The top 3 surface in the one-page brief.

---

## Determinism

Same input → same output. Every sort has an explicit secondary key (ids). No metric count enters any computation. No randomness, no model calls in the scoring path.

---

## Discriminant-validity test (the proof the score means something)

This is the primary validity mechanism (cheaper and more honest than asserting absolute correctness). It runs as a unit test against the three public sample packs and doubles as README evidence. The packs were authored to produce these results under the rules above:

| Pack | Decisions ready | Overall band | Definition quality | Designed-weak dimension(s) | Signature debt |
|---|---|---|---|---|---|
| `onboarding_measurement_ready` | 2 / 2 | **Decision-ready** | Strong | *none Weak* | none above `low` |
| `collaboration_portfolio_design` | 2 / 2 | **Usable with caution** | Strong | **Portfolio role clarity** (Weak) | `decision_linkage`: `comment_volume`, `mentions_per_user` orphaned |
| `search_decision_gap` | 1 / 2 | **Fragile** | Strong | **Decision coverage & linkage** (Weak); also Guardrail coverage, Operating rhythm | `decision_linkage`: `ship_search_ranking_change` → undefined `query_understanding_score` |

### Asserted (must hold)

1. **Strict band ordering:** onboarding `Decision-ready` ≻ collaboration `Usable with caution` ≻ search `Fragile`.
2. **Designed weakness present:** collaboration rates *Portfolio role clarity* = `Weak`; search rates *Decision coverage & linkage* = `Weak`; onboarding has **no** `Weak` dimension.
3. **Strength preserved:** all three rate *Metric definition quality* = `Strong`. The framework must show that good metrics do not by themselves make a system decision-ready — the discriminator is the system around them, not the metrics or their count.
4. **Signature debt** for each non-healthy pack appears in its top-3 by id.

If any assertion fails after a rules change, either the rules or the packs are wrong — fix one, never silently re-baseline.

### Why this is the right validity check

It tests *discrimination* (does the score separate systems that should differ?) and *attribution* (does it point at the real weakness?), deterministically, with no rater pool required. A larger calibration study against independent raters — mirroring the v1 calibration work — is earmarked as future work once real private packs are available.
