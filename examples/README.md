# Metric Pack Examples

This directory contains example metric packs for the Streamlit app. Each
one is purpose-built to demonstrate a different aspect of the framework.

## Available Examples

### generic_product_metric_pack.yaml

A full-featured pack for a generic product workflow. Covers adoption,
engagement, outcome, reliability, and support metrics across four V1
definitions and one V0 proxy.

Demonstrates: multi-pillar strategy boards, impact graph linking metrics
to business goals, V0/V1 tier progression, ratio and value SQL patterns.

**Pack score: ~91**

---

### mixed_maturity_pack.yaml

Three production-ready V1 metrics alongside one V0 proxy that the team
is still stabilising. The pack score lands below the average metric score
because the floor weight pulls it toward the weakest metric.

Demonstrates: how a single V0 proxy affects pack-level scoring, the
difference between average metric score and pack score, realistic
mid-stage team state.

**Pack score: ~91** (average 95, floor pulls to 91 via the V0 proxy at 80)

---

### spreadsheet_pipeline_pack.yaml

A pack mid-migration from spreadsheet reporting to a SQL-backed warehouse.
Two metrics are fully migrated; two still run out of spreadsheet pipelines
and declare `implementation_type: spreadsheet`.

Demonstrates: the `missing_sql_structural` gap and its larger -12 deduction
(vs the default -5 for SQL that is merely absent). Shows why the framework
distinguishes "SQL will come soon" from "this metric lives in a spreadsheet."

**Pack score: ~89** (two perfect metrics, two at 83 due to structural SQL gap)

---

## How to Use

Run the app and upload any YAML file from this directory:

```bash
streamlit run app.py
```

Or score any pack directly from Python:

```python
import yaml
from mmf.scoring import score_pack

with open("examples/mixed_maturity_pack.yaml") as f:
    pack = yaml.safe_load(f)

result = score_pack(pack)
print(result.pack_score)
```

Use these as templates for your own metric packs. The `generic_product_metric_pack.yaml`
is the most complete structural reference; the other two focus on specific
scoring scenarios.

