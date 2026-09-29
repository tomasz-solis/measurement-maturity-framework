# Case study 3: Uber's MAPC definition at IPO

Result: a miss. The framework scores 100/100 on a metric that bundles different behaviours into one headline number. MMF checks whether a metric is defined, not whether it is the right single measure.

## What happened

In April 2019 Uber filed its S-1 ahead of its IPO. The headline user metric for investors was Monthly Active Platform Consumers (MAPC):

> The number of unique consumers who completed a Ridesharing or New Mobility ride or received an Uber Eats meal on our platform at least once in a given month, averaged over each month in the quarter.

MAPC for Q4 2018 was 91 million, up 35% year over year.

The definition was precise and public, but it combined three products: rideshare, micro-mobility (scooters and bikes from the JUMP acquisition) and food delivery. Analysts at the time (Investing.com, MergersAndInquisitions.com and others) pointed out the problem: if rideshare stalled while Uber Eats grew fast, MAPC would still look healthy, and an investor reading the headline wouldn't see the shift.

This isn't metric fraud. Uber disclosed how MAPC was built, and anyone who read past the headline could see it. But the metric only works as a clean headline if the reader doesn't look closely at what's inside.

## What the framework sees

Reconstructed spec: [`03_uber_mapc.yaml`](03_uber_mapc.yaml).

The SQL unions three event sources and counts distinct consumers. Every structural check passes:

```text
Pack score: 100.0
  mapc: 100.0 - Well-defined and ready for production use.
```

The metric has an owner (Corporate FP&A, Investor Metrics), SQL, three tests, a description, a grain and a unit. Nothing is missing.

This is a different miss from Facebook. Facebook's metric was structurally fine but logically wrong. Uber's is structurally and logically fine for its definition, but the definition is a composite that hides variation inside it. The problem isn't in the SQL. It's in what was put in the SQL.

## What this case teaches

The framework checks how well a metric is defined, not whether framing it as one metric was wise. If a team decides "accounts that bought anything from us" is the right unit, MMF can audit that metric. It can't tell the team the unit is strategically misleading.

For any metric that combines different sub-populations, a 100/100 score approves the implementation, not the concept. A careful reviewer should also ask:

- What is this metric made of, and do the parts move together?
- If one part grows while another shrinks, does the total still say what we want?
- Should a breakdown sit next to the headline number?

MMF doesn't ask these today.

## What it would take to catch this

Three possible extensions, from least to most effort:

1. A `decomposable` check. An optional field lists a metric's sub-metrics (for example `decomposes_into: [rideshare_mau, new_mobility_mau, eats_mau]`), and a composite metric without it loses points. It mainly forces the analyst to be explicit.
2. A `homogeneity_assumption` field. Composite metrics declare whether their parts are assumed to move together. If they do, a test has to check it against history, for example a correlation between sub-metric movements.
3. A breakdown rule for headline metrics. Any metric used for investor or board reporting must carry a sub-breakdown in the pack. This is closer to governance than scoring.

Option 1 is about a week of work and useful right away. Option 2 is more honest but needs backfilled sub-metrics for every composite. Option 3 belongs closer to a CFO office than a metric framework.

## What it would catch if the analyst declared the risk

As with Netflix (case 1), the analyst can signal the risk. A careful analyst might write a `description` that names it:

> MAPC aggregates Ridesharing, New Mobility, and Uber Eats consumers. Investors reading MAPC growth in isolation may miss divergence between these segments. Always present MAPC alongside sub-segment breakdowns when used in external reporting.

They might also tag it V0 until a segment breakdown exists, so the tier deduction shows the risk in the score. That's a reasonable use of the framework. It won't do it on its own.

## Sources

- Uber Technologies, Inc., Form S-1 (April 11, 2019), definition of MAPC
- PYMNTS, "Uber's Growth Slowed But Sees $12 Trillion Market Opportunity" (April 2019)
- CNBC, "Uber releases S-1 filing for IPO" (April 11, 2019)
- Investing.com, "Uber IPO Preview" (April 2019)
- MergersAndInquisitions.com, "Uber Valuation" (May 2019)
