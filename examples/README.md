# Metric Pack Examples

This directory contains example metric packs showing how to apply the framework.

## Available Examples

### generic_product_metric_pack.yaml

Sample metric pack for a generic product workflow covering:
- Adoption metrics (feature activation)
- Engagement metrics (weekly active rate)
- Outcome metrics (time to first value)
- Health metrics (workflow reliability)
- Support metrics (ticket ratio)

Demonstrates:
- Multi-pillar metric trees
- Strategy board visualization
- Impact graph linking metrics to business goals
- V0/V1 tier progression
- Generic naming you can reuse without inheriting one company's domain
- Current pack structure used by the app (`pack`, `strategy_board`, `impact_graph`, `metrics`)

### How to Use

1. Load any YAML file into the auditor:
   ```bash
   streamlit run app.py
   ```

2. Review the maturity score and suggestions

3. Use as a template for your own metric packs
