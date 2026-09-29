# PRD: MetricReady v2, product measurement readiness

Status: draft. Version 2.0-draft. Replaces v1 (metric-pack auditor).

## 1. Naming

One product, one name, one tagline.

- Repo: `measurement-maturity-framework` (unchanged).
- Product and app: MetricReady (unchanged).
- Concept: product measurement readiness.

Tagline:

> MetricReady checks whether a product area's measurement system is ready to support recurring decisions, not just whether individual metrics are well defined.

No third name appears anywhere in the product, docs or UI.

## 2. Summary

v1 asks whether one metric is structurally ready. It validates a metric pack, scores definition maturity and suggests the next fix. That logic is defended with evidence (a Bayesian weight-sensitivity study and a calibration study) and stays.

v2 asks a bigger question: can this product area use its measurement system to make reliable recurring decisions?

It models a product vertical as a measurement graph (metrics, the decisions they feed, the OKRs they ladder to, the guardrails that protect them, the instrumentation they depend on, the owners and rhythm that keep them alive) and reasons over that graph. The headline is how many of the vertical's key decisions are backed by trusted, owned, instrumented, guardrailed metrics.

v2 has two uses by design:

- The public repo is an org-agnostic engine plus sample packs.
- A private deployment maps a real organization's OKRs, KPIs, dashboards and metric definitions into the same schema, using local packs that never enter the public repo.

The same code runs both. No company-specific logic, names or data live in the public repo.

## 3. What v1 misses, and what stays

Stays:

- Metric-level scoring and its deductions (`mmf/scoring.py`, `mmf/config.py`).
- The validator's structural checks (`mmf/validator.py`).
- Deterministic suggestions (`mmf/suggestions.py`).
- The Streamlit UI layer (`mmf/ui.py`, `components.py`, `layout.py`, `sidebar.py`, `theme.css`, `streamlit_compat.py`, `streamlit_mermaid.py`).
- The evidence: `analysis/` (robustness and calibration) and `case_studies/`. They give the project its credibility, and v2 extends them.

The gap: v1 stops at the metric. A vertical can have well-defined metrics and still be unable to support a decision, because no metric links to the decision, the guardrail is never reviewed, instrumentation is incomplete, or nobody owns the answer. v1 can't see any of that. v2 models the relationships, not only the nodes.

## 4. Design principles

Every later section must follow these.

### P1: count neutrality

Metric count is never a rating input. The framework doesn't score, rank or warn on how many OKRs, KPIs or metrics a vertical has. The schema has no min or max metric range, and no score has a count term.

The real concern that a portfolio can be hard to operate is expressed as a count of problems: orphaned metrics, metrics with no role, decisions with no metric, guardrails reviewed nowhere. Many metrics that are all role-clear and decision-linked score well; a few muddled ones score poorly.

Banned output language: too many KPIs, KPI overload, bad KPI design, fewer metrics, reduce metrics.
Preferred: portfolio focus, metric role clarity, decision linkage, operating complexity, measurement coverage, orphaned metric.

### P2: derive, don't declare

The value is graph analysis, not transcription. Anything that can be derived from structure is derived, never retyped by the author. An orphaned metric is detected, not declared. Free text is for facts the structure can't see (for example "this event fires incorrectly in one client").

### P3: honest scores over precise-looking ones

The headline is a decision-readiness fraction and an ordinal band, not a weighted number to two significant figures. Any 0 to 100 composite is optional, labelled directional, and must get the same robustness treatment v1 gave its deductions.

### P4: measures documentation, not behaviour, and says so

A static pack shows whether a measurement system is documented and structured to support decisions. It can't show whether decisions are actually made that way. The product claim is scoped to match, and evidence fields (`decision_log_exists`, `last_reviewed`) count more than declarations wherever both exist.

### P5: progressive disclosure

A pack with only metrics is valid and useful (it runs v1 logic). Each extra section unlocks more. Missing sections are reported as not assessed, never scored as zero. A half-mapped private vertical gives partial value, not forty broken-reference errors.

### P6: determinism and transparency

Same input, same output, with stable tie-breaks on every sort. Every score has a visible, documented driver. No hidden prompts, no LLM in scoring.

### P7: the public repo stays clean by control, not discipline

CI enforces that no company data reaches the public repo. Sample packs vary in size and structure so they read as illustrations, never as commentary on a real organization.

## 5. Goals and non-goals

Goals:

| # | Goal |
|---|---|
| G1 | Assess vertical-level measurement readiness from one pack, decisions first. |
| G2 | Keep the public repo org-agnostic and runnable with sample packs alone. |
| G3 | Support private, local-only packs that map real metrics into the schema with no public repo changes. |
| G4 | Assess portfolio design (role clarity, balance, decision linkage, operability) under P1, independent of count. |
| G5 | Produce leadership-ready outputs: decision map, debt summary, portfolio assessment, one-page brief, cross-vertical view. |
| G6 | Compare readiness patterns across verticals without a single-number leaderboard. |
| G7 | Keep the logic transparent, deterministic and documented (P6). |

Non-goals: a BI tool, semantic layer, dbt replacement, metric catalog, experimentation platform, dashboard generator, SQL engine, automated KPI selector or LLM metric judge. It doesn't auto-fix or auto-approve metrics. It supports product judgment and doesn't replace it.

## 6. Users and jobs

| User | Job |
|---|---|
| Senior, Staff or Principal Product Analyst (primary) | Check whether a product area has usable measurement, find definition and linkage gaps, map metrics to decisions, build an improvement plan. |
| Cross-vertical measurement owner, such as an Analytics or Measurement Lead (primary) | Owns measurement quality across several areas. Needs a consistent way to see where systems are strong or weak, spot shared gaps, prioritise enablement and standardise the conversation, without ranking teams. The cross-vertical view (section 13) is built for this role. |
| Product Lead or PM (secondary) | See which metrics are trusted, which decisions lack support, and how primary metrics differ from supporting, diagnostic and guardrail metrics. |

## 7. Core concept: the measurement graph

A vertical measurement pack describes one product area as a graph:

```text
company goals
   ▲
vertical outcomes ──▶ OKRs ──▶ key results
   ▲                              │
   │                       linked_metrics
   │                              ▼
decisions ──required_metrics──▶ metrics ──depends_on──▶ instrumentation
   │            guardrails ───────┘
   └── action thresholds (display-only)

measurement debt: mostly DERIVED from the graph; partly authored for what the graph can't see
```

Readiness is worked out over this graph. The central object is the decision, because a measurement system exists to serve decisions. A vertical is ready to the extent each key decision is backed by trusted, owned, instrumented, guardrailed metrics.

## 8. Schema (progressive levels)

`schema_version: "2.0"`. Routing is the single source of truth: `"1.0"` goes to the v1 path, `"2.0"` to v2, anything else gets a clear warning and a best-effort v1 path. Existing v1 packs and fixtures must keep passing unchanged.

| Level | Sections | Unlocks |
|---|---|---|
| L0 | `metrics` only | v1 metric readiness |
| L1 | plus `metrics[].role`, `strategy`, `okrs` | Portfolio role clarity, OKR/strategy linkage |
| L2 | plus `decisions` | Decision map, decision-readiness rollup |
| L3 | plus `instrumentation`, `operating_model`, authored `measurement_debt` | Instrumentation readiness, operating rhythm, full brief |

Each level is valid on its own. Lower levels report the rest as not assessed.

Example pack (org-agnostic, and deliberately not 6 KPIs):

```yaml
pack:
  id: onboarding_measurement_readiness
  name: Onboarding Measurement Readiness Pack
  version: 0.1.0
  schema_version: "2.0"
  visibility: public_sample        # public_sample | private (validated, see section 15)

vertical:
  id: onboarding
  name: Onboarding
  description: Example area focused on getting new accounts to first value.
  lifecycle_stage: scaling
  owner: Onboarding Product Team

strategy:
  company_goals:
    - { id: retention, name: Customer Retention }
  vertical_outcomes:
    - id: faster_first_value
      name: Get new accounts to first value faster
      linked_company_goals: [retention]

okrs:
  - id: onboarding_okr_1
    objective: Improve activation
    owner: Onboarding Product Team
    period: Example period
    key_results:
      - id: kr_activation
        description: Increase 14-day activation rate
        linked_metrics: [activation_rate]

# design_intent is free text and UNSCORED. There is no count range. (P1)
metric_portfolio:
  design_intent: Support the weekly onboarding review.

metrics:
  - id: activation_rate
    name: Activation Rate
    role: primary_metric              # see section 9
    tier: V1                          # v1 maturity tier, separate from role
    status: active
    accountable: Onboarding Product Team
    description: Share of new accounts reaching first value within 14 days.
    unit: percent
    grain: account
    direction: higher_is_better
    linked_okrs: [onboarding_okr_1]
    linked_decisions: [continue_new_onboarding]
    depends_on: [setup_completed_event]   # instrumentation ids
    sql:
      numerator: |
        SELECT COUNT(DISTINCT account_id) FROM setup_events
        WHERE event = 'first_value' AND days_since_signup <= 14
      denominator: |
        SELECT COUNT(DISTINCT account_id) FROM accounts
    tests: [{ type: not_null }, { type: range, field: value, min: 0, max: 100 }]
    interpretation_notes: [Read with support_contact_rate.]
  # ... a small, varied set, not a fixed canonical count

decisions:
  - id: continue_new_onboarding
    question: Should we continue rolling out the new onboarding flow?
    owner: Onboarding Product Lead
    cadence: weekly during rollout
    decision_type: rollout
    required_metrics: [activation_rate, support_contact_rate]
    guardrails: [support_contact_rate]
    action_thresholds:                # display only, never scored (P3/P6)
      - { condition: Activation up and guardrails stable, action: Continue }
      - { condition: Activation up but support contacts up, action: Pause and investigate }

instrumentation:
  - id: setup_completed_event
    status: partial                   # complete | partial | missing
    description: First-value event tracking is incomplete in the new flow.

operating_model:
  review_cadence: weekly
  primary_forum: Product performance review
  decision_log_exists: false          # evidence field (P4)
  last_reviewed: null

# Authored debt is ONLY for what the graph can't derive (P2). Most debt is derived.
measurement_debt:
  - id: first_value_event_gap
    type: instrumentation
    severity: medium
    description: First-value event fires inconsistently for one signup path.
    affected_metrics: [activation_rate]
    affected_decisions: [continue_new_onboarding]
    recommended_fix: Fix event before using this as a rollout gate.

# Private packs only: the parser accepts it, CI rejects it in public (section 15)
internal_references:
  dashboard_url: null
  dbt_model: null
  source_table: null
```

Every v2 section except `metrics` is optional. Missing optional fields never crash; they turn a dimension into not assessed.

## 9. Metric roles

Each metric has exactly one role. Roles are separate from v1 `tier` (maturity) and from the readiness score (definition quality). The schema documents all three so they never get mixed up.

Roles in v2 (only those the evaluator uses):

| Role | Meaning |
|---|---|
| `primary_metric` | The main success measure for the area or decision |
| `supporting_metric` | Explains movement in a primary metric |
| `diagnostic_metric` | Investigation, segmentation, root cause |
| `guardrail_metric` | Protects against harmful optimisation |
| `input_metric` / `output_metric` | Behaviour expected to drive outcomes vs the outcome itself. Used by the balance check (section 10). |

`health_metric` waits until a check uses it. Roles the evaluator ignores don't ship.

## 10. Portfolio design assessment (independent of count)

Checks whether the metric set is understandable, role-clear, balanced, decision-linked and operable. Everything is derived and nothing counts metrics (P1, P2).

| Signal | Check |
|---|---|
| Role clarity | Every metric has a role, and each decision context has at least one `primary_metric`. |
| Decision/OKR linkage | Each metric links to at least one decision, OKR or explicit diagnostic use. |
| Orphans | Metrics linked to nothing. This is the operating-complexity signal: a count of orphans, never of metrics. |
| Balance | Input vs output roles and guardrails exist where decisions carry real risk. |
| Possible duplication | Metrics sharing grain, direction and a near-identical definition, flagged neutrally as "may measure the same concept", never as "too many". |

The output is a band plus specific, blameless findings, for example:

> Portfolio design: Partial. Primary outcome is clear and guardrails exist. 2 metrics are not linked to a recurring decision; classify their role and map each to a decision or a diagnostic use.

No sentence mentions how many metrics exist.

## 11. Scoring model

### Layer 1: metric readiness (kept)

Unchanged from v1: 0 to 100 per metric via the existing deductions and `pack_floor_weight`. v2 metrics use the same logic.

### Layer 2: vertical readiness (new, decision-centric)

Built bottom-up, not as an 11-axis weighted average.

Step 1, decision readiness. Each decision gets a status from its graph:

| Status | When |
|---|---|
| Ready | All `required_metrics` exist, each is trusted (Layer 1 score at or above the caution threshold) and owned, guardrails exist where the decision type implies risk, and no blocking (`high`/`critical`) instrumentation or definition debt sits on the path. |
| Usable with caution | Minor gaps, for example a supporting metric below threshold, or a guardrail that exists but isn't reviewed. |
| Not ready | A required metric is missing or untrusted, or blocking debt sits on the path. |

Step 2, headline: "N of M key decisions are decision-ready." It counts decisions, which P1 allows.

Step 3, dimension profile: eight dimensions, each an ordinal band (`Strong`, `Partial`, `Weak`, `Not assessed`) with an explicit field-level driver. No equal-weight 0 to 5 average.

| # | Dimension | Derived from |
|---|---|---|
| 1 | Decision coverage & linkage | The decisions to required_metrics graph; orphaned decisions and metrics |
| 2 | Metric definition quality | Rollup of Layer 1 scores |
| 3 | Portfolio role clarity | Section 10 |
| 4 | Guardrail coverage | Risk-bearing decisions with or without guardrails |
| 5 | Instrumentation readiness | `instrumentation[].status` and instrumentation debt severity |
| 6 | Ownership clarity | Metrics and decisions with `accountable` or `owner` |
| 7 | Operating rhythm | `review_cadence`, `last_reviewed`, `decision_log_exists` (evidence, P4) |
| 8 | Strategy / OKR linkage | Metrics to OKRs to vertical_outcomes to company_goals |

Step 4, overall band: a rule-based map from the decision-ready fraction and the dimension profile to one of four bands. The names differ from the metric-level bands to avoid confusion:

| Vertical band | Meaning |
|---|---|
| Decision-ready | Key decisions are backed by trusted, owned, instrumented metrics |
| Usable with caution | Most decisions are supported; specific, named gaps remain |
| Fragile | Several decisions lack trusted or instrumented metrics |
| Not ready for recurring decisions | Core decision support is missing |

Optional and experimental: one 0 to 100 composite may appear behind a "directional" label, only once it has a robustness check (section 17). It is never the headline.

There is no measurement-debt dimension. It would double count and penalise honest disclosure (P4). Debt feeds dimensions 1, 4 and 5 as evidence.

## 12. Measurement debt (mostly derived)

Types: `definition`, `ownership`, `instrumentation`, `testing`, `decision_linkage`, `strategy_linkage`, `operating_rhythm`. Severity: `low`, `medium`, `high`, `critical`.

Derived debt (the default, P2):

| Condition | Debt type |
|---|---|
| Orphaned metric | `decision_linkage` |
| Metric with no SQL | `definition` |
| Metric with no owner | `ownership` |
| `instrumentation.status != complete` | `instrumentation` |
| Guardrail in no reviewed forum | `operating_rhythm` |
| OKR with no metric | `strategy_linkage` |

Authored debt covers only what the graph can't see. It never lowers a dimension below what derived debt already implies: disclosing a problem you have must not score worse than hiding it (P4).

Output: grouped by type, sorted by severity with a stable secondary sort on id (P6), each item linked to affected metrics and decisions with a recommended fix. The top 3 appear in the brief.

## 13. Cross-vertical view

Loads several private packs locally and compares them by pattern, never as a leaderboard (P1, G6).

It shows:

- A matrix of verticals by the eight dimensions, each cell a band, not a number.
- Shared gaps: dimensions or debt types that are `Weak` or `Partial` across many verticals. This is the signal for prioritising enablement (for example "instrumentation readiness is the most common weak dimension").
- Decision-support coverage: which decision types most often lack trusted metrics.

It never shows a single 0 to 100 score per vertical ranked top to bottom, or any best/worst framing.

A cross-vertical measurement owner uses this to standardise the conversation and target enablement without ranking teams. It is private-only and read-only over local packs, and no sample comparison data ships in the public repo.

## 14. App experience

Sections (v2 packs unlock the new ones; v1 packs show only the v1 set):

1. Upload or select a sample pack
2. Vertical overview
3. Strategy and OKRs, then the metric portfolio
4. Vertical readiness (fraction, dimension profile, band)
5. Metric readiness table (Layer 1)
6. Decision map
7. Measurement debt
8. One-page brief
9. Export
10. Cross-vertical view (only with several local packs loaded)

Behaviour: detect the schema version and route; run v1 logic for v1 packs and hide v2 sections; show validation warnings clearly; handle missing optional sections (show not assessed); support local private packs; offer downloads.

The brief and portfolio text are filled from templates using structured findings (P6). They are formulaic on purpose, not generated narrative, which keeps determinism honest and avoids drifting toward an LLM path.

## 15. Public and private use, and leak prevention

Public repo: engine and sample packs only. Every committed pack has `visibility: public_sample` and no non-null `internal_references`.

Private use: local packs in a git-ignored path (for example `private_packs/`), with `visibility: private` and optionally filled `internal_references` and real metric definitions. The parser accepts these fields and scoring ignores them.

Leak prevention is a control, not a convention (P7):

- `.gitignore` excludes `private_packs/`.
- A validator rule and a CI check fail the build if any committed pack in `examples/` has `visibility: private` or any non-null `internal_references.*`.
- The CI check runs in the existing `.github/workflows`.

That makes "no company data in public" something the repo can prove, which shows the same discipline the framework is about.

## 16. Sample packs

Three packs, deliberately different in size and shape so none looks like a real org's fingerprint (P7). Domains are generic SaaS areas.

| Pack | Domain | Shape | Shows |
|---|---|---|---|
| `onboarding_measurement_ready.yaml` | Onboarding | ~4 metrics, 1 OKR, 2 decisions | A healthy, decision-ready system |
| `collaboration_portfolio_design.yaml` | Team collaboration | ~5 metrics, mixed roles, some orphans | Role clarity and linkage gaps, neutral findings |
| `search_decision_gap.yaml` | Search and discovery | ~3 to 4 metrics, OKRs linked, weak decision links | Good definitions, weak decision model |

Counts vary between packs and none matches a "2 to 3 OKRs plus 6 KPIs" structure. No pack name, count or comment reads as commentary on any organization.

## 17. Validity and robustness

v1 earned credibility by defending its scoring with evidence. v2 matches that:

- Discriminant validity test (main, deterministic): the three sample packs must rank in the intended order (onboarding, then collaboration, then search, by overall band), and each pack's top derived debt item must be its designed weakness. It is a unit test, a README evidence point and the cheapest honest proof the score means something.
- Rollup stability: if the optional 0 to 100 composite ships, a sensitivity check in `analysis/` must show the band order holds under reasonable changes to dimension thresholds, like the existing Bayesian study.
- A v2 case study: one reconstruction of a known public measurement failure mapped onto the vertical model in `case_studies/`, showing what the decision map and debt view would and wouldn't have caught.

## 18. Functional requirements

| # | Requirement |
|---|---|
| FR1 | Schema routing. v1 packs validate and score unchanged; v2 packs unlock vertical analysis; unknown versions warn clearly; missing optional fields never crash. Acceptance: the v1 test suite stays green. |
| FR2 | Vertical validation. Missing vertical id is an error; missing name flagged; missing owner warned; broken cross-references and duplicate ids detected. |
| FR3 | OKR validation. Several KRs per OKR; KR to metric links validated; broken links flagged; unlinked OKRs flagged as info. |
| FR4 | Portfolio evaluator (P1). Identifies roles; flags missing roles, orphans (a count of orphans, never of metrics) and missing guardrails on risk-bearing decisions; detects possible duplicate concepts; uses only neutral language; has no count term. |
| FR5 | Decision map. Lists decisions with owner, cadence, type, required metrics and guardrails; flags missing metric references; links to affected debt; assigns a readiness status. |
| FR6 | Metric readiness. v1 scoring kept; v2 metrics use the same logic; drivers visible. |
| FR7 | Vertical readiness. Decision-ready fraction, eight dimension bands and an overall band, with explicit drivers per dimension and no falsely precise headline. |
| FR8 | Measurement debt. Derived from structure; authored debt merged without penalising disclosure; grouped by type; sorted by severity with a stable tie-break; linked to metrics and decisions; top 3 in the brief. |
| FR9 | One-page brief. Markdown with vertical name, overall band, decision-ready fraction, strengths, named risks and next actions; downloadable. |
| FR10 | Export. Validation as JSON, metric readiness as CSV, vertical profile as CSV, brief as Markdown. |
| FR11 | Cross-vertical. Loads several local packs; shows the dimension matrix and shared-gap summary; no single-number ranking. |
| FR12 | Leak guard. CI fails if a committed `examples/` pack is `visibility: private` or has non-null `internal_references`. |
| FR13 | Tests. v1 compatibility, v2 parsing, broken references, duplicate ids, missing roles, missing guardrails, decision map, debt derivation and sorting, vertical band, brief, discriminant-validity order, leak guard. |

## 19. Non-functional requirements

| # | Requirement |
|---|---|
| NFR1 | Transparency: all scoring rules documented in `docs/V2_SCORING_METHODOLOGY.md`. |
| NFR2 | Determinism: identical input gives identical output, including every sort. |
| NFR3 | Portability: works on generic YAML, with no dependency on private systems. |
| NFR4 | Local-first privacy: private packs work entirely locally; nothing is uploaded. |
| NFR5 | Maintainability: v2 modules are small and additive; v1 modules keep their behaviour. |
| NFR6 | Public readability: a hiring manager or senior IC understands the value, and the count-neutral stance, without running the app. |

## 20. File structure (changes to the current tree)

Written as keep, extend and add, so no working code is implied deleted.

```text
mmf/
  validator.py            KEEP      (v1 rules unchanged)
  scoring.py              KEEP      (Layer 1 unchanged)
  config.py               KEEP      (+ v2 thresholds appended)
  suggestions.py          KEEP
  mermaid.py              EXTEND    (strategy tree reads v2 strategy/okrs; see open Q)
  ui.py / components.py / layout.py / sidebar.py / theme.css
                          KEEP/EXTEND (new sections reuse existing helpers)
  streamlit_compat.py / streamlit_mermaid.py   KEEP
  bayesian_scoring.py     KEEP      (reused by section 17 rollup stability)
  schema.py               ADD       (version routing, single source of truth)
  vertical_validator.py   ADD
  vertical_scoring.py     ADD       (decision readiness + dimension bands)
  metric_portfolio.py     ADD       (count-independent, P1)
  decision_map.py         ADD
  measurement_debt.py     ADD       (derive-first, P2)
  brief.py                ADD       (template slot-fill)
  cross_vertical.py       ADD       (pattern compare, no leaderboard)

examples/                 ADD three v2 sample packs (section 16); keep v1 packs
templates/                ADD vertical_measurement_pack_template.yaml
docs/                     ADD V2_SCHEMA.md, V2_SCORING_METHODOLOGY.md, PRIVATE_USAGE_GUIDE.md
analysis/                 EXTEND  rollup stability check
case_studies/             EXTEND  one v2 case study
tests/                    ADD     test_* per FR13
.github/workflows/        EXTEND  leak guard (FR12)
```

`analysis/` and `case_studies/` are kept and extended. They are the repo's evidence.

## 21. Phasing and MVP

The original MVP was effectively every phase. This one front-loads the defensible features (and the judgment behind them, NFR6), not the flashiest.

MVP, in order:

1. v2 schema (progressive levels), `V2_SCHEMA.md` and the three sample packs (designed for the section 17 test).
2. Vertical validator and schema routing (FR1, FR2; the v1 suite stays green).
3. Decision map (FR5) and derived measurement debt (FR8), the outputs that set v2 apart.
4. Decision-readiness rollup, dimension bands and overall band (FR7), with the discriminant validity test (section 17).
5. One-page brief (FR9) and exports (FR10).
6. Leak guard and `PRIVATE_USAGE_GUIDE.md` (FR12).

Deferred on purpose:

- The optional 0 to 100 composite (only with section 17 robustness).
- The cross-vertical view (FR11), in a second release. It needs stable single-vertical output and real private packs to compare.
- Any LLM narrative, SQL execution, dashboard or database integration, org-specific adapters or weighting UI.

The flashiest feature, a single vertical score, is the least grounded and ships last or as experimental. The decision map and debt view carry the real insight and ship first.

First PR: schema, templates, the three sample packs, `V2_SCHEMA.md` and README positioning. No app or scoring changes yet. `V2_SCHEMA.md` is written as progressive levels, and the three packs differ in the ways the later validity test checks.

## 22. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Reads as commentary on a real org | P1 count neutrality (no count in scoring or language), varied sample shapes (section 16), org-agnostic PRD and README. Not judging count is itself the defence. |
| Score looks falsely precise | P3: fraction and bands as the headline; 0 to 100 optional and gated on robustness (section 17). |
| Honest debt disclosure penalised | P4: authored debt never scores worse than the derived baseline. |
| A half-filled pack feels punishing | P5: not assessed instead of zero; progressive levels. |
| Self-reported links overclaim usage | P4 scoping; evidence fields count more than declarations. |
| Cross-vertical view becomes a leaderboard | Section 13: patterns and bands only, no single-number ranking, private-only. |
| v1 code damaged in the overhaul | Section 20 keep/extend/add plan and FR1 acceptance (v1 suite green). |
| App grows too complex | UI built around five core outputs: decision map, portfolio, debt, brief, scorecard. |

## 23. Open questions

1. Strategy tree (`mmf/mermaid.py`): rebuild on v2 `strategy`/`okrs`, or keep v1 `strategy_board`/`impact_graph` as a separate optional input? Leaning: v2 replaces it, with a one-time mapping note in `V2_SCHEMA.md`.
2. Risk-bearing classification for guardrail coverage: infer from `decision_type`, or require an explicit `risk: true` flag? Leaning: infer, with an optional override.
3. Trusted-metric threshold for decision readiness: reuse the metric-level "usable with caution" cutoff, or set a higher bar for gating decisions? Leaning: a separate, higher bar.
4. Cross-vertical view in the public app (with a synthetic multi-pack demo), or private-only? Leaning: private-only, with a static screenshot in the docs for the public story.

## 24. Positioning (for the README)

> MetricReady checks whether a product area's measurement system is ready to support recurring decisions. v1 assesses individual metric quality. v2 assesses the system: which decisions are backed by trusted, owned, instrumented metrics, where the gaps are, and what to fix next.
>
> MetricReady does not judge whether a team has too many or too few metrics. It assesses whether the metric portfolio is structured well enough to support recurring product decisions.
