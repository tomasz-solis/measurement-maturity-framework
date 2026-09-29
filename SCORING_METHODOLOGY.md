# Scoring methodology

Version 1.2. Last updated 2026-04-19. Status: active.

The scoring logic as implemented. If this file and the code disagree, the code wins: [mmf/config.py](mmf/config.py) and [mmf/scoring.py](mmf/scoring.py).

## Scope

The score measures how mature a metric definition is and how risky it is to decide on. It doesn't measure business performance, forecast quality or strategic importance. It covers a small set of failure modes that are easy to explain and act on.

## Metric score

Each metric starts at `100` and loses points for these gaps:

| Check | Deduction | Why it matters |
|---|---:|---|
| `tier: V0` | -10 | A V0 metric may change definition mid-quarter, so trends are unreliable. This adds to any other gap. |
| missing `accountable` or `responsible` | -5 | No owner means slower debugging, weaker follow-up and a metric that outlives its usefulness. |
| missing SQL (default, no `implementation_type`) | -5 | Without query logic nobody can reproduce or inspect the metric. |
| missing SQL with `implementation_type: v0_proxy` | -3 | SQL is deferred while the proxy settles, so the gap is temporary by design. |
| missing SQL with `implementation_type: spreadsheet`/`notebook`/`dashboard`/`other` | -12 | The metric doesn't live in a query engine. The gap is structural, not temporary. |
| missing tests | -5 | Without basic checks, breakage stays hidden until it shows up in a dashboard. |
| missing `description` | -3 | Readers have to guess intent from the name. |
| missing `grain` | -2 | Readers can't tell what one row is, so aggregation is ambiguous. |
| missing `unit` | -2 | Is 0.12 a ratio, a percent or a count? |

Only one of the three missing-SQL deductions fires, chosen by `implementation_type` (see [the missing SQL split](#the-missing-sql-split--3---5---12)).

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

The default base score is `100`.

## Why these weights

The deductions reflect relative risk.

### V0 tier: -10

The largest deduction, because instability adds to every other gap. A V0 metric can change definition mid-quarter, so even with SQL and tests today, last month's number may not compare with this month's. The -10 is for lost comparability over time, not current completeness.

### Missing owner, SQL or tests: -5 each

Three independent failure modes, weighted equally:

- No owner: the metric may be right today but breaks when upstream tables change and nobody knows they should update it.
- No SQL: the number can't be reproduced, audited or handed to another team.
- No tests: without basic checks (not_null, range bounds), breakage is found in a board deck instead of a pipeline alert.

None dominates. A metric with SQL but no owner is as risky as one with an owner but no SQL.

### Missing description, grain or unit: -3, -2, -2

Softer deductions. They penalise metrics that are harder to read or maintain without blocking an otherwise sound pack. A metric with SQL, tests and an owner but no description is still usable; new teammates just need longer to understand it. Missing intent (-3) is a bigger reading risk than missing formatting metadata (-2).

### The missing SQL split: -3 / -5 / -12

One `missing_sql = -5` was too coarse for two different situations:

- Temporary: a V0 proxy where the team hasn't written SQL yet on purpose ("we'll add it once the definition settles"). A soft gap, because the metric is tagged as work in progress.
- Structural: no SQL because the metric isn't in a query engine at all (a spreadsheet pipeline, an undocumented notebook, a black-box dashboard calculation). Not temporary, and hard to review independently.

The optional `implementation_type` field tells them apart:

| `implementation_type` | Deduction | Gap code | Reason |
|---|---:|---|---|
| (absent) | -5 | `missing_sql` | Default, compatible with existing packs |
| `v0_proxy` | -3 | `missing_sql_temporary` | Temporary by design |
| `spreadsheet` / `notebook` / `dashboard` / `other` | -12 | `missing_sql_structural` | Can't be reviewed |

Older packs without `implementation_type` get the -5 default. Analysts who want the stronger signal declare the type.

## Robustness

The weights are set by judgment, not derived, so the fair question is how much the scores depend on them. The Bayesian study in [`analysis/bayesian_robustness.ipynb`](analysis/bayesian_robustness.ipynb) says: very little.

Each weight is treated as a random variable with a Beta prior centred on its rule-based value (scale 20, concentration 20, so the 90% prior interval covers about ±50% of each weight). Across 27 synthetic packs covering the realistic quality range, the Spearman correlation between rule-based scores and Bayesian posterior means is 0.9992, and the largest score gap is 0.43 points.

So rankings hold under reasonable weight uncertainty. Asked "why -10 for V0 and not -8 or -12?", the answer is that within that range the order barely changes. What the study can't show is whether the weights are right in absolute terms. That needs calibration against independent judgments, which the next section starts on.

### `pack_floor_weight` sensitivity

How the pack score moves with `pack_floor_weight` for a two-metric pack scoring `[100, 85]`. This is one dimension; the notebook covers all seven weights together.

| pack_floor_weight | Pack score | Meaning |
|---|---|---|
| 0.0 | 92.50 | Plain average, ignores the weakest metric |
| 0.1 | 91.75 | |
| 0.2 | 91.00 | |
| 0.3 | 90.25 | Default: 70% average, 30% floor |
| 0.4 | 89.50 | |
| 0.5 | 88.75 | Close to 50/50 |
| 1.0 | 85.00 | Pack score equals the weakest metric |

The default 0.3 is conservative. A pack is often used as one decision surface, and one fragile metric can distort the story in ways an average hides. Full minimum (1.0) overpunishes packs where one metric is a deliberate V0 proxy and the rest are production-ready.

## Calibration findings

A small calibration study in [`analysis/weight_calibration.ipynb`](analysis/weight_calibration.ipynb) fit weights to a consensus ranking of the 27 synthetic packs. Two raters produced the ranking: me (twice, for test-retest reliability, ρ = 0.97 between attempts) and an independent model rater as a second check. A ridge regression (α = 1.0, positive weights) on gap counts per metric gave fitted weights with three material differences from the defaults:

| Finding | Default | Fitted | Status |
|---|---|---|---|
| `missing_sql` is underweighted. Both raters ranked missing SQL as the most severe gap. | -5 | about -8 to -10 (roughly 2x) | Magnitude not shipped. The structural split (above) shipped. |
| `tier_v0` is overweighted. A well-documented V0 metric shouldn't lose more than a poorly documented V1 metric. | -10 | about -5 | Not shipped |
| `missing_owner` is slightly underweighted. | -5 | about -7 | Not shipped |

The first finding matched an independent critique that one -5 lumped two different gaps together, which led to the `missing_sql` split.

Why the magnitudes haven't shipped:

- n = 27 is small. A ridge regression with seven features on 27 observations can overfit even with regularisation.
- Two raters is thin: one human (me) and one LLM. A stronger study needs at least three independent human raters from different backgrounds.
- The packs are synthetic. Real packs may behave differently.

The notebook states these caveats, and shipping the fitted weights now would ignore them. A follow-up with more raters is planned; the worksheet, ranking CSVs and fit code are ready for it.

## Pack score

The pack score blends the average metric score with the weakest one:

```text
pack_score = (1 - pack_floor_weight) * average_metric_score
           + pack_floor_weight * min_metric_score
```

With the default `pack_floor_weight = 0.3`, that is 70% average quality and 30% weakest-metric floor. A pack is often one decision surface, and a plain average hides a single fragile metric too easily.

## Bands

Thresholds come from [mmf/config.py](mmf/config.py):

| Range | Label | Usually means | Safe for |
|---|---|---|---|
| `80-100` | Decision-ready | Owner, SQL and tests present; not a V0 proxy, or it makes up for it elsewhere | Dashboards in regular reviews, target tracking, decisions needing a stable definition |
| `60-79` | Usable with caution | Useful, but at least one structural gap still matters. Fine for direction, review it before it becomes a commitment metric. | Exploration, trend monitoring, forming hypotheses |
| `40-59` | Early/fragile | Several structural gaps. More a draft signal than an operating metric. | Prototypes, early exploration |
| `0-39` | Not safe for decisions | Too many core safeguards missing | Nothing yet. Fix owner, SQL and tests first. |

## Worked examples

### 1. Fully defined V1 metric

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

Score: `100`.

### 2. V0 proxy with no SQL or tests

```yaml
id: support_ticket_ratio
name: Support Ticket Ratio
tier: V0
responsible: Customer Success
```

Score: `100 - 10 - 5 - 5 - 3 - 2 - 2 = 73`. It has an owner but loses points for being a V0 proxy with no SQL, no tests and no description, grain or unit.

### 3. Mixed pack

Metric scores `[100, 85]`, so the average is 92.5 and the minimum is 85:

```text
pack_score = 0.7 * 92.5 + 0.3 * 85 = 90.25
```

This is why a pack can score below its average when most metrics look strong.

### 4. The SQL split in action

Example 2, now declared as a `v0_proxy`:

```yaml
id: support_ticket_ratio
name: Support Ticket Ratio
tier: V0
responsible: Customer Success
implementation_type: v0_proxy
```

```text
100 - 10 (V0) - 3 (missing_sql_temporary) - 5 (tests) - 3 (desc) - 2 (grain) - 2 (unit) = 75
```

Declaring the proxy softens the SQL gap by 2 points, from 73 to 75. The analyst marked it as work in progress, so the missing SQL belongs to the stage, not to a reliability problem.

Compare a metric with an owner, tests, description, grain and unit that lives in a spreadsheet:

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

```text
100 - 12 (missing_sql_structural) = 88
```

Otherwise well defined. The -12 reflects that a spreadsheet is hard to review outside the spreadsheet. At 88 it is still decision-ready, but clearly below the SQL-backed version at 100.

## Validation vs scoring

Validation checks some things that don't change the score: missing or unknown `schema_version`, missing `requires`, missing metric `name`, duplicate IDs, malformed `metrics`, partial ratio SQL, and SQL syntax warnings when `sqlparse` is available. So a pack can validate with warnings and still score well, and not every validation issue is a deduction.

## Suggestions

Suggestions come from the scored output and the metric definitions. The scorer emits these gaps:

| Gap | When |
|---|---|
| `tier_v0` | Tier is V0 |
| `missing_accountable` | No owner |
| `missing_sql` | No SQL, no `implementation_type` |
| `missing_sql_temporary` | No SQL, `implementation_type: v0_proxy` |
| `missing_sql_structural` | No SQL, `implementation_type` is `spreadsheet`, `notebook`, `dashboard` or `other` |
| `missing_tests` | No tests |
| `missing_description` | No description |
| `missing_grain` | No grain |
| `missing_unit` | No unit |

Exactly one `missing_sql*` gap fires per metric without SQL. The suggestion layer also handles richer gap names (such as `deprecated_status`) for future rules, but those aren't part of the scoring contract today.

## Configuration

Defaults live in [mmf/config.py](mmf/config.py):

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

If you change them:

1. Update the tests.
2. Update this document.
3. Check the app labels and band descriptions.
4. Rerun the Bayesian robustness analysis to confirm the rankings still hold.

## Current limits

No deduction today for deprecated status (a suggestion only) or missing upstream dependencies (`requires`).

The three weight changes from the calibration study (`missing_sql` to about -8 to -10, `tier_v0` to about -5, `missing_accountable` to about -7) are on hold until a larger rater pool exists. They don't affect scoring now; they are recorded so the next study starts from a clear list of what was considered and deferred.
