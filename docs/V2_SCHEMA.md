# V2 Schema — Vertical Measurement Pack

Status: Draft
Schema version: `"2.0"`
Companion: [V2_SCORING_METHODOLOGY.md](V2_SCORING_METHODOLOGY.md), [PRD](PRD_v2_product_measurement_readiness.md)

A v2 pack describes **one product vertical as a measurement graph**: metrics, the decisions they feed, the OKRs they ladder to, the guardrails that protect them, the instrumentation they depend on, and the ownership and rhythm that keep them alive.

This document defines the structure. The scoring rules that read it live in the methodology doc.

---

## Version routing (the single source of truth)

`mmf/schema.py` reads `pack.schema_version` and routes:

| `pack.schema_version` | Behavior |
|---|---|
| `"1.0"` | v1 path. Validated and scored exactly as before. v2 sections ignored. |
| `"2.0"` | v2 path. Full vertical analysis. |
| anything else / missing | Clear warning; best-effort v1 path. |

A v1 pack is therefore a valid input — it simply unlocks less. Existing v1 packs and fixtures must continue to pass unchanged.

---

## Progressive levels (you do not need a full pack to get value)

A pack is useful at any level. Higher levels unlock more analysis; **absent sections are reported as _not assessed_, never penalized as zero.** This is what lets a partially-mapped vertical produce partial value instead of dozens of "broken reference" errors.

| Level | Add these sections | Unlocks |
|---|---|---|
| **L0** | `metrics` only | v1 metric readiness (unchanged) |
| **L1** | `metrics[].role`, `strategy`, `okrs` | portfolio role clarity, strategy/OKR linkage |
| **L2** | `decisions` | decision map, decision-readiness rollup, overall band |
| **L3** | `instrumentation`, `operating_model`, authored `measurement_debt` | instrumentation readiness, operating rhythm, full brief |

---

## Three orthogonal axes (do not conflate them)

A common confusion is collapsing three independent properties of a metric into one. v2 keeps them separate:

| Axis | Field | Question it answers | Values |
|---|---|---|---|
| **Maturity tier** | `tier` | How stable is the definition? | `V0` (proxy) / `V1` (settled) — same as v1 |
| **Portfolio role** | `role` | What job does this metric do? | `primary_metric`, `supporting_metric`, … (§ Roles) |
| **Definition quality** | *(derived)* | Is it structurally ready? | the v1 metric-readiness score, 0–100 |

A `V1`, `primary_metric` scoring `100` and a `V0`, `guardrail_metric` scoring `72` are three-way independent facts. Nothing in the schema or scoring treats them as the same thing.

---

## Count neutrality (binding)

The schema contains **no** field for an expected or target number of OKRs, KPIs, or metrics, and no scoring rule reads metric count. `metric_portfolio.design_intent` is free text for the author's own context and is never scored. The framework expresses operating concerns as **count of problems** (orphaned metrics, missing roles, unlinked decisions), never **count of metrics**. See the methodology doc and PRD §4 (P1).

---

## Top-level sections

### `pack` (required)

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Unique pack id. |
| `name` | ✓ | str | Human name. |
| `version` |  | str | Pack version (semver-ish). |
| `schema_version` | ✓ | str | `"2.0"` for v2. Drives routing. |
| `visibility` | ✓ | enum | `public_sample` \| `private`. **Validated**: a committed pack under `examples/` must be `public_sample`. |

### `vertical` (required at L1+)

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Vertical id. Missing → error. |
| `name` | ✓ | str | Missing → error. |
| `description` |  | str | |
| `lifecycle_stage` |  | enum | e.g. `exploring` \| `scaling` \| `mature`. Informational. |
| `owner` |  | str | Missing → warning. |

### `strategy` (L1+)

```yaml
strategy:
  company_goals:
    - { id: retention, name: Customer Retention }
  vertical_outcomes:
    - id: faster_first_value
      name: Get new accounts to first value faster
      linked_company_goals: [retention]   # ids must resolve
```

### `okrs` (L1+)

```yaml
okrs:
  - id: onboarding_okr_1
    objective: Improve activation
    owner: Onboarding Product Team
    period: Example period            # keep org-agnostic in public packs
    key_results:
      - id: kr_activation
        description: Increase 14-day activation rate
        linked_metrics: [activation_rate]   # ids must resolve to metrics[]
```

- Multiple key results per OKR are supported.
- `linked_metrics` ids must resolve; broken links are flagged.
- An OKR with no resolvable metric is flagged informationally (strategy-linkage debt).

### `metric_portfolio` (optional, L1+)

| Field | Req | Type | Notes |
|---|---|---|---|
| `design_intent` |  | str | Free text. **Unscored.** No count fields exist. |

### `metrics` (required, all levels)

Superset of the v1 metric, plus v2 graph fields. All v1 scoring fields behave identically.

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Unique. |
| `name` | ✓ | str | |
| `role` | L1+ | enum | Portfolio role (§ Roles). Missing → role-clarity finding. |
| `tier` |  | enum | `V0` \| `V1`. v1 scoring. |
| `status` |  | str | `active` default. |
| `accountable` / `responsible` |  | str | Either satisfies ownership. Missing → warning + ownership finding. |
| `description` |  | str | v1 scoring. |
| `unit`, `grain` |  | str | v1 scoring. |
| `direction` |  | enum | `higher_is_better` \| `lower_is_better`. Informational. |
| `linked_okrs` |  | [str] | OKR ids; must resolve. |
| `linked_decisions` |  | [str] | Decision ids; must resolve. |
| `depends_on` |  | [str] | Instrumentation ids; must resolve when `instrumentation` present. |
| `sql` |  | map | `value:` or `numerator:`+`denominator:`. v1 scoring. |
| `tests` |  | [map] | v1 scoring. |
| `known_limitations` |  | [str] | Informational. |
| `interpretation_notes` |  | [str] | Informational. |

A metric **linked to nothing** (`linked_okrs`, `linked_decisions` both empty/absent) is an **orphan** → decision-linkage debt. A metric linked to an OKR but to no decision is a softer "OKR-linked but not operationalized" finding.

### `decisions` (L2+) — the central object

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Unique. |
| `question` | ✓ | str | The recurring decision. |
| `owner` |  | str | Missing → ownership finding. |
| `cadence` |  | str | e.g. `weekly during rollout`. |
| `decision_type` |  | enum | Drives risk classification (§ Risk-bearing). |
| `required_metrics` |  | [str] | Metric ids; **must resolve**. A missing ref makes the decision *Not ready*. |
| `guardrails` |  | [str] | Metric ids; must resolve. |
| `action_thresholds` |  | [map] | `{condition, action}` free text. **Display-only — never validated or scored.** |

### `instrumentation` (L3)

```yaml
instrumentation:
  - id: setup_completed_event
    status: complete            # complete | partial | missing
    description: First-value event tracking.
```

Referenced by `metrics[].depends_on`. `partial`/`missing` feeds instrumentation-readiness scoring and derives instrumentation debt.

### `operating_model` (L3)

| Field | Req | Type | Notes |
|---|---|---|---|
| `review_cadence` |  | str | Evidence for operating rhythm. |
| `primary_forum` |  | str | |
| `decision_log_exists` |  | bool | Evidence field (weighted above declarations, PRD P4). |
| `last_reviewed` |  | date/null | `null` is valid and means "no evidence". |

### `measurement_debt` (L3, authored — mostly you won't need it)

**Most debt is derived from the graph** (see methodology § Debt). You author an item here **only for what the graph cannot see** — e.g., "this event fires inconsistently on one path."

```yaml
measurement_debt:
  - id: query_understanding_not_instrumented
    type: instrumentation        # definition|ownership|instrumentation|testing|
                                 # decision_linkage|strategy_linkage|operating_rhythm
    severity: high               # low|medium|high|critical
    description: A planned relevance metric has no instrumentation source yet.
    affected_metrics: []
    affected_decisions: [ship_search_ranking_change]
    recommended_fix: Instrument query-understanding signal before gating ranking changes.
```

Authored debt **never lowers a dimension below what derived debt already implies** — honest disclosure must not score worse than silence (PRD P4).

### `internal_references` (private packs only)

```yaml
internal_references:
  dashboard_url: null
  metric_catalog_url: null
  dbt_model: null
  source_table: null
```

Tolerated by the parser, ignored by scoring. **A committed `examples/` pack with any non-null value here fails CI** (PRD §15). Public sample packs keep these `null` or omit the block.

---

## Cross-reference integrity

The validator resolves every id reference and flags breaks (PRD FR2/FR3/FR5):

- `metrics[].linked_okrs` → `okrs[].id`
- `metrics[].linked_decisions` → `decisions[].id`
- `metrics[].depends_on` → `instrumentation[].id`
- `okrs[].key_results[].linked_metrics` → `metrics[].id`
- `decisions[].required_metrics` / `guardrails` → `metrics[].id`
- `strategy.vertical_outcomes[].linked_company_goals` → `strategy.company_goals[].id`
- `measurement_debt[].affected_metrics` / `affected_decisions` → respective ids

Duplicate ids within any collection are errors.

---

## Minimal valid packs

**L0 (equivalent to a v1 pack):**

```yaml
pack: { id: p, name: P, schema_version: "2.0", visibility: public_sample }
metrics:
  - { id: m1, name: My Metric, tier: V1, accountable: Team, description: "...",
      unit: percent, grain: account, sql: { value: "SELECT 1" }, tests: [{type: not_null}] }
```

**Full L3 examples:** see [`examples/onboarding_measurement_ready.yaml`](../examples/onboarding_measurement_ready.yaml), [`collaboration_portfolio_design.yaml`](../examples/collaboration_portfolio_design.yaml), [`search_decision_gap.yaml`](../examples/search_decision_gap.yaml).
