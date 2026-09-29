# Product

## Register

product

## Platform

web

## Users

Analytics leads responsible for whether the company's metrics can be trusted. They own metrics they didn't always write, get asked to sign off numbers about to drive a decision, and need a defensible way to say "not yet" that holds up in a room of people who would rather ship. They arrive with a metric pack and a deadline.

There is one audience. PMs, execs and data teams read the output, but the tool is built for the person who signs off.

## Product purpose

A review tool for metric definitions before they are treated as decision-ready. It validates a metric pack, scores it, shows measurement debt, maps the decisions each metric should support, and exports the review. The concrete win: a metric marked not ready before it drives a call. Catching it here costs a conversation. Catching it after costs the decision.

## Positioning

Metrics are treated as decision-ready by default. This shows which ones have earned it.

## Brand personality

Rigorous, welcoming, practical. The voice is an honest analyst briefing a decision maker. It states the method, says its own limits out loud, and assumes the reader is smart but not a statistician. Closest in feel to FT or Economist interactives, where the chart and the text argue together and the caveat is part of the argument.

## Anti-references

A raw Streamlit default: unstyled widgets, stock colours, a prototype nobody looked after. If the app looks like someone's weekend notebook with a slider, the method loses credibility with it.

## Design principles

1. "Not ready" is the valuable verdict. The tool exists to say no with evidence. A failed check is the product working; present it that way.
2. Say the limit out loud. Where a score is soft or a check is a heuristic, the app says so where you read it.
3. The verdict must hold up in the room. Every finding can be exported and quoted, because the user has to defend it to people who want a different answer.
4. Meet non-specialists where they are. Every score, band and debt category has a plain-language definition within reach. Jargon that can't explain itself doesn't ship.
5. One system across the Lab. This app is one of three Product Decision Lab apps (`product-decision-under-uncertainty`, `experiment-architect`, `measurement-maturity-framework`). They must look like one family, so the design system is shared (see below). A visual idea that can't work in the other two doesn't ship here.

## Design system constraint (cross-repo)

`mmf/theme-tokens.css` is the shared source of truth and is byte-identical in all three repos (`mmf/` here, `static/` in product-decision-under-uncertainty, `ui/` in experiment-architect). Also shared: the pinned light Streamlit base with `primaryColor #4f6dff`, the periwinkle and mint radial background, the dark gradient sidebar, light panels, pill tabs and buttons, and the Avenir Next font stack.

Rules:

- Never edit the `--ds-*` tokens for this app alone. A token change is a three-repo change: edit here, then copy the file verbatim to the other two.
- Local names (`--mmf-*`) may only alias `--ds-*` tokens, never redefine the palette.
- Per-app variation is allowed only in the hero (`.mmf-hero`, vs `.app-hero` and `.editorial-hero`) and in app-specific components.

## Accessibility

WCAG 2.1 AA. Body text at least 4.5:1 and large text at least 3:1 against its surface (including the dark sidebar and hero), full keyboard navigation, `prefers-reduced-motion` respected, and severity (the pass, warn and fail vocabulary this app is built on) never shown by colour alone. Every verdict pairs its colour with an icon or label.
