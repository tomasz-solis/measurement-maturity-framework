# Case Study 3 — Uber's MAPC definition at IPO

**Status:** MISS. The framework scores 100/100 on a metric whose definition
bundles different behaviors into one headline number. The lesson is that MMF
checks whether a metric is defined, not whether it is the right single construct.

## What happened

In April 2019, Uber filed its S-1 ahead of its IPO. The headline user metric
disclosed to investors was "Monthly Active Platform Consumers" (MAPC),
defined as:

> The number of unique consumers who completed a Ridesharing or New Mobility
> ride or received an Uber Eats meal on our platform at least once in a given
> month, averaged over each month in the quarter.

MAPC in Q4 2018 was reported at 91 million, up 35% year over year.

The definition was technically precise and publicly disclosed. But it
combined three products — rideshare, micro-mobility (scooters and bikes
from the JUMP acquisition), and food delivery — into a single number.
Analyst coverage at the time (Investing.com, MergersAndInquisitions.com,
and others) noted the problem: if rideshare growth stalled but Uber Eats
grew fast, MAPC would still look healthy, and an investor reading the
headline number would not see the shift.

This is not metric fraud. Uber disclosed the construction. Any analyst with
the time to read past the headline could see what was in MAPC. But that's
the point: the metric only works cleanly as a headline number if the reader
does not look too closely at what is bundled inside it.

## What the framework sees

Reconstructed metric spec: [`03_uber_mapc.yaml`](03_uber_mapc.yaml).

The SQL UNIONs three event sources and counts distinct consumers. Every
structural check MMF runs passes:

```
Pack score: 100.0
  mapc: 100.0 — Well-defined and production-ready.
```

The metric has an owner (Corporate FP&A — Investor Metrics), SQL, three tests,
a description, grain, unit. Nothing is missing. The framework rates it
production-ready.

**This is a miss, but a different kind from the Facebook miss.** The Facebook
metric was structurally fine but logically wrong. The Uber metric is
structurally and logically fine *for the definition given* — but the definition
itself is a composite that obscures variation within it. The bug isn't in the
SQL; it's in the choice of what to put in the SQL.

## What this case teaches

**The framework checks the quality of a metric's definition, not the quality of
the decision to frame it as one metric.** If a team decides that "accounts that
bought anything from us" is the right unit of analysis, the framework can
audit whether that metric is well-defined. It cannot tell the team that their
choice of unit is strategically misleading.

Practical implication: for any metric that aggregates heterogeneous sub-
populations, the framework's 100/100 score is a green light on *the
implementation*, not on *the concept*. A careful reviewer should also ask:

- What is this metric composed of, and do those components move together?
- If one component grows while another shrinks, does the composite signal
  what we want it to signal?
- Is there a breakdown view that should accompany the headline number?

None of those questions live in MMF today.

## What would it take to catch this in the framework?

Three candidate extensions, in increasing order of effort:

1. **A `decomposable` check.** Add an optional field to a metric spec listing
   its sub-metrics (e.g. `decomposes_into: [rideshare_mau, new_mobility_mau,
   eats_mau]`). Deduct points when a metric is composite but has no
   decomposition listed. This is mostly about forcing the analyst to be
   explicit rather than letting composition hide.

2. **A `homogeneity_assumption` field.** Require composite metrics to declare
   whether their components are assumed to co-move (same direction, similar
   magnitude). When that assumption is asserted, require a test that checks
   it historically — e.g. a correlation check between sub-metric movements.

3. **A reporting/decomposition rule for headline metrics.** Require that any
   metric whose use case includes "investor reporting" or "board-level"
   carries a sub-breakdown in the pack. This is closer to a governance
   extension than a scoring one.

Option 1 is a week's work and immediately useful. Option 2 is more honest
but requires backfilled sub-metrics for every composite, which is a lot to
ask. Option 3 is governance and lives closer to a CFO office than a metric
framework.

## What the framework *would* catch if the analyst declared the problem

Just as with Netflix (Case 1), the framework gives the analyst a way to signal
the risk *if they choose to*. A pragmatic analyst looking at Uber's MAPC might
write a `description` that explicitly names the composition risk:

> MAPC aggregates Ridesharing, New Mobility, and Uber Eats consumers. Investors
> reading MAPC growth in isolation may miss divergence between these segments.
> Always present MAPC alongside sub-segment breakdowns when used in external
> reporting.

And might tag the metric V0 until a segment-breakdown companion is ready. The
tier deduction would then surface the risk in the score, as with Netflix.

That is a reasonable use of the framework by the analyst. It is not something
the framework will do on its own.

## Sources

- Uber Technologies, Inc., Form S-1 (April 11, 2019), definition of MAPC
- PYMNTS, "Uber's Growth Slowed But Sees $12 Trillion Market Opportunity"
  (April 2019)
- CNBC, "Uber releases S-1 filing for IPO" (April 11, 2019)
- Investing.com, "Uber IPO Preview" (April 2019)
- MergersAndInquisitions.com, "Uber Valuation" (May 2019)
