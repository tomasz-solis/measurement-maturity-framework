# V2 scoring methodology: vertical measurement readiness

Status: draft. Related: [V2_SCHEMA.md](V2_SCHEMA.md), [PRD](PRD_v2_product_measurement_readiness.md), [SCORING_METHODOLOGY.md](../SCORING_METHODOLOGY.md) (v1).

The v2 scoring logic, precise enough to reproduce by hand. As in v1, if this doc and the code disagree, the code wins.

## Scope

v2 works on a measurement graph (metrics, decisions, OKRs, guardrails, instrumentation) and reports how ready a vertical's measurement system is to support recurring decisions.

It measures whether the system is documented and structured to support decisions, not whether decisions are actually made that way (PRD P4). Evidence fields (`decision_log_exists`, `last_reviewed`) count for more than self-declared links. The product never claims to observe behaviour from a static pack.

Count is never an input (PRD P1). No rule here reads the number of OKRs, KPIs or metrics. Problems are counted instead: orphans, missing roles, unlinked decisions.

## Two layers

| Layer | Question | Output |
|---|---|---|
| L1: metric readiness | Is this metric structurally ready? | 0 to 100 per metric (same as v1) |
| L2: vertical readiness | Can this vertical support recurring decisions? | Decision-ready fraction, 8 dimension bands, overall band |

### Layer 1

The v1 model unchanged: each metric starts at 100 and loses points for structural gaps (tier V0, missing owner, SQL, tests, description, grain, unit), and `pack_floor_weight` blends them into a pack score. See [SCORING_METHODOLOGY.md](../SCORING_METHODOLOGY.md). v2 metrics use the same code.

## Layer 2: vertical readiness

Built up from decisions, not as a weighted average of dimensions.

### Step 1: decision readiness

A metric is trusted for gating decisions if its L1 score is at least 80 (the v1 decision-ready cutoff). That bar is deliberately higher than the 60 "usable" cutoff, and it settles PRD open question Q3.

A decision is risk-bearing if `decision_type` is one of `rollout`, `launch`, `ranking_change`, `pricing_change`, `default_change` or `deprecation`. Others (`prioritization`, `investment`, `monitoring` and so on) don't need a guardrail.

For each decision `d`, in order:

```text
missing_ref     = any id in d.required_metrics ∪ d.guardrails not defined in metrics[]
untrusted       = any required metric undefined, unowned, or L1 < 80
blocking_debt   = any high|critical debt whose affected_metrics ∩ d.required_metrics ≠ ∅
missing_guard   = d is risk-bearing and d.guardrails is empty

status(d):
  NOT_READY          if missing_ref or untrusted or blocking_debt
  USABLE_WITH_CAUTION else if missing_guard or (a guardrail exists but operating rhythm is Weak)
  READY              otherwise
```

### Step 2: headline

> N of M key decisions are decision-ready.

The main number. It counts decisions (allowed by P1), never metrics. The fraction `R = N/M` maps to a band:

| `R` | Fraction band |
|---|---|
| `R = 1.0` | Decision-ready |
| `0.5 ≤ R < 1.0` | Usable with caution |
| `0 < R < 0.5` | Fragile |
| `R = 0` or no decisions defined | Not ready (or Not assessed if L<2) |

### Step 3: eight dimensions

Each dimension gets an ordinal band (`Strong`, `Partial`, `Weak`, `Not assessed`) with a documented rule. No 0 to 5 averaging. A dimension without inputs is Not assessed (P5), never scored 0.

| # | Dimension | Rule |
|---|---|---|
| 1 | Decision coverage & linkage | `Strong` if `R ≥ 0.8` and no decision has a missing ref. `Partial` if `R ≥ 0.5`. `Weak` if `R < 0.5` or any decision points to an undefined metric. Not assessed without `decisions`. |
| 2 | Metric definition quality | From the L1 pack score: `Strong` at 80 or more, `Partial` at 60 or more, else `Weak`. |
| 3 | Portfolio role clarity | `Strong` if every metric has a `role`, there are no orphans and at least one `primary_metric`. `Partial` if at least 80% have roles and at most 20% are orphaned. Else `Weak`. An orphan links to no decision and no OKR. Not assessed without roles (L0). |
| 4 | Guardrail coverage | Over risk-bearing decisions: `Strong` if all have a guardrail, `Partial` if at least 50% do, else `Weak`. Not assessed without risk-bearing decisions. |
| 5 | Instrumentation readiness | `Weak` if any `instrumentation.status == missing`, or high/critical instrumentation debt hits a defined metric on a decision path. `Partial` if any is `partial`. Else `Strong`. Not assessed without `instrumentation` and `depends_on`. |
| 6 | Ownership clarity | `Strong` if all metrics and decisions have owners. `Partial` at 80% or more. Else `Weak`. |
| 7 | Operating rhythm | `Strong` if `review_cadence` is set and there is `decision_log_exists` or a recent `last_reviewed`. `Partial` with cadence only. `Weak` with neither. Not assessed without `operating_model`. |
| 8 | Strategy / OKR linkage | `Strong` if most primary and supporting metrics link to an OKR and most key results resolve to a defined metric. `Partial` if one side holds. Else `Weak`. Not assessed without `okrs`. |

Debt isn't its own dimension. That would double count and penalise honest disclosure (P4). Debt feeds dimensions 1, 4 and 5 instead.

### Step 4: overall band

Bands from best to worst: `Decision-ready`, `Usable with caution`, `Fragile`, `Not ready for recurring decisions`. These names differ from the metric-level bands on purpose, so a metric score and a vertical score can't be confused.

The overall band is the worst of the fraction band and every dimension cap:

| Weak dimension | Caps overall at |
|---|---|
| Decision coverage & linkage | Fragile |
| Metric definition quality | Fragile |
| Instrumentation readiness (blocking) | Fragile |
| Portfolio role clarity | Usable with caution |
| Guardrail coverage | Usable with caution |
| Operating rhythm | Usable with caution |
| Ownership clarity | Usable with caution |
| Strategy / OKR linkage | Usable with caution |

`Strong`, `Partial` and `Not assessed` dimensions don't cap anything.

```text
overall_band = min( fraction_band, *[cap(dim) for dim in dimensions if band(dim) == Weak] )
```

### Optional 0 to 100 composite (deferred)

A single 0 to 100 number may come later, labelled directional, and only with a sensitivity check (in `analysis/`) showing the band order is stable under reasonable threshold changes, the same bar v1 set with its Bayesian study. It will never be the headline. Until then the headline is the fraction plus the bands.

## Measurement debt

### Derived (default, PRD P2)

Worked out from the graph, not written by hand:

| Condition | Debt type | Default severity |
|---|---|---|
| Metric linked to no decision and no OKR (orphan) | `decision_linkage` | medium |
| Metric linked to an OKR but no decision | `decision_linkage` | low |
| Decision points to an undefined metric | `decision_linkage` | high |
| Metric missing SQL or tests | `definition` / `testing` | from L1 |
| Metric missing owner | `ownership` | medium |
| `instrumentation.status != complete` | `instrumentation` | medium (high if missing) |
| Risk-bearing decision with no guardrail | `operating_rhythm` | medium |
| Guardrail metric in no reviewed forum | `operating_rhythm` | low |
| OKR key result with no resolvable metric | `strategy_linkage` | low |

### Authored

Only for what the graph can't see. Authored debt never lowers a dimension below the derived baseline: disclosing a known problem must never score worse than hiding it (P4).

### Ordering

Debt is sorted by `(severity desc, type asc, id asc)`, a total order, so the same input always gives the same top N (PRD P6). The top 3 appear in the one-page brief.

## Determinism

Same input, same output. Every sort has an explicit secondary key (ids). No metric count enters any calculation. No randomness and no model calls in scoring.

## Discriminant validity test

The main check that the score means something. It is cheaper and more honest than claiming absolute correctness. It runs as a unit test on the three public sample packs and also serves as README evidence. The packs were written to produce these results under the rules above:

| Pack | Decisions ready | Overall band | Definition quality | Designed weak dimension(s) | Signature debt |
|---|---|---|---|---|---|
| `onboarding_measurement_ready` | 2 / 2 | Decision-ready | Strong | none | nothing above `low` |
| `collaboration_portfolio_design` | 2 / 2 | Usable with caution | Strong | Portfolio role clarity | `decision_linkage`: `comment_volume`, `mentions_per_user` orphaned |
| `search_decision_gap` | 1 / 2 | Fragile | Strong | Decision coverage & linkage; also Guardrail coverage, Operating rhythm | `decision_linkage`: `ship_search_ranking_change` points to undefined `query_understanding_score` |

### Must hold

1. Strict band order: onboarding `Decision-ready`, then collaboration `Usable with caution`, then search `Fragile`.
2. The designed weakness shows: collaboration has Portfolio role clarity `Weak`, search has Decision coverage & linkage `Weak`, and onboarding has no `Weak` dimension.
3. Strength is kept: all three rate Metric definition quality `Strong`. Good metrics alone don't make a system decision-ready; what separates them is the system around the metrics, not the metrics or their count.
4. Each non-healthy pack's signature debt is in its top 3 by id.

If an assertion fails after a rules change, either the rules or the packs are wrong. Fix one; never quietly re-baseline.

### Why this is the right check

It tests discrimination (does the score separate systems that should differ?) and attribution (does it point at the real weakness?), deterministically, without a rater pool. A larger calibration study with independent raters, like the v1 work, is planned once real private packs exist.
