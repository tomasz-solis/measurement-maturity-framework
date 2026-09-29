# Case study 2: Facebook's inflated video watch-time metric

Result: a miss. The SQL exists, the metric has an owner and the pack is well formed. The problem is inside the query logic, which MMF doesn't audit.

## What happened

From roughly 2014 to 2016, Facebook overstated a video engagement metric used by advertisers. Public reporting and later lawsuit filings said the numerator counted all watched seconds while the denominator counted only views longer than three seconds. That mismatch pushed the reported average up a lot.

A sceptic would say: if the framework misses this, what good is it? MMF was never meant to prove a query is logically correct. It checks whether a metric is documented, reviewable and owned.

## What the framework sees

Reconstructed pack: [`02_facebook_video_duration.yaml`](02_facebook_video_duration.yaml).

The pack has an owner, a description, SQL, tests, a unit and a grain, so MMF scores it highly. Uncomfortable but honest: the query is present and reviewable. The logic inside it is wrong.

## What this case teaches

MMF reviews structure, not SQL semantics. It helps teams notice missing owners, absent or hidden SQL, missing tests, and unstable definitions that should be tagged V0. It can't tell you a ratio is built wrong if the SQL is there and parses.

## What helps beyond MMF

If this kind of failure matters to you, add a layer next to MMF:

- Query review by another analyst or engineer.
- Metric-specific invariants in the tests.
- Reconciliation against raw events or alternative definitions.
- Pair review for ratios and filters.

## Sources

- Wall Street Journal reporting on Facebook's September 2016 disclosure
- Later class-action filings describing the denominator bug
- Facebook's public statements on the correction window and affected metrics
