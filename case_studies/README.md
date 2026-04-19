# Case Studies

These case studies apply MMF to public metric failures after the fact.

The main takeaway is simple: most famous metric failures are not the kind of
failure MMF was built to catch. That is not a bug in the case studies. It is
the point of them.

MMF is strongest on slow governance problems:

- metrics with no clear owner
- SQL that lives only in one person's head
- definitions that drift without being tagged as unstable
- metrics with no tests even though teams already rely on them

The public failures below are different. They are usually logic bugs, framing
choices, or model problems. Running them through MMF makes the framework's
scope easier to see.

## The cases

| # | Case | Year | MMF verdict | Lesson |
|---|------|------|-------------|--------|
| 1 | [Netflix "view" redefinition](01_netflix_view_redefinition.md) | 2019-2020 | MISS (V1) / HIT (V0) | V0 is useful when the definition itself is still moving |
| 2 | [Facebook video watch time](02_facebook_video_duration.md) | 2014-2016 | MISS | Structural review does not catch a logic bug inside the SQL |
| 3 | [Uber MAPC at IPO](03_uber_mapc.md) | 2019 | MISS | A well-defined metric can still be a bad headline metric |

Netflix is the only partial hit, and only if the analyst chooses to tag the
metric as V0 before the redefinition happens. Facebook and Uber are clean
misses by design.

## Why these cases still matter

They show where MMF stops. That makes it easier to use the framework honestly.
If a team needs SQL review, ownership hygiene, and clearer definitions, MMF is
useful. If a team needs protection against misleading aggregation choices or
subtle logic bugs inside an otherwise valid query, MMF is not enough on its own.

That is also where some follow-on changes came from. The current
`missing_sql_temporary` / `missing_sql_structural` split grew out of this work
plus the calibration notes in the main methodology doc.

## Running the analysis

Each case has a YAML spec and, where relevant, a Python script:

```bash
# Netflix — two-version comparison (V1 reconstruction vs V0 cautious tagging)
python case_studies/01_netflix_run.py

# Any other case — direct scoring
python -c "
import yaml
from mmf.scoring import score_pack
with open('case_studies/02_facebook_video_duration.yaml') as f:
    pack = yaml.safe_load(f)
print(score_pack(pack))
"
```

## Methodology notes

- These YAML files are reconstructions from public reporting, not leaked internal specs.
- The framework is run as-is. There is no case-specific scoring logic.
- The commentary around each case is there to explain scope, not to rescue the framework after the fact.
