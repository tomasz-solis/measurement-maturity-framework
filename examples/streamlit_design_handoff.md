# Streamlit App Design Handoff

Use this as the design brief for any other project that needs to recreate
the current Measurement Maturity Framework app. It is not a pixel-perfect
spec. It captures the intent, structure, and visual rules that make the
app feel like this product instead of a generic Streamlit dashboard.

## Product Feel

The app should feel like an editorial review tool, not an analytics
dashboard. It is calm, opinionated, and slightly skeptical. The message is:
"review the metric definition before the number starts steering decisions."

That has a few practical consequences:

- Keep the tone serious but not stiff.
- Prefer plain language over product-speak.
- Show risk clearly, but do not turn the interface into alarm theatre.
- Make the app feel curated. Every section should have a purpose.

## Core Layout

The app uses a wide single-page layout with the sidebar expanded by
default.

- Sidebar: dark, branded control rail for inputs and downloads.
- Main area: light canvas with soft gradients and roomy spacing.
- Max content width: about `1260px`.
- Flow: hero first, then summary cards, then four vertical sections.

The page is designed as a guided read:

1. Hero explains what this review does.
2. Summary cards show pack identity, validation state, pack score, and the
   weakest metric.
3. `Signal 01` covers validation.
4. `Signal 02` covers scoring.
5. `Signal 03` covers suggestions.
6. `Signal 04` covers the strategy tree.

Use visible separators between major sections. The current app uses simple
horizontal rules.

## Visual Direction

The visual system mixes a soft light workspace with a darker, high-contrast
hero and sidebar.

### Background and surfaces

- Page background: very light grey-blue with subtle radial gradients.
- Content cards: translucent white surfaces with soft borders.
- Hero and sidebar: dark gradient surfaces with blue and mint glow accents.
- Corners: large radius throughout. Most cards feel between `22px` and
  `36px`.
- Shadows: soft and layered, not dramatic.

### Color palette

Base colors:

- Background: `#eff2f7`
- Ink: `#10131a`
- Muted text: `#646c79`
- Accent blue: `#4f6dff`
- Accent mint: `#1ecf9b`
- Watch amber: `#d18a1f`
- Risk red: `#dd5b52`

Use blue for neutral emphasis, mint for positive accents, amber for caution,
and red for real risk. Keep those meanings stable across the app.

### Typography

The design relies on one simple contrast:

- Headlines and numeric values: `"Avenir Next", "Helvetica Neue", sans-serif`
- Everything else: Streamlit default sans is fine if a custom body font is
  not available

Style rules:

- Main headings are large, tight, and slightly condensed through negative
  tracking.
- Small labels use uppercase with generous letter spacing.
- Large values use tabular numerals when possible.
- Body copy stays readable and restrained.

## Key Components

### Sidebar

The sidebar is not just a utility panel. It acts like the app's branded
control surface.

Include:

- Small kicker: `Measurement Maturity`
- Main title: `Metric Pack Review`
- Short description explaining upload + review flow
- File uploader in a rounded, softly outlined container
- Example-pack download buttons
- Normalized YAML download after upload
- One concise tip at the bottom

The sidebar should feel darker and denser than the main canvas, but still
clean.

### Hero

The hero is a large dark card with:

- An uppercase kicker
- One direct headline
- A short explanatory paragraph
- A row of pill badges

In the empty state, the hero explains the product. In the loaded state, it
switches to the pack name and uses the pills for pack metadata such as
metric count, version, schema, and score label.

The hero is important because it stops the app from feeling like raw
Streamlit output.

### Summary cards

Right under the hero, use a 4-card row:

- Pack ID
- Validation
- Pack Score
- Weakest Metric

Cards are rounded, lightly translucent, and short on text. One card can use
the darker style to anchor the row.

Tone the key number in each card:

- Blue for neutral metadata
- Green/mint for healthy state
- Amber for caution
- Red for risk

### Section headers

Every major section starts with:

- A small label like `Signal 01`
- A clear title
- A short paragraph explaining why the section matters

This framing matters. The app is designed as a guided audit, not a bundle of
widgets.

### Validation section

The validation area should communicate one idea first: "structure comes
before score."

Use:

- A success or error banner
- Three stat cards for errors, warnings, and info
- A tabular issue list
- Optional technical details in a collapsed expander

Even when validation fails, the app still continues into scoring. That is a
deliberate product choice and should be preserved.

### Scoring section

This section uses more native Streamlit metrics, but styled to match the
rest of the app.

Show:

- Pack score
- Weakest metric
- Average metric
- Threshold band with four maturity levels
- Table of per-metric results

The threshold band should read like an interpretation guide, not a chart.
The active band gets a gentle blue/mint highlight.

### Suggestions section

Suggestions are grouped by metric inside expanders.

Rules:

- Sort weaker metrics first.
- Make the expander title include an icon, the metric name, and the metric
  id.
- Use success, warning, and info states inside each expander.

This section should feel actionable, not verbose.

### Strategy tree

The strategy tree is last and optional. It is useful, but not the main
event.

If diagram rendering is unavailable, fall back gracefully to code or a
warning state. Do not let this section break the rest of the app.

## Empty State

Before upload, the app should not look blank.

Below the hero, show three explainer cards:

- `Signal 01`: check the structure first
- `Signal 02`: score decision risk, not performance
- `Signal 03`: see the strategy path

This keeps the first-run experience intentional and explains the product in
under a minute.

## Interaction Rules

Keep the interaction model simple:

- One page
- One primary input path through the sidebar
- No tabs
- No heavy filtering
- No modal workflow

The app should feel like a clean review pass:

- upload a pack
- scan the summary
- read sections in order
- download normalized YAML if needed

## Copy Style

The copy is one of the design assets. Keep it in the same voice.

- Write in plain English.
- Be direct.
- Avoid hype, buzzwords, and generic reassurance.
- Say what the tool does not do as clearly as what it does.
- Use phrasing like "decision-ready", "usable with caution", and "not safe
  for decisions".

Good copy sounds like an experienced operator reviewing risk, not a growth
landing page.

## Streamlit Implementation Notes

If the other project is also using Streamlit, these implementation choices
matter:

- Use `st.set_page_config(layout="wide", initial_sidebar_state="expanded")`.
- Inject custom CSS early.
- Style Streamlit primitives through `data-testid` selectors only where
  needed.
- Build hero, section headers, stat cards, threshold bands, and empty-state
  cards as HTML blocks rendered through `st.markdown(...,
  unsafe_allow_html=True)`.
- Keep native Streamlit widgets for things that benefit from default
  behavior, such as file upload, metrics, alerts, tables, and expanders.

That balance is the point. The app should still feel like Streamlit, just
much more intentional.

## What To Preserve

If the design needs to be adapted, preserve these things first:

- Dark sidebar + dark hero against a light content canvas
- Editorial section framing with `Signal 01`, `Signal 02`, and so on
- Large rounded cards with soft glass-like surfaces
- Clear severity colors with stable meaning
- Single-page review flow
- Copy that frames the app as a structural metric audit

## What Can Change

These parts are safe to adapt:

- The exact font, if `Avenir Next` is not available
- Minor spacing values
- Exact shadows and blur intensity
- The specific wording of helper text
- Whether the strategy tree uses Mermaid or another diagram renderer

## Prompt Starter For Another AI Project

If you need to brief another coding agent, this prompt is a good starting
point:

```text
Build a Streamlit app that matches the feel of an editorial audit tool, not
a default dashboard. Use a wide layout with an expanded dark sidebar and a
light main canvas. Add a large dark gradient hero card, glassy rounded stat
cards, and section headers labeled Signal 01, Signal 02, Signal 03, and
Signal 04. Use blue for neutral emphasis, mint for positive state, amber for
caution, and red for risk. Keep the flow single-page: hero, summary cards,
validation, scoring, suggestions, and an optional strategy diagram. The copy
should be plain, skeptical, and practical. Avoid marketing language and
avoid generic Streamlit styling.
```
