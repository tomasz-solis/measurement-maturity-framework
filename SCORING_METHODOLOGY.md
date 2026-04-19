# Scoring Methodology

**Version**: 1.2
**Last Updated**: 2026-04-19
**Status**: Active

This document describes the scoring logic that is actually implemented in the repo today.

If this file and the code ever disagree, the code is the source of truth:
- [mmf/config.py](mmf/config.py)
- [mmf/scoring.py](mmf/scoring.py)

---

## Scope

The scoring system measures **definition maturity** and **decision risk**.

It does not measure:
- business performance
- forecast quality
- whether the metric is strategically important

The current implementation is intentionally narrow. It focuses on a small set of failure modes that are easy to explain and easy to act on.

---

## Metric Score

Each metric starts at `100`.

Points are deducted for the following gaps:

| Check | Deduction | Why it matters |
|---|---:|---|
| `tier: V0` | -10 | Instability risk is additive to any other gap — a V0 metric may change definition mid-quarter, making trends unreliable. |
| missing `accountable` or `responsible` | -5 | No owner means slower debugging, weaker follow-up, and higher risk of the metric drifting past its shelf life. |
| missing SQL (default, `implementation_type` not set) | -5 | Without query logic the metric can't be independently reproduced or inspected. |
| missing SQL with `implementation_type: v0_proxy` | -3 | SQL is deferred while the proxy settles, so the gap is temporary by design. |
| missing SQL with `implementation_type: spreadsheet`/`notebook`/`dashboard`/`other` | -12 | No SQL because the implementation is not in a query engine. Larger deduction because the gap is structural, not temporary. |
| missing tests | -5 | Without basic checks, silent breakage goes undetected until it surfaces in a dashboard. |
| missing `description` | -3 | A metric without a description forces readers to reverse-engineer intent from naming alone. |
| missing `grain` | -2 | Without grain, a reader can't tell what one row represents, making aggregation decisions ambiguous. |
| missing `unit` | -2 | Without unit, value interpretation is a guess (is 0.12 a ratio, a percent, or a count?). |

The three SQL-missing deductions are mutually exclusive. A metric with missing SQL fires exactly one of them, selected by the `implementation_type` field. See the "The missing_sql split" section below for the full reasoning.

Formula:

```text
metric_score = clamp(
    base_score
    - v0_tier_deduction
    - missing_accountable_deduction
    - sql_deduction              # one of: missing_sql | missing_sql_temporary | missing_sql_structural
    - missing_tests_deduction
    - missing_description_deduction
    - missing_grain_deduction
    - missing_unit_deduction,
    0,
    100
)
```

Default base score is `100`.

---

## Weight Rationale

The deduction values reflect relative risk contributions, not arbitrary constants.

### V0 tier: -10

V0 gets the largest deduction because tier instability is additive to every
other gap. A V0 metric can change definition mid-quarter. That makes trend
analysis unreliable even if SQL and tests exist today — the number it tracked
last month may not be comparable to the number it tracks this month. The -10
reflects that risk to historical comparability, not just current completeness.

### Missing accountable/SQL/tests: -5 each

These carry equal weight because they represent three independent failure modes:

- **Ownership gap**: the metric may be correct today but becomes unreliable
  when upstream tables change and nobody knows they're responsible for updating
  the definition.
- **SQL gap**: without query logic, the number can't be reproduced,
  audited, or handed off to another team.
- **Test gap**: without basic checks (not_null, range bounds), breakage
  is discovered in a board deck rather than a data pipeline alert.

Each is worth -5 because each represents one dimension of verifiability.
None dominates the others — a metric with SQL but no owner is as risky in
practice as one with an owner but no SQL.

### Missing description/grain/unit: -3, -2, -2

These are softer deductions. They penalise metrics that are harder to
interpret or maintain, without blocking a pack that is otherwise well-defined.
A metric without a description but with SQL, tests, and an owner is still
usable — it's just harder to onboard new teammates to.

The asymmetry (description = -3, grain/unit = -2) reflects that missing
intent is a bigger interpretability risk than missing formatting metadata.

### The missing_sql split: -3 / -5 / -12

A single `missing_sql = -5` was too coarse to cover two structurally
different situations that both produce the same gap:

- **Temporary absence.** A V0 proxy metric where the team has deliberately
  not written SQL yet: "we'll add it once the definition settles."
  This is a soft gap because the metric is explicitly tagged as
  work-in-progress.
- **Structural absence.** A metric with no SQL because the implementation
  is not in a query engine at all — a spreadsheet pipeline, an
  undocumented notebook, a black-box dashboard calculation. This is not
  a temporary gap; it's irreducible unreviewability.

The framework distinguishes these cases using an optional
`implementation_type` field on each metric:

| `implementation_type` | Deduction | Gap code | Reason |
|---|---:|---|---|
| (absent) | -5 | `missing_sql` | Default — backward-compatible with existing packs |
| `v0_proxy` | -3 | `missing_sql_temporary` | Temporary by design |
| `spreadsheet` / `notebook` / `dashboard` / `other` | -12 | `missing_sql_structural` | Structurally unreviewable |

The three deductions are mutually exclusive. Older packs that don't declare
`implementation_type` get the backward-compatible -5 default. Analysts who
want the stronger signal opt in by declaring the type.

---

## Robustness Analysis

The deduction weights above are asserted, not derived. That's an honest
limit of the scoring model and it invites a reasonable question: how
much do the scores depend on the specific weight values?

The answer, from the Bayesian robustness study in
[`analysis/bayesian_robustness.ipynb`](analysis/bayesian_robustness.ipynb),
is: not much. Each deduction weight is treated as a random variable with a
Beta prior centred on its rule-based value (scale 20, concentration 20, so
the prior 90% CI covers roughly ±50% of each weight). Across 27 synthetic
packs spanning the realistic quality space, the Spearman rank correlation
between rule-based scores and Bayesian posterior means is **0.9992**, with
maximum absolute score divergence of **0.43 points**. The rankings are
essentially invariant to which specific weight values you pick within the
plausible range.

What this does support: the rankings stay stable under reasonable weight
uncertainty. A reviewer asking "why -10 for V0 and not -8 or -12?" gets a
quantitative answer: within that band, the ordering barely changes.

What this does not support: whether the asserted weights are *right* in
absolute terms. Calibration against independent judgments of pack quality
would still be needed for that. The small calibration study in the next
section is a first pass, not a replacement for the robustness work.

### `pack_floor_weight` sensitivity

For completeness, the table below shows how the pack score changes as
`pack_floor_weight` varies, for a two-metric pack with scores `[100, 85]`.
This is a single-dimensional sensitivity check. The full robustness
analysis in the notebook covers all seven deduction weights jointly.

| pack_floor_weight | Pack score | Interpretation |
|---|---|---|
| 0.0 | 92.50 | Pure average — ignores the weakest metric entirely |
| 0.1 | 91.75 | |
| 0.2 | 91.00 | |
| **0.3** | **90.25** | **Default — 70% average, 30% floor** |
| 0.4 | 89.50 | |
| 0.5 | 88.75 | Blend approaches 50/50 |
| 1.0 | 85.00 | Full min — pack score equals weakest metric |

The default 0.3 is conservative. A pack is often used as one decision
surface, and a single fragile metric can distort the broader story in ways
pure averages hide. Full-min (1.0) overpunishes packs where one metric is
intentionally a V0 proxy while the rest are production-ready.

---

## Calibration Findings

A small-n calibration study in
[`analysis/weight_calibration.ipynb`](analysis/weight_calibration.ipynb)
fit the default weights against a consensus ranking of the 27 synthetic
packs. The ranking was produced by two rankers: the project author
(who ranked twice for test-retest reliability, ρ = 0.97 between
attempts) and Claude as an independent LLM ranker. A ridge regression
(α = 1.0, positive weights) on gap counts per metric produced a fitted
weight configuration with three substantive differences from MMF's
defaults.

**Finding 1: `missing_sql` is underweighted.** Both rankers
independently placed missing SQL as the single most severe gap. The
fitted value is roughly 2x the current weight. This lines up with
an independent design critique that a single -5 deduction conflates
two structurally different gaps, leading to the `missing_sql` split
described above, **which has been shipped**. The magnitude revision
(e.g. raising default `missing_sql` from -5 to -8) **has not been
shipped** pending a larger-n study.

**Finding 2: `tier_v0` is overweighted.** The calibration suggests it
should be around half its current value. Rationale: V0 is useful
information for any downstream consumer because it tags the metric as a
temporary proxy. A well-documented V0 metric should not be penalised
more than a poorly-documented V1 metric. **This change has not been
shipped** for the same reason.

**Finding 3: `missing_owner` is slightly underweighted.** The
calibration suggests -7 rather than -5. **Not shipped.**

Why the magnitude revisions have not shipped:

- **n = 27 is small.** Ridge regression with seven features fit on 27
  observations is susceptible to overfitting even with regularisation.
- **Two rankers is thin.** The study has one human rater (the project
  author) and one LLM rater. A stronger calibration needs at least
  three independent human raters, ideally drawn from different
  professional backgrounds.
- **Synthetic packs only.** Real-world metric packs might show
  different weight dynamics.

The notebook is explicit about those caveats. Shipping the fitted weights now
would ignore the notebook's own warning labels.

What has shipped from this work: the `missing_sql` split into `missing_sql_temporary`
(-3) and `missing_sql_structural` (-12), selected by the
`implementation_type` field. This addresses the *structural* form of
Finding 1 without relying on the magnitude of a small-n fit.

A follow-up calibration with a larger rater pool is earmarked as
future work. The scaffolding (worksheet, ranking CSVs, fit code) is
in place so that a second study can be run quickly once independent
raters are available.

---

## Pack Score

The pack score is not a plain average.

It blends:
- the average metric score
- the weakest metric score

Formula:

```text
pack_score = (1 - pack_floor_weight) * average_metric_score
           + pack_floor_weight * min_metric_score
```

Default configuration:

```text
pack_floor_weight = 0.3
```

This means the pack score is:
- 70% average metric quality
- 30% weakest-metric floor

Why do this:
- a pack is often used as one decision surface
- a single fragile metric can distort a broader story
- pure averages hide that risk too easily

---

## Thresholds

Current thresholds come from [mmf/config.py](mmf/config.py):

| Range | Label |
|---|---|
| `80-100` | Decision-ready |
| `60-79` | Usable with caution |
| `40-59` | Early/fragile |
| `0-39` | Not safe for decisions |

Interpretation:

### 80-100: Decision-ready

This usually means:
- ownership is defined
- SQL is present
- tests are present
- the metric is not a V0 proxy, or it compensates for that elsewhere

Safe for:
- dashboards used in regular operating reviews
- target tracking
- decisions that need a stable metric definition

### 60-79: Usable with caution

This usually means:
- the metric is useful
- at least one structural gap still matters
- the metric may be acceptable for directional work but should be reviewed before it becomes a commitment metric

Safe for:
- exploration
- trend monitoring
- hypothesis generation

### 40-59: Early/fragile

This usually means:
- multiple structural gaps are still present
- the metric is more of a draft signal than a reliable operating metric

Safe for:
- prototypes
- early exploratory analysis

### 0-39: Not safe for decisions

This usually means:
- too many core safeguards are missing
- the metric definition is not strong enough for serious reliance

Recommendation:
- fix ownership, SQL, and tests before using it in a meaningful decision loop

---

## Worked Examples

### Example 1: Fully defined V1 metric

```yaml
id: active_accounts
name: Active Accounts
description: Daily active accounts with at least one qualifying event.
tier: V1
accountable: Growth Team
grain: account_day
unit: count
sql:
  value: |
    SELECT COUNT(DISTINCT account_id) FROM account_activity
tests:
  - type: not_null
```

Score:

```text
100
```

### Example 2: V0 proxy with no SQL or tests

```yaml
id: support_ticket_ratio
name: Support Ticket Ratio
tier: V0
responsible: Customer Success
```

Score:

```text
100 - 10 - 5 - 5 - 3 - 2 - 2 = 73
```

The metric keeps ownership, but still loses points for being a V0 proxy with no SQL, no tests, and missing basic interpretability fields.

### Example 3: Mixed pack

Metric scores:

```text
[100, 85]
```

Intermediate values:

```text
average_metric_score = 92.5
min_metric_score = 85
```

Pack score:

```text
pack_score = 0.7 * 92.5 + 0.3 * 85 = 90.25
```

Rounded result:

```text
90.25
```

This is why the pack score can be lower than the average metric score even when most metrics look strong.

### Example 4: The SQL split in action

The same bare V0 proxy from Example 2, but now declared explicitly as a
`v0_proxy`:

```yaml
id: support_ticket_ratio
name: Support Ticket Ratio
tier: V0
responsible: Customer Success
implementation_type: v0_proxy
```

Score:

```text
100 - 10 (V0) - 3 (missing_sql_temporary) - 5 (tests) - 3 (desc) - 2 (grain) - 2 (unit) = 75
```

Declaring the metric as a deliberate V0 proxy earns a 2-point softening
on the SQL gap, lifting the score from 73 (Example 2) to 75. The framework
reads this as: "the analyst explicitly marked this as work-in-progress,
the missing SQL is a feature of the stage, not a reliability problem."

Contrast with a metric that has owner, tests, description, grain, and
unit — but is implemented in a spreadsheet:

```yaml
id: weekly_ticket_ratio
name: Weekly Ticket Ratio
description: Weekly ratio of tickets to active accounts.
grain: account_week
unit: ratio
responsible: Customer Success
implementation_type: spreadsheet
tests:
  - type: not_null
```

Score:

```text
100 - 12 (missing_sql_structural) = 88
```

The metric is otherwise well-defined. The -12 deduction reflects that a
spreadsheet implementation is irreducibly unreviewable — not a temporary
gap. At 88, the metric is still in the "decision-ready" band but sits
meaningfully below the equivalent SQL-backed version at 100.

---

## Relationship To Validation

Validation and scoring are related, but they are not the same thing.

Validation checks additional things that do not currently change the score, including:
- missing `schema_version`
- unknown `schema_version`
- missing `requires`
- missing metric `name`
- duplicate metric IDs
- malformed `metrics`
- partial ratio SQL
- lightweight SQL syntax warnings when `sqlparse` is available

That means:
- a pack can validate with warnings and still score well
- a pack can score well while still having useful info-level cleanup items
- not every validation issue is a scoring deduction

---

## Relationship To Suggestions

Suggestions are generated from the scored output plus the metric definitions.

The current scorer emits these gap types:
- `tier_v0`
- `missing_accountable`
- `missing_sql` (default when `implementation_type` is not set)
- `missing_sql_temporary` (when `implementation_type: v0_proxy`)
- `missing_sql_structural` (when `implementation_type` is `spreadsheet`, `notebook`, `dashboard`, or `other`)
- `missing_tests`
- `missing_description`
- `missing_grain`
- `missing_unit`

The three `missing_sql*` gaps are mutually exclusive; exactly one fires per metric that lacks SQL.

The suggestion layer can also react to richer gap names (for example, `deprecated_status`), which makes it ready for future scoring expansion, but those richer gaps are not part of the active scoring contract today.

---

## Configuration

Default configuration is defined in [mmf/config.py](mmf/config.py):

```python
ScoringConfig(
    base_score=100,
    deductions={
        "v0_tier": 10,
        "missing_accountable": 5,
        "missing_sql": 5,              # default when implementation_type is not set
        "missing_sql_temporary": 3,    # v0_proxy
        "missing_sql_structural": 12,  # spreadsheet | notebook | dashboard | other
        "missing_tests": 5,
        "missing_description": 3,
        "missing_grain": 2,
        "missing_unit": 2,
    },
    thresholds={
        "decision_ready": 80,
        "usable_with_caution": 60,
        "early_fragile": 40,
    },
    pack_floor_weight=0.3,
)
```

If you change these values:
- update the tests
- update this document
- re-check the app labels and threshold descriptions
- re-run the Bayesian robustness analysis to confirm rank stability still holds

---

## Current Limits

The current scoring model does not deduct for:

- deprecated status (surfaced as a suggestion only)
- missing upstream dependencies (`requires`)

These may appear in suggestions but are not active scoring deductions.
`missing_description`, `missing_grain`, and `missing_unit` are now active
deductions (see the table above).

The calibration study (see "Calibration Findings" above) also flagged
three weight-magnitude revisions that are **not** shipped:

- `missing_sql` default value (currently -5; calibration suggests -8 to -10)
- `tier_v0` (currently -10; calibration suggests ~-5)
- `missing_accountable` (currently -5; calibration suggests ~-7)

These are held pending a larger-n rater pool. They do not affect the
current scoring behaviour and are documented here so that any future
calibration study starts from a clear record of what was considered
and deferred.
