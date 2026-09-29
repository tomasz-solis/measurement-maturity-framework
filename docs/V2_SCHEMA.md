# V2 schema: vertical measurement pack

Status: draft. Schema version `"2.0"`. Related: [V2_SCORING_METHODOLOGY.md](V2_SCORING_METHODOLOGY.md), [PRD](PRD_v2_product_measurement_readiness.md).

A v2 pack describes one product vertical as a measurement graph: metrics, the decisions they feed, the OKRs they ladder to, the guardrails that protect them, the instrumentation they depend on, and the owners and rhythm that keep them alive. This doc defines the structure; the scoring rules are in the methodology doc.

## Version routing

`mmf/schema.py` reads `pack.schema_version` and routes the pack:

| `pack.schema_version` | Behaviour |
|---|---|
| `"1.0"` | v1 path, validated and scored as before. v2 sections ignored. |
| `"2.0"` | v2 path, full vertical analysis. |
| anything else, or missing | Clear warning, best-effort v1 path. |

A v1 pack is valid input; it just unlocks less. Existing v1 packs and fixtures must keep passing unchanged.

## Levels

A pack is useful at any level. Higher levels unlock more analysis. Missing sections are reported as not assessed, never scored as zero, so a partly mapped vertical gets partial value instead of dozens of broken-reference errors.

| Level | Add | Unlocks |
|---|---|---|
| L0 | `metrics` only | v1 metric readiness |
| L1 | `metrics[].role`, `strategy`, `okrs` | Portfolio role clarity, strategy/OKR linkage |
| L2 | `decisions` | Decision map, decision-readiness rollup, overall band |
| L3 | `instrumentation`, `operating_model`, authored `measurement_debt` | Instrumentation readiness, operating rhythm, full brief |

## Three separate properties

Three independent properties of a metric are easy to confuse. v2 keeps them apart:

| Property | Field | Question | Values |
|---|---|---|---|
| Maturity tier | `tier` | How stable is the definition? | `V0` (proxy) or `V1` (settled), as in v1 |
| Portfolio role | `role` | What job does the metric do? | `primary_metric`, `supporting_metric` and others (see Roles) |
| Definition quality | derived | Is it structurally ready? | The v1 readiness score, 0 to 100 |

A `V1` `primary_metric` scoring `100` and a `V0` `guardrail_metric` scoring `72` are independent facts on all three. Nothing in the schema or scoring treats them as one.

## Count neutrality (binding)

The schema has no field for an expected or target number of OKRs, KPIs or metrics, and no scoring rule reads metric count. `metric_portfolio.design_intent` is free text for the author and is never scored. Problems are counted (orphaned metrics, missing roles, unlinked decisions), never metrics. See the methodology doc and PRD section 4 (P1).

## Top-level sections

### `pack` (required)

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Unique pack id. |
| `name` | ✓ | str | Human name. |
| `version` |  | str | Pack version (roughly semver). |
| `schema_version` | ✓ | str | `"2.0"` for v2. Drives routing. |
| `visibility` | ✓ | enum | `public_sample` or `private`. Validated: a committed pack in `examples/` must be `public_sample`. |

### `vertical` (required at L1 and above)

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Vertical id. Missing is an error. |
| `name` | ✓ | str | Missing is an error. |
| `description` |  | str | |
| `lifecycle_stage` |  | enum | For example `exploring`, `scaling`, `mature`. Informational. |
| `owner` |  | str | Missing is a warning. |

### `strategy` (L1 and above)

```yaml
strategy:
  company_goals:
    - { id: retention, name: Customer Retention }
  vertical_outcomes:
    - id: faster_first_value
      name: Get new accounts to first value faster
      linked_company_goals: [retention]   # ids must resolve
```

### `okrs` (L1 and above)

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

- An OKR can have several key results.
- `linked_metrics` ids must resolve; broken links are flagged.
- An OKR with no resolvable metric is flagged as strategy-linkage debt (informational).

### `metric_portfolio` (optional, L1 and above)

| Field | Req | Type | Notes |
|---|---|---|---|
| `design_intent` |  | str | Free text. Not scored. There are no count fields. |

### `metrics` (required at every level)

The v1 metric plus v2 graph fields. All v1 scoring fields behave the same.

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Unique. |
| `name` | ✓ | str | |
| `role` | L1+ | enum | Portfolio role (see Roles). Missing is a role-clarity finding. |
| `tier` |  | enum | `V0` or `V1`. v1 scoring. |
| `status` |  | str | Defaults to `active`. |
| `accountable` / `responsible` |  | str | Either counts as an owner. Missing is a warning and an ownership finding. |
| `description` |  | str | v1 scoring. |
| `unit`, `grain` |  | str | v1 scoring. |
| `direction` |  | enum | `higher_is_better` or `lower_is_better`. Informational. |
| `linked_okrs` |  | [str] | OKR ids; must resolve. |
| `linked_decisions` |  | [str] | Decision ids; must resolve. |
| `depends_on` |  | [str] | Instrumentation ids; must resolve when `instrumentation` exists. |
| `sql` |  | map | `value:`, or `numerator:` and `denominator:`. v1 scoring. |
| `tests` |  | [map] | v1 scoring. |
| `known_limitations` |  | [str] | Informational. |
| `interpretation_notes` |  | [str] | Informational. |

A metric linked to nothing (`linked_okrs` and `linked_decisions` both empty or absent) is an orphan and creates decision-linkage debt. A metric linked to an OKR but no decision gets a softer "OKR-linked but not used in a decision" finding.

### `decisions` (L2 and above): the central object

| Field | Req | Type | Notes |
|---|---|---|---|
| `id` | ✓ | str | Unique. |
| `question` | ✓ | str | The recurring decision. |
| `owner` |  | str | Missing is an ownership finding. |
| `cadence` |  | str | For example `weekly during rollout`. |
| `decision_type` |  | enum | Sets risk classification (see Risk-bearing). |
| `required_metrics` |  | [str] | Metric ids; must resolve. A missing ref makes the decision Not ready. |
| `guardrails` |  | [str] | Metric ids; must resolve. |
| `action_thresholds` |  | [map] | `{condition, action}` free text. Display only, never validated or scored. |

### `instrumentation` (L3)

```yaml
instrumentation:
  - id: setup_completed_event
    status: complete            # complete | partial | missing
    description: First-value event tracking.
```

Referenced by `metrics[].depends_on`. `partial` or `missing` feeds instrumentation-readiness scoring and creates instrumentation debt.

### `operating_model` (L3)

| Field | Req | Type | Notes |
|---|---|---|---|
| `review_cadence` |  | str | Evidence for operating rhythm. |
| `primary_forum` |  | str | |
| `decision_log_exists` |  | bool | Evidence field, counts more than declarations (PRD P4). |
| `last_reviewed` |  | date/null | `null` is valid and means no evidence. |

### `measurement_debt` (L3, authored; usually not needed)

Most debt is derived from the graph (see the methodology's debt section). Add an item here only for what the graph can't see, for example "this event fires inconsistently on one path".

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

Authored debt never lowers a dimension below what derived debt already implies. Honest disclosure must never score worse than silence (PRD P4).

### `internal_references` (private packs only)

```yaml
internal_references:
  dashboard_url: null
  metric_catalog_url: null
  dbt_model: null
  source_table: null
```

The parser accepts it and scoring ignores it. A committed `examples/` pack with any non-null value here fails CI (PRD section 15). Public sample packs keep these `null` or leave the block out.

## Cross-reference checks

The validator resolves every id reference and flags breaks (PRD FR2, FR3, FR5):

| From | To |
|---|---|
| `metrics[].linked_okrs` | `okrs[].id` |
| `metrics[].linked_decisions` | `decisions[].id` |
| `metrics[].depends_on` | `instrumentation[].id` |
| `okrs[].key_results[].linked_metrics` | `metrics[].id` |
| `decisions[].required_metrics` / `guardrails` | `metrics[].id` |
| `strategy.vertical_outcomes[].linked_company_goals` | `strategy.company_goals[].id` |
| `measurement_debt[].affected_metrics` / `affected_decisions` | the matching ids |

Duplicate ids in any collection are errors.

## Minimal valid packs

L0 (same as a v1 pack):

```yaml
pack: { id: p, name: P, schema_version: "2.0", visibility: public_sample }
metrics:
  - { id: m1, name: My Metric, tier: V1, accountable: Team, description: "...",
      unit: percent, grain: account, sql: { value: "SELECT 1" }, tests: [{type: not_null}] }
```

Full L3 examples: [`examples/onboarding_measurement_ready.yaml`](../examples/onboarding_measurement_ready.yaml), [`collaboration_portfolio_design.yaml`](../examples/collaboration_portfolio_design.yaml), [`search_decision_gap.yaml`](../examples/search_decision_gap.yaml).
