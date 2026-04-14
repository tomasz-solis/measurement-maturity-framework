# Scoring Methodology

**Version**: 1.1  
**Last Updated**: 2026-04-14  
**Status**: Active

This document describes the scoring logic that is actually implemented in the repo today.

If this file and the code ever disagree, the code is the source of truth:
- [mmf/config.py](../mmf/config.py)
- [mmf/scoring.py](../mmf/scoring.py)

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
| `tier: V0` | -10 | Early proxies are less stable by definition. |
| missing `accountable` or `responsible` | -5 | No clear owner means slower debugging and weaker follow-up. |
| missing SQL | -5 | Without query logic, the metric cannot be reproduced or inspected. |
| missing tests | -5 | Without basic checks, breakage is easier to miss. |

Formula:

```text
metric_score = clamp(
    base_score
    - v0_tier_deduction
    - missing_accountable_deduction
    - missing_sql_deduction
    - missing_tests_deduction,
    0,
    100
)
```

Default base score is `100`.

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

Current thresholds come from [mmf/config.py](../mmf/config.py):

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
tier: V1
accountable: Growth Team
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
100 - 10 - 5 - 5 = 80
```

The metric keeps ownership, but still loses points for being a V0 proxy with no SQL and no tests.

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

The suggestion layer can also react to richer gap names, which makes it ready for future scoring expansion, but those richer gaps are not part of the active scoring contract today.

---

## Configuration

Default configuration is defined in [mmf/config.py](../mmf/config.py):

```python
ScoringConfig(
    base_score=100,
    deductions={
        "v0_tier": 10,
        "missing_accountable": 5,
        "missing_sql": 5,
        "missing_tests": 5,
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

The current scoring model does not yet deduct for:
- missing description
- missing grain
- missing unit
- missing dependencies
- deprecated status

Those may still appear in docs or suggestions discussions as future extensions, but they are not active scoring deductions in the current codebase.
