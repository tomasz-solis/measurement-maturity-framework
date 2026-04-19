# Case Study 2 — Facebook's inflated video watch-time metric

**Status:** MISS. The SQL exists, the metric has an owner, and the pack looks
well-formed. The problem sits inside the query logic, which MMF does not audit.

## What happened

From roughly 2014 to 2016, Facebook overstated a video engagement metric used
by advertisers. Public reporting and later lawsuit filings said the numerator
counted all watched seconds, while the denominator counted only views longer
than three seconds. That mismatch pushed the reported average up materially.

This is the kind of failure that makes people suspicious of any "metric
governance" tool. A skeptic would say: if the framework misses this, what good
is it? The fair answer is that MMF was never meant to prove a query is logically
correct. It checks whether the metric is documented, reviewable, and owned.

## What the framework sees

Reconstructed pack: [`02_facebook_video_duration.yaml`](02_facebook_video_duration.yaml)

The pack has:

- an owner
- a description
- SQL
- tests
- unit and grain

So MMF gives it a strong score. That result is uncomfortable, but honest. The
query is present and reviewable. The bug is that the logic inside the query is
wrong.

## What this case teaches

MMF is a structural review layer, not a semantic SQL checker.

It can help teams notice:

- missing ownership
- absent or hidden SQL
- missing tests
- unstable definitions that should still be tagged V0

It cannot tell you that a ratio is built incorrectly if the SQL itself is
present and syntactically fine.

## What would help beyond MMF

If this kind of failure matters in your environment, you need an extra layer on
top of MMF. A few examples:

- query review by another analyst or engineer
- metric-specific invariants in tests
- reconciliation checks against raw events or alternate definitions
- pair review for ratios and filters

Those practices live next to MMF, not inside it.

## Sources

- Wall Street Journal reporting on Facebook's September 2016 disclosure
- Subsequent class-action filings describing the denominator bug
- Facebook's public statements on the correction window and affected metrics
