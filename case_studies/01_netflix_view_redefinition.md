# Case Study 1 — Netflix redefines "view," reported viewership jumps 35%

**Status:** MISS under default tagging. HIT when the metric is proactively
tagged V0. Teaches: V0 is not just for "new" metrics. It is also for metrics
whose definition is not stable yet.

## What happened

From roughly 2015 to 2019, Netflix reported viewership using a metric it later
called "watchers": a view was counted when a household watched at least 70% of
a title's runtime. In the Q4 2019 shareholder letter (January 2020), Netflix
redefined "view" to mean any account that watched at least two minutes of a
title — long enough to suggest intent, per the company's framing.

The effect was immediate and material. Netflix itself disclosed in that same
shareholder letter that the new metric was "about 35% higher on average than
the prior metric." The company's example: *Our Planet* had 33M member households
under the old definition and 45M under the new one. Same show, same actual
watching behavior, 35% more reported viewers.

Critics across trade press (Hollywood Reporter, Variety, Wall Street Journal)
noted that the redefinition came right as subscriber growth was slowing, and
that two minutes of a 50-minute episode was a very loose threshold.

Netflix eventually shifted again in 2021 (to total hours watched, aligning with
Nielsen) and again in 2023 (to hours divided by runtime, which normalises for
content length). In six years the underlying question "is this title popular?"
had four different operational answers.

## What the framework sees

Reconstructed metric spec: [`01_netflix_actual.yaml`](01_netflix_actual.yaml).
Run the analysis: `python case_studies/01_netflix_run.py`.

### Version A — what Netflix likely had internally (tier: V1)

```
Pack score: 100.0
  title_views: 100.0 — Well-defined and production-ready.
```

The metric has SQL, an owner, tests, a description, unit, grain. Every
structural check passes. The framework rates it production-ready and hands
the analyst a green light.

**This is a miss.** The framework's checklist does not include "is this
definition under product-marketing pressure to change?" And as a tool that
only audits what you tell it, it cannot. A competent analyst, looking at the
Netflix spec as of Q3 2019, would have written something very close to
Version A. The metric worked. The SQL was correct. Tests caught freshness
and range problems. Ownership was clear.

### Version B — same metric, proactively tagged V0

```
Pack score: 90.0
  title_views: 90.0 — Good start, but it's a V0 proxy.
    gaps: ['tier_v0']
```

A -10 deduction. The metric is flagged as a V0 proxy and the framework's
suggestion output (not shown above) would recommend scheduling a V1 pass once
the definition settles. A downstream consumer, whether that is an earnings
preparer or dashboard builder, would see the V0 tag and know to double-check that the metric
definition still matches what they assumed when they incorporated it into their
work.

## What this case teaches

The framework's gap-check system doesn't detect redefinition risk directly.
What it *does* provide is a dedicated instrument for the analyst to declare it:
**V0 is not just for "I haven't finished the SQL yet." V0 is for "this definition
is not something I'm willing to commit to long-term."**

Under that interpretation, any of the following should plausibly be V0:

- Metrics tied to evolving product definitions (what counts as "active"? what
  counts as "completed"?)
- Metrics that depend on thresholds the product team controls ("70% watched,"
  "2 minutes watched")
- Metrics where marketing or leadership has pressured redefinitions in the past
- Metrics whose underlying event schema is still evolving

A Netflix analyst who had read this framework in 2018 and tagged `title_views`
as V0 would have been doing exactly what the framework is designed for: encoding
a known stability risk into the score, so that downstream consumers see it
without having to know the metric's full history.

## What the framework still cannot catch

Even with V0 tagging, the framework does not:

- Predict *when* a redefinition will happen
- Compare the new and old definitions for continuity
- Flag historical series discontinuities when a redefinition has just occurred
- Quantify the impact of the redefinition on downstream decisions

Those would be useful extensions. None of them are in the current scoring
contract. Naming them honestly is part of what a mature measurement framework
should do.

## Sources

- Netflix Q4 2019 shareholder letter (via company investor relations; reported in
  WSJ, Hollywood Reporter, Variety — January 2020)
- Hollywood Reporter, "Netflix Viewership Changes Explained" (June 2023)
- Michael L Wayne, "Netflix audience data, streaming industry discourse," journals.sagepub.com (2022)
