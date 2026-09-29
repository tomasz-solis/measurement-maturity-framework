# Streamlit app design handoff

A brief for any project that needs to recreate the Measurement Maturity Framework app. It isn't a pixel spec. It captures the intent, structure and visual rules that make the app feel like this product and not a generic Streamlit dashboard.

This handoff predates the shared Lab design system in [DESIGN.md](../DESIGN.md). Where they disagree (for example on shadows, glass surfaces and uppercase labels), DESIGN.md wins.

## Feel

An editorial review tool, not an analytics dashboard: calm, opinionated, a bit sceptical. The message is "review the metric definition before the number starts steering decisions."

- Serious but not stiff.
- Plain language over product-speak.
- Show risk clearly without alarm theatre.
- Every section has a purpose.

## Layout

A wide single page with the sidebar open by default.

- Sidebar: dark, branded control rail for inputs and downloads.
- Main area: light canvas with soft gradients and roomy spacing.
- Max content width: about `1260px`.

The page reads top to bottom:

1. The hero says what the review does.
2. Summary cards: pack identity, validation state, pack score, weakest metric.
3. `Signal 01`: validation.
4. `Signal 02`: scoring.
5. `Signal 03`: suggestions.
6. `Signal 04`: strategy tree.

Major sections are separated by simple horizontal rules.

## Visual direction

A soft light workspace next to a darker, high-contrast hero and sidebar.

### Surfaces

- Page background: very light grey-blue with subtle radial gradients.
- Content cards: white surfaces with soft borders.
- Hero and sidebar: dark gradients with blue and mint glow.
- Corners: large radius, mostly `22px` to `36px`.

### Colours

| Role | Value | Meaning |
|---|---|---|
| Background | `#eff2f7` | |
| Ink | `#10131a` | |
| Muted text | `#646c79` | |
| Accent blue | `#4f6dff` | Neutral emphasis |
| Accent mint | `#1ecf9b` | Positive |
| Watch amber | `#d18a1f` | Caution |
| Risk red | `#dd5b52` | Real risk |

Keep these meanings the same everywhere in the app.

### Type

- Headlines and numbers: `"Avenir Next", "Helvetica Neue", sans-serif`.
- Everything else: Streamlit's default sans is fine if no custom body font is available.
- Main headings are large and tight, with negative tracking.
- Large values use tabular numerals where possible.
- Body copy stays readable and restrained.

## Components

### Sidebar

The app's branded control surface. It holds:

- A small kicker, `Measurement Maturity`.
- The title, `Metric Pack Review`.
- A short description of the upload and review flow.
- The file uploader in a rounded, softly outlined container.
- Download buttons for example packs.
- A normalised YAML download after upload.
- One short tip at the bottom.

Darker and denser than the main canvas, but still clean.

### Hero

A large dark card with a kicker, one direct headline, a short paragraph and a row of pill badges. Before upload it explains the product. After upload it shows the pack name, and the pills show pack metadata (metric count, version, schema, score label). The hero is what stops the app feeling like raw Streamlit.

### Summary cards

A row of four under the hero: Pack ID, Validation, Pack Score, Weakest Metric. Rounded, short on text. One card can use the dark style to anchor the row. Colour the key number: blue for neutral metadata, mint for healthy, amber for caution, red for risk.

### Section headers

Each major section starts with a small label (`Signal 01`), a clear title and a short paragraph on why the section matters. The app is a guided audit, not a bundle of widgets.

### Validation

One idea first: structure comes before score. Show a success or error banner, three stat cards (errors, warnings, info), a table of issues, and technical detail in a collapsed expander. Scoring still runs when validation fails. That is deliberate; keep it.

### Scoring

Native Streamlit metrics styled to match: pack score, weakest metric, average metric, a threshold band with the four maturity levels, and a per-metric table. The threshold band reads like a guide, not a chart, and the active band gets a soft blue or mint highlight.

### Suggestions

Grouped by metric in expanders, weakest metric first. Each expander title has an icon, the metric name and its id. Use success, warning and info states inside. Actionable, not wordy.

### Strategy tree

Last and optional. If diagrams can't render, fall back to code or a warning. It must never break the rest of the app.

## Empty state

Before upload the page shouldn't look blank. Under the hero, three explainer cards:

- `Signal 01`: check the structure first.
- `Signal 02`: score decision risk, not performance.
- `Signal 03`: see the strategy path.

That explains the product in under a minute.

## Interaction

One page, one input path through the sidebar, no tabs, no heavy filtering, no modals. A review pass: upload a pack, scan the summary, read the sections in order, download normalised YAML if needed.

## Copy

The copy is part of the design.

- Plain English, direct.
- No hype, buzzwords or generic reassurance.
- Say what the tool doesn't do as clearly as what it does.
- Use the band names: "decision-ready", "usable with caution", "not safe for decisions".

It should sound like an experienced operator reviewing risk, not a growth landing page.

## Streamlit notes

- Use `st.set_page_config(layout="wide", initial_sidebar_state="expanded")`.
- Inject custom CSS early.
- Style Streamlit primitives through `data-testid` selectors only where needed.
- Build the hero, section headers, stat cards, threshold bands and empty-state cards as HTML through `st.markdown(..., unsafe_allow_html=True)`.
- Keep native widgets where default behaviour helps: file upload, metrics, alerts, tables, expanders.

It should still feel like Streamlit, just deliberate.

## Keep, and what can change

| Keep | Can change |
|---|---|
| Dark sidebar and hero on a light canvas | The exact font, if Avenir Next isn't available |
| Section framing with `Signal 01`, `Signal 02` and so on | Minor spacing |
| Large rounded cards | Exact shadows |
| Severity colours with fixed meanings | Helper text wording |
| One-page review flow | Mermaid or another diagram renderer |
| Copy that frames the app as a structural metric audit | |

## Prompt for another coding agent

```text
Build a Streamlit app that feels like an editorial audit tool, not a default dashboard. Use a wide layout with an expanded dark sidebar and a light main canvas. Add a large dark gradient hero card, rounded stat cards, and section headers labeled Signal 01, Signal 02, Signal 03 and Signal 04. Use blue for neutral emphasis, mint for positive state, amber for caution and red for risk. Keep the flow on one page: hero, summary cards, validation, scoring, suggestions and an optional strategy diagram. Keep the copy plain, sceptical and practical. Avoid marketing language and default Streamlit styling.
```
