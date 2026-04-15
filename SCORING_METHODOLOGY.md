# Scoring Methodology

**Version**: 1.1  
**Last Updated**: 2026-04-15  
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
| missing SQL | -5 | Without query logic the metric can't be independently reproduced or inspected. |
| missing tests | -5 | Without basic checks, silent breakage goes undetected until it surfaces in a dashboard. |
| missing `description` | -3 | A metric without a description forces readers to reverse-engineer intent from naming alone. |
| missing `grain` | -2 | Without grain, a reader can't tell what one row represents, making aggregation decisions ambiguous. |
| missing `unit` | -2 | Without unit, value interpretation is a guess (is 0.12 a ratio, a percent, or a count?). |

Formula:

```text
metric_score = clamp(
    base_score
    - v0_tier_deduction
    - missing_accountable_deduction
    - missing_sql_deduction
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

---

## Sensitivity Analysis

The table below shows how the pack score changes as `pack_floor_weight` varies,
for a representative two-metric pack with scores of `[100, 85]`.

| pack_floor_weight | Pack score | Interpretation |
|---|---|---|
| 0.0 | 92.50 | Pure average — ignores the weakest metric entirely |
| 0.1 | 91.75 | |
| 0.2 | 91.00 | |
| **0.3** | **90.25** | **Default — 70% average, 30% floor** |
| 0.4 | 89.50 | |
| 0.5 | 88.75 | Blend approaches 50/50 |
| 1.0 | 85.00 | Full min — pack score equals weakest metric |

The default 0.3 is a conservative choice. A pack is often used as one decision
surface, and a single fragile metric can distort the broader story in ways that
pure averages hide. Full-min (1.0) overpunishes packs where one metric is
intentionally a V0 proxy while the rest are production-ready.

A future calibration study could derive an optimal floor weight from a labelled
dataset of historical metric quality outcomes. The current value is a principled
starting point, not an empirically optimised parameter.

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
- `missing_sql`
- `missing_tests`
- `missing_description`
- `missing_grain`
- `missing_unit`

The suggestion layer can also react to richer gap names, which makes it ready for future scoring expansion, but those richer gaps are not part of the active scoring contract today.

---

## Configuration

Default configuration is defined in [mmf/config.py](mmf/config.py):

```python
ScoringConfig(
    base_score=100,
    deductions={
        "v0_tier": 10,
        "missing_accountable": 5,
        "missing_sql": 5,
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

---

## Current Limits

The current scoring model does not deduct for:

- deprecated status (surfaced as a suggestion only)
- missing upstream dependencies (`requires`)

These may appear in suggestions but are not active scoring deductions.
`missing_description`, `missing_grain`, and `missing_unit` are now active
deductions (see the table above).
