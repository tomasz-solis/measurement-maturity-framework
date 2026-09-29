# Case studies

MMF applied after the fact to public metric failures. Most famous metric failures aren't the kind MMF was built to catch, and that is the point: the cases show where it stops.

MMF is strongest on slow governance problems:

- Metrics with no clear owner.
- SQL that lives in one person's head.
- Definitions that drift without being tagged as unstable.
- Metrics with no tests even though teams rely on them.

The public failures below are mostly logic bugs, framing choices or model problems.

| # | Case | Year | MMF verdict | Lesson |
|---|------|------|-------------|--------|
| 1 | [Netflix "view" redefinition](01_netflix_view_redefinition.md) | 2019-2020 | MISS (V1) / HIT (V0) | V0 is useful when the definition itself is still moving |
| 2 | [Facebook video watch time](02_facebook_video_duration.md) | 2014-2016 | MISS | Structural review doesn't catch a logic bug inside the SQL |
| 3 | [Uber MAPC at IPO](03_uber_mapc.md) | 2019 | MISS | A well-defined metric can still be a bad headline metric |

Netflix is the only partial hit, and only if the analyst tags the metric V0 before the redefinition. Facebook and Uber are clean misses by design.

## Why they still matter

They make the framework easier to use honestly. If a team needs SQL review, ownership hygiene and clearer definitions, MMF helps. If it needs protection against misleading aggregation or subtle logic bugs inside a valid query, MMF isn't enough on its own.

The `missing_sql_temporary` / `missing_sql_structural` split came out of this work and the calibration notes in the main methodology doc.

## Running them

Each case has a YAML spec and, where needed, a Python script:

```bash
# Netflix: V1 reconstruction vs cautious V0 tagging
python case_studies/01_netflix_run.py

# Any other case: score directly
python -c "
import yaml
from mmf.scoring import score_pack
with open('case_studies/02_facebook_video_duration.yaml') as f:
    pack = yaml.safe_load(f)
print(score_pack(pack))
"
```

## Method notes

- The YAML files are reconstructions from public reporting, not internal specs.
- The framework runs as-is, with no case-specific scoring logic.
- The commentary explains scope. It doesn't rescue the framework after the fact.
