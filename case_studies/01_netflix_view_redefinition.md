# Case study 1: Netflix redefines "view", reported viewership jumps 35%

Result: a miss with default tagging, a hit if the metric is tagged V0 in advance. V0 isn't only for new metrics. It is also for metrics whose definition isn't stable yet.

## What happened

From roughly 2015 to 2019, Netflix reported viewership with a metric it later called "watchers": a household counted as a view after watching at least 70% of a title's runtime. In the Q4 2019 shareholder letter (January 2020), Netflix changed "view" to mean any account that watched at least two minutes of a title, enough to suggest intent in the company's framing.

The effect was immediate. Netflix said in the same letter that the new metric was "about 35% higher on average than the prior metric." Its example: *Our Planet* had 33M member households under the old definition and 45M under the new one. Same show, same viewing, 35% more reported viewers.

Trade press (Hollywood Reporter, Variety, Wall Street Journal) pointed out that the change came just as subscriber growth was slowing, and that two minutes of a 50-minute episode is a very loose threshold.

Netflix changed again in 2021 (total hours watched, in line with Nielsen) and in 2023 (hours divided by runtime, which normalises for length). In six years, "is this title popular?" had four different operational answers.

## What the framework sees

Reconstructed spec: [`01_netflix_actual.yaml`](01_netflix_actual.yaml). Run it with `python case_studies/01_netflix_run.py`.

### Version A: what Netflix likely had internally (tier V1)

```text
Pack score: 100.0
  title_views: 100.0 - Well-defined and ready for production use.
```

The metric has SQL, an owner, tests, a description, a unit and a grain. Every structural check passes, so the framework gives a green light.

That's a miss. The checklist has no item for "is this definition under marketing pressure to change?", and a tool that only audits what you tell it can't have one. A competent analyst looking at the spec in Q3 2019 would have written something very close to Version A. The metric worked, the SQL was right, the tests caught freshness and range problems, and ownership was clear.

### Version B: the same metric, tagged V0 in advance

```text
Pack score: 90.0
  title_views: 90.0 - Good start, but it's a V0 proxy.
    gaps: ['tier_v0']
```

A 10-point deduction. The metric is flagged as a V0 proxy, and the suggestions (not shown) would recommend a V1 pass once the definition settles. Anyone downstream, an earnings preparer or a dashboard builder, would see the V0 tag and know to check the definition still matches what they assumed.

## What this case teaches

The gap checks don't detect redefinition risk directly. What the framework does give is a way for the analyst to declare it: V0 can mean "I'm not willing to commit to this definition long term."

On that reading, these should probably be V0:

- Metrics tied to changing product definitions (what counts as "active" or "completed").
- Metrics that depend on thresholds the product team controls ("70% watched", "2 minutes watched").
- Metrics that leadership or marketing have pushed to redefine before.
- Metrics whose event schema is still changing.

A Netflix analyst who tagged `title_views` as V0 in 2018 would have been using the framework exactly as designed: putting a known stability risk into the score so downstream users see it without knowing the metric's history.

## What it still can't catch

Even with V0 tagging, the framework doesn't:

- Predict when a redefinition will happen.
- Compare old and new definitions for continuity.
- Flag breaks in a historical series right after a redefinition.
- Measure the redefinition's effect on downstream decisions.

Those would be useful extensions. None are in the current scoring contract.

## Sources

- Netflix Q4 2019 shareholder letter (via investor relations; reported in WSJ, Hollywood Reporter, Variety, January 2020)
- Hollywood Reporter, "Netflix Viewership Changes Explained" (June 2023)
- Michael L Wayne, "Netflix audience data, streaming industry discourse," journals.sagepub.com (2022)
