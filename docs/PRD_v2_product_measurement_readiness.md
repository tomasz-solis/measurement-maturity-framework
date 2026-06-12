# PRD — MetricReady v2: Product Measurement Readiness

Status: Draft
Version: 2.0-draft
Supersedes: v1 (metric-pack auditor)

---

## 1. Naming

One product, one name, one tagline.

- Repo: `measurement-maturity-framework` (unchanged).
- Product / app: **MetricReady** (unchanged).
- Concept: *product measurement readiness*.

Tagline:

> MetricReady checks whether a product area's measurement system is ready to support recurring decisions — not just whether individual metrics are well defined.

No third name is introduced anywhere in the product, docs, or UI.

---

## 2. Summary

v1 answers: *is this individual metric structurally ready?* It validates a metric pack, scores definition maturity, and suggests the next fix. That logic is empirically defended (Bayesian weight-sensitivity and a calibration study) and stays intact.

v2 answers a larger question: *can this product area use its measurement system to make reliable recurring decisions?*

v2 does this by modelling a product vertical as a **measurement graph** — metrics, the decisions they feed, the OKRs they ladder to, the guardrails that protect them, the instrumentation they depend on, and the ownership and rhythm that keep them alive — and then reasoning over that graph. The headline result is decision-centric: *how many of this vertical's key decisions are backed by trusted, owned, instrumented, guardrailed metrics.*

v2 is **dual-use by design**:

- The public repo is a fully org-agnostic engine plus illustrative sample packs.
- A private deployment maps a real organization's existing OKRs, KPIs, dashboards, and metric definitions into the same schema using local packs that never enter the public repo.

The same code runs both. No company-specific logic, names, or data live in the public repo.

---

## 3. What's wrong with v1 for this job (and what we keep)

Keep:

- Metric-level readiness scoring and its deductions (`mmf/scoring.py`, `mmf/config.py`).
- The validator's structural checks (`mmf/validator.py`).
- Deterministic suggestions (`mmf/suggestions.py`).
- The Streamlit UI layer (`mmf/ui.py`, `components.py`, `layout.py`, `sidebar.py`, `theme.css`, `streamlit_compat.py`, `streamlit_mermaid.py`).
- The evidence assets: `analysis/` (robustness + calibration) and `case_studies/`. These are the credibility of the project and v2 **extends** them; it does not orphan them.

Gap v2 closes: v1 stops at the metric. A vertical can have a set of well-defined metrics and still be unable to support a decision — because no metric is linked to the decision, the guardrail is never reviewed, the instrumentation is incomplete, or nobody owns the answer. v1 cannot see any of that. v2 models the relationships, not just the nodes.

---

## 4. Design principles (the spine)

These are non-negotiable and every later section must conform to them.

### P1 — Count neutrality

Metric count is **never** a rating input. The framework does not score, rank, or warn on the number of OKRs, KPIs, or metrics a vertical has. There is no `min`/`max` metric range in the schema and no count term in any score.

The legitimate concern that "a portfolio can be hard to operate" is expressed as **count of problems, not count of metrics**: orphaned metrics, metrics with no role, decisions with no metric, guardrails reviewed nowhere. A vertical with many metrics that are all role-clear and decision-linked scores well; a vertical with few muddled ones scores poorly.

Banned output language: *too many KPIs, KPI overload, bad KPI design, fewer metrics, reduce metrics.*
Preferred output language: *portfolio focus, metric role clarity, decision linkage, operating complexity, measurement coverage, orphaned metric.*

### P2 — Derive, don't declare

The framework's value is graph analysis, not transcription. Wherever a finding can be **derived** from structure, it is derived — never re-typed by the author. An orphaned metric is detected, not declared. Authored free-text is reserved for facts the structure cannot see (e.g., "this event fires incorrectly in one client").

### P3 — Honest scoring over precise-looking scoring

The headline is a **decision-readiness fraction** and an ordinal **band**, not a weighted two-significant-figure number. Any 0–100 composite is optional, labelled directional, and must ship with the same robustness treatment v1 gave its deductions. We do not regress on the rigor v1 established.

### P4 — Measures documentation, not behavior — and says so

A static pack reveals whether a measurement system is *documented and structured* to support decisions. It cannot observe whether decisions are actually made that way. The product claim is scoped accordingly, and evidence fields (`decision_log_exists`, `last_reviewed`) are weighted above declaration fields wherever both exist.

### P5 — Progressive disclosure

A pack containing only metrics is valid and useful (it runs v1 logic). Each additional section unlocks more analysis. Absent sections are reported as **not assessed**, never penalized as zero. A half-mapped private vertical produces partial value, not forty broken-reference errors.

### P6 — Determinism and transparency

Same input → same output, including stable tie-breaks on every sort. Every score has a visible, documented driver. No hidden prompts, no LLM in the scoring path.

### P7 — Public stays clean by control, not by discipline

No company data reaches the public repo because CI enforces it, not because someone remembered. Sample packs are deliberately varied in size and structure so they read as illustrative, never as commentary on any real organization.

---

## 5. Goals and non-goals

### Goals

- G1. Assess vertical-level measurement readiness from a single pack, decision-first.
- G2. Keep the public repo fully org-agnostic and runnable with sample packs alone.
- G3. Support private, local-only packs that map real metrics into the schema with zero changes to the public repo.
- G4. Assess metric-portfolio *design* (role clarity, balance, decision linkage, operability) under P1 — count-independent.
- G5. Produce leadership-ready outputs: decision map, debt summary, portfolio assessment, one-page brief, and a cross-vertical view.
- G6. Compare measurement readiness *patterns* across multiple verticals without producing a single-number leaderboard.
- G7. Preserve transparent, deterministic, documented logic (P6).

### Non-goals

Not a BI tool, semantic layer, dbt replacement, metric catalog, experimentation platform, dashboard generator, SQL execution engine, automated KPI selector, or LLM metric judge. Not a system that auto-fixes or auto-approves metrics. It supports product judgment; it does not replace it.

---

## 6. Users and jobs

### Primary — Senior / Staff / Principal Product Analyst

Assess whether a product area has usable measurement; find definition and linkage gaps; map metrics to decisions; build an improvement plan.

### Primary — Cross-vertical measurement owner (Analytics Lead / Measurement Lead)

Owns measurement quality across several product areas. Needs a consistent way to: see where measurement systems are strong or weak, spot gaps shared across verticals, prioritize enablement work, and standardize how measurement quality is discussed — **without** ranking teams against each other. This is the role v2's cross-vertical view (§13) is built for.

### Secondary — Product Lead / PM

Understand which metrics are trusted, which decisions are unsupported, and how primary metrics differ from supporting, diagnostic, and guardrail metrics.

---

## 7. Core concept: the measurement graph

A **vertical measurement pack** describes one product area as a graph:

```
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

Readiness is reasoned over this graph. The central object is the **decision**, because a measurement system exists to serve decisions. A vertical is measurement-ready to the extent each of its key decisions is backed by trusted, owned, instrumented, guardrailed metrics.

---

## 8. Schema (progressive levels)

`schema_version: "2.0"`. Routing is the single source of truth: `pack.schema_version == "1.0"` → v1 path; `== "2.0"` → v2 path; anything else → clear warning and best-effort v1 path. Existing v1 packs and fixtures must continue to pass unchanged.

### Progressive levels (P5)

| Level | Sections present | Unlocks |
|---|---|---|
| L0 | `metrics` only | v1 metric readiness (unchanged) |
| L1 | + `metrics[].role`, `strategy`, `okrs` | portfolio role clarity, OKR/strategy linkage |
| L2 | + `decisions` | decision map, decision-readiness rollup |
| L3 | + `instrumentation`, `operating_model`, authored `measurement_debt` | instrumentation readiness, operating rhythm, full brief |

Each level is independently valid. Higher levels enable more dimensions; lower levels report the rest as *not assessed*.

### Example pack (illustrative, org-agnostic — deliberately not 6 KPIs)

```yaml
pack:
  id: onboarding_measurement_readiness
  name: Onboarding Measurement Readiness Pack
  version: 0.1.0
  schema_version: "2.0"
  visibility: public_sample        # public_sample | private — validated, see §15

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

# design_intent is free-text and UNSCORED. There is no count range. (P1)
metric_portfolio:
  design_intent: Support the weekly onboarding review.

metrics:
  - id: activation_rate
    name: Activation Rate
    role: primary_metric              # see §9
    tier: V1                          # v1 maturity tier — orthogonal to role
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
  # ... a small, varied set — not a fixed canonical count

decisions:
  - id: continue_new_onboarding
    question: Should we continue rolling out the new onboarding flow?
    owner: Onboarding Product Lead
    cadence: weekly during rollout
    decision_type: rollout
    required_metrics: [activation_rate, support_contact_rate]
    guardrails: [support_contact_rate]
    action_thresholds:                # display-only, never scored (P3/P6)
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

# Private packs only — tolerated by the parser, rejected in public by CI (§15)
internal_references:
  dashboard_url: null
  dbt_model: null
  source_table: null
```

All v2 sections except `metrics` are optional. Missing optional fields never crash; they downgrade a dimension to *not assessed*.

---

## 9. Metric roles

Each metric has exactly one role. Roles are **orthogonal to v1 `tier`** (maturity) and to the metric-readiness score (definition quality). The schema documents all three axes explicitly so they are never conflated.

Roles shipped in v2 (only those actually used by the evaluator):

- `primary_metric` — the main success measure for the area or decision.
- `supporting_metric` — explains movement in a primary metric.
- `diagnostic_metric` — investigation / segmentation / root cause.
- `guardrail_metric` — protects against harmful optimization.
- `input_metric` / `output_metric` — behavior expected to drive outcomes vs. resulting outcome. Used by the input/output balance check (§10).

`health_metric` is **deferred** until a check uses it; we do not ship roles the evaluator ignores.

---

## 10. Portfolio design assessment (count-independent)

Assesses whether the metric set is understandable, role-clear, balanced, decision-linked, and operable — **all derived, none count-based** (P1, P2).

Derived signals:

- Role clarity: every metric has a role; at least one `primary_metric` is identifiable per decision context.
- Decision/OKR linkage: each metric links to at least one decision, OKR, or explicit diagnostic use.
- Orphans: metrics linked to nothing (the operating-complexity signal — *count of orphans*, never count of metrics).
- Balance: presence of input vs. output and guardrail roles where decisions carry material risk.
- Possible duplication: metrics that share grain + direction + near-identical definition (flagged neutrally as "may measure the same concept," never as "too many").

Output is a band plus specific, blameless findings, e.g.:

> Portfolio design: Partial. Primary outcome is clear and guardrails exist. 2 metrics are not linked to a recurring decision; classify their role and map each to a decision or a diagnostic use.

No sentence references how many metrics exist.

---

## 11. Scoring model

### Layer 1 — Metric readiness (preserved)

Unchanged from v1. Per-metric 0–100 via the existing deductions and `pack_floor_weight`. v2 metrics are scored by the same logic.

### Layer 2 — Vertical measurement readiness (new, decision-centric)

Built bottom-up, not as an 11-axis weighted average.

**Step 1 — Decision readiness.** For each decision, derive a status from its graph:

- `Ready`: all `required_metrics` exist, each is *trusted* (Layer-1 score ≥ caution threshold) and owned; guardrails present where the decision type implies risk; no blocking (`high`/`critical`) instrumentation or definition debt on the path.
- `Usable with caution`: minor gaps (e.g., a supporting metric below threshold, guardrail present but unreviewed).
- `Not ready`: a required metric missing/untrusted, or blocking debt on the path.

**Step 2 — Headline.** *N of M key decisions are decision-ready.* This is the primary number and it is count-of-decisions, which P1 permits (decisions, not metrics).

**Step 3 — Dimension profile.** Eight grounded dimensions, each reported as an ordinal band — `Strong / Partial / Weak / Not assessed` — with an explicit field-level driver. No equal-weight 0–5 average.

| # | Dimension | Derived from |
|---|---|---|
| 1 | Decision coverage & linkage | decisions ↔ required_metrics graph; orphaned decisions/metrics |
| 2 | Metric definition quality | rollup of Layer-1 scores |
| 3 | Portfolio role clarity | §10 |
| 4 | Guardrail coverage | risk-bearing decisions with/without guardrails |
| 5 | Instrumentation readiness | `instrumentation[].status` + instrumentation debt severity |
| 6 | Ownership clarity | metrics/decisions with `accountable`/`owner` |
| 7 | Operating rhythm | `review_cadence`, `last_reviewed`, `decision_log_exists` (evidence, P4) |
| 8 | Strategy / OKR linkage | metrics ↔ OKRs ↔ vertical_outcomes ↔ company_goals |

**Step 4 — Overall band.** A rules-based map from the decision-ready fraction and the dimension profile to one of four bands. The band vocabulary is **distinct from the metric-level bands** to avoid conflation:

| Vertical band | Meaning |
|---|---|
| Decision-ready | Key decisions are backed by trusted, owned, instrumented metrics |
| Usable with caution | Most decisions supported; specific, named gaps remain |
| Fragile | Several decisions lack trusted or instrumented metrics |
| Not ready for recurring decisions | Core decision support is missing |

**Optional, experimental:** a single 0–100 composite may be offered behind an explicit "directional" label, but only once it carries a robustness check (§17). It is never the headline.

There is no measurement-debt *dimension* (it would double-count and would penalize honest disclosure — P4). Debt instead informs dimensions 1, 4, and 5 as evidence.

---

## 12. Measurement debt (mostly derived)

Debt types: `definition`, `ownership`, `instrumentation`, `testing`, `decision_linkage`, `strategy_linkage`, `operating_rhythm`. Severity: `low | medium | high | critical`.

- **Derived debt** (default, P2): orphaned metric → `decision_linkage`; metric with no SQL → `definition`; metric with no owner → `ownership`; `instrumentation.status != complete` → `instrumentation`; guardrail in no reviewed forum → `operating_rhythm`; OKR with no metric → `strategy_linkage`.
- **Authored debt**: only for what the graph cannot see. Honest disclosure of authored debt never lowers a dimension band below what the derived debt already implies — disclosing a problem you already have must not score worse than hiding it (P4).

Output: grouped by type, sorted by severity with a stable secondary sort on id (P6), each item linked to affected metrics/decisions with a recommended fix. Top 3 surface in the brief.

---

## 13. Cross-vertical view (the role-prep capability)

Loads several private packs locally and compares them **by pattern, never by leaderboard** (P1, G6).

What it shows:

- A dimension-profile matrix: verticals × the eight dimensions, each cell a band (not a number).
- **Shared gaps**: dimensions or debt types that are `Weak`/`Partial` across many verticals — the enablement-prioritization signal (e.g., "instrumentation readiness is the most common weak dimension").
- **Decision-support coverage**: across verticals, which decision types most often lack trusted metrics.

What it deliberately does **not** show:

- A single 0–100 score per vertical ranked top-to-bottom.
- Any "best/worst vertical" framing.

This is the artifact a cross-vertical measurement owner uses to standardize the conversation and target enablement, without turning measurement quality into an inter-team ranking.

Cross-vertical is **private-only and read-only over local packs**; it never ships sample "comparison" data in the public repo.

---

## 14. App experience

Sections (v2 packs unlock the new ones; v1 packs show only the v1 set):

1. Upload / select sample pack
2. Vertical overview
3. Strategy & OKRs → metric portfolio
4. Vertical readiness (decision-ready fraction + dimension profile + band)
5. Metric readiness table (Layer 1)
6. Decision map
7. Measurement debt
8. One-page brief
9. Export
10. Cross-vertical view (only when multiple local packs are loaded)

Behavior: detect schema version and route; run v1 logic for v1 packs and hide v2 sections; show validation warnings clearly; tolerate missing optional sections (render *not assessed*); support local private packs; downloadable outputs.

The brief and portfolio prose are **template slot-filled from structured findings** (P6) — explicitly formulaic, not generated narrative. This keeps determinism honest and avoids drifting toward an LLM path.

---

## 15. Public / private dual-use and leak prevention

**Public repo:** engine + sample packs only. Every committed pack has `visibility: public_sample` and no non-null `internal_references`.

**Private use:** local packs under a git-ignored path (e.g., `private_packs/`), `visibility: private`, optionally populated `internal_references` and real metric definitions. The parser tolerates these fields; they are ignored by scoring.

**Leak prevention is a control, not a convention (P7):**

- `.gitignore` excludes `private_packs/`.
- A validator rule + a CI check fail the build if any committed pack under `examples/` has `visibility: private` or any non-null `internal_references.*`.
- The CI check is part of the existing `.github/workflows`.

This makes "no company data in public" a property the repo can prove, which is itself a demonstration of the discipline the framework is about.

---

## 16. Sample packs (org-agnostic, varied by design)

Three packs, deliberately different in size and shape so none reads as a real org's fingerprint (P7). Domains are generic SaaS areas, not finance-specific.

| Pack | Domain | Shape | Demonstrates |
|---|---|---|---|
| `onboarding_measurement_ready.yaml` | Onboarding | ~4 metrics, 1 OKR, 2 decisions | A healthy, decision-ready system |
| `collaboration_portfolio_design.yaml` | Team collaboration | ~5 metrics, mixed roles, some orphans | Role clarity + linkage gaps, neutral findings |
| `search_decision_gap.yaml` | Search / discovery | ~3–4 metrics, OKRs linked, weak decision links | Good definitions, weak decision model |

Counts vary across packs and none matches a "2–3 OKRs + 6 KPIs" structure. No pack name, count, or comment reads as commentary on any organization.

---

## 17. Validity and robustness (carry the v1 bar forward)

v1's credibility came from defending its scoring empirically. v2 matches that with:

- **Discriminant-validity test (primary, deterministic):** the three sample packs must rank in intended order (onboarding > collaboration > search on overall band), and each pack's top derived debt item must equal its designed weakness. This is a unit test, a README evidence point, and the cheapest honest proof the score means something.
- **Rollup stability:** if the optional 0–100 composite ships, a sensitivity check (in `analysis/`) must show the vertical band ordering is stable under reasonable variation in dimension thresholds — mirroring the existing Bayesian study.
- **A v2 case study:** extend `case_studies/` with one reconstruction of a known public measurement failure mapped onto the vertical model, showing what the decision map and debt view would and would not have caught.

---

## 18. Functional requirements

- **FR1 Schema routing.** v1 packs validate and score unchanged; v2 packs unlock vertical analysis; unknown versions warn clearly; missing optional fields never crash. (Acceptance: existing v1 test suite stays green.)
- **FR2 Vertical validation.** Missing vertical id flagged (error); missing name flagged; missing owner warned; invalid cross-references detected; duplicate ids detected.
- **FR3 OKR validation.** Multiple KRs supported; KR↔metric links validated; broken links flagged; unlinked OKRs flagged informationally.
- **FR4 Portfolio evaluator (P1).** Identifies roles; flags missing roles; flags orphans (count of orphans, never count of metrics); flags missing guardrails on risk-bearing decisions; detects possible duplicate concepts; emits only neutral language; contains no count term.
- **FR5 Decision map.** Lists decisions with owner, cadence, type, required metrics, guardrails; flags missing metric references; links to affected debt; assigns decision-readiness status.
- **FR6 Metric readiness.** v1 scoring preserved; v2 metrics scored by the same logic; drivers visible.
- **FR7 Vertical readiness.** Decision-ready fraction + eight dimension bands + overall band; explicit per-dimension drivers; no false-precision headline.
- **FR8 Measurement debt.** Derives debt from structure; merges authored debt without penalizing disclosure; groups by type; severity sort with stable tie-break; links to metrics/decisions; surfaces top 3 in the brief.
- **FR9 One-page brief.** Markdown: vertical name, overall band, decision-ready fraction, strengths, named risks, recommended next actions; downloadable.
- **FR10 Export.** Validation → JSON; metric readiness → CSV; vertical profile → CSV; brief → Markdown.
- **FR11 Cross-vertical.** Loads multiple local packs; renders dimension-profile matrix and shared-gap summary; emits no single-number ranking.
- **FR12 Leak guard.** CI fails if a committed `examples/` pack is `visibility: private` or has non-null `internal_references`.
- **FR13 Tests.** v1 compatibility; v2 parsing; broken references; duplicate ids; missing roles; missing guardrails; decision map; debt derivation + sorting; vertical band; brief; discriminant-validity ordering; leak guard.

---

## 19. Non-functional requirements

- NFR1 Transparency: all scoring rules documented in `docs/V2_SCORING_METHODOLOGY.md`.
- NFR2 Determinism: identical input → identical output, including all sorts.
- NFR3 Portability: works on generic YAML; no dependency on private systems.
- NFR4 Local-first privacy: private packs usable entirely locally; nothing uploaded externally.
- NFR5 Maintainability: v2 modules are additive and small; v1 modules unchanged in behavior.
- NFR6 Public readability: a hiring manager or senior IC understands the value, and the count-neutrality stance, without running the app.

---

## 20. File structure (diff over the current tree)

Expressed as keep / extend / add so no working code is implied-deleted.

```
mmf/
  validator.py            KEEP      (v1 rules unchanged)
  scoring.py              KEEP      (Layer 1 unchanged)
  config.py               KEEP      (+ v2 thresholds appended)
  suggestions.py          KEEP
  mermaid.py              EXTEND    (strategy tree reads v2 strategy/okrs; see open Q)
  ui.py / components.py / layout.py / sidebar.py / theme.css
                          KEEP/EXTEND (new sections reuse existing helpers)
  streamlit_compat.py / streamlit_mermaid.py   KEEP
  bayesian_scoring.py     KEEP      (reused by §17 rollup stability)
  schema.py               ADD       (version routing, single source of truth)
  vertical_validator.py   ADD
  vertical_scoring.py     ADD       (decision readiness + dimension bands)
  metric_portfolio.py     ADD       (count-independent, P1)
  decision_map.py         ADD
  measurement_debt.py     ADD       (derive-first, P2)
  brief.py                ADD       (template slot-fill)
  cross_vertical.py       ADD       (pattern compare, no leaderboard)

examples/                 ADD three v2 sample packs (§16); keep v1 packs
templates/                ADD vertical_measurement_pack_template.yaml
docs/                     ADD V2_SCHEMA.md, V2_SCORING_METHODOLOGY.md, PRIVATE_USAGE_GUIDE.md
analysis/                 EXTEND  rollup stability check
case_studies/             EXTEND  one v2 case study
tests/                    ADD     test_* per FR13
.github/workflows/        EXTEND  leak guard (FR12)
```

`analysis/` and `case_studies/` are explicitly retained and extended — they are the repo's evidence base.

---

## 21. Phasing and MVP

The original "MVP" was effectively all phases. This MVP is chosen to maximize demonstrated judgment (NFR6) and to front-load the *defensible* features, not the flashiest one.

**MVP (in order):**

1. v2 schema (progressive levels) + `V2_SCHEMA.md` + the three sample packs (designed for §17 discriminant testing).
2. Vertical validator + schema routing (FR1, FR2; v1 suite stays green).
3. Decision map (FR5) and derived measurement debt (FR8) — the differentiated outputs.
4. Decision-readiness rollup + dimension bands + overall band (FR7), with the discriminant-validity test (§17).
5. One-page brief (FR9) and exports (FR10).
6. Leak guard + `PRIVATE_USAGE_GUIDE.md` (FR12).

**Deliberately deferred:**

- The optional 0–100 composite (ship only with §17 robustness).
- Cross-vertical view (FR11) — second release; depends on stable single-vertical output and on having real private packs to compare.
- Any LLM narrative, SQL execution, dashboard/db integration, org-specific adapters, weighting UI.

The flashiest feature — a single vertical score — is the least grounded and ships last (or as experimental). The decision map and debt view carry the real insight and ship first.

**Recommended first PR (unchanged from the original instinct, refined):** schema + templates + three sample packs + `V2_SCHEMA.md` + README positioning. No app or scoring changes yet. `V2_SCHEMA.md` is written as progressive levels; the three packs differ in ways the later validity test asserts on.

---

## 22. Risks and mitigations

- **Reads as commentary on a real org.** → P1 count neutrality (no count anywhere in scoring or language) + §16 varied sample shapes + the org-agnostic PRD/README. The framework's stance is "we do not judge count," which is itself the defense.
- **Score looks falsely precise.** → P3: decision-ready fraction + bands as headline; 0–100 optional and gated on robustness (§17).
- **Honest debt disclosure penalized.** → P4: authored debt never scores worse than the derived baseline.
- **Pack feels punishing when half-filled.** → P5: not-assessed instead of zero; progressive levels.
- **Self-reported links overclaim usage.** → P4 scoping + evidence fields weighted above declarations.
- **Cross-vertical view becomes a leaderboard.** → §13 hard constraint: patterns and bands only, no single-number ranking, private-only.
- **Working v1 code damaged in the overhaul.** → §20 keep/extend/add diff + FR1 acceptance (v1 suite green).
- **App grows too complex.** → UI organized around five core outputs: decision map, portfolio, debt, brief, scorecard.

---

## 23. Open questions (genuinely open)

1. Strategy tree (`mmf/mermaid.py`): rebuild on v2 `strategy`/`okrs`, or keep v1 `strategy_board`/`impact_graph` as a separate optional input? (Leaning: v2 model supersedes; provide a one-time mapping note in `V2_SCHEMA.md`.)
2. Decision "risk-bearing" classification for guardrail-coverage scoring: infer from `decision_type`, or require an explicit `risk: true` flag? (Leaning: infer, with optional override.)
3. Trusted-metric threshold for decision readiness: reuse the metric-level "usable with caution" cutoff, or set a distinct, higher bar for decision gating? (Leaning: distinct, higher.)
4. Cross-vertical view in the public app at all (with synthetic multi-pack demo), or private-only? (Leaning: private-only; a static screenshot in docs for the public story.)

---

## 24. Positioning (for README)

> MetricReady checks whether a product area's measurement system is ready to support recurring decisions. v1 assesses individual metric quality. v2 assesses the system: which decisions are backed by trusted, owned, instrumented metrics, where the gaps are, and what to fix next.
>
> MetricReady does not judge whether a team has too many or too few metrics. It assesses whether the metric portfolio is structured well enough to support recurring product decisions.
```
