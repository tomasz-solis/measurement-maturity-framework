# Product

## Register

product

## Platform

web

## Users

Analytics leads who are responsible for whether the company's metrics can be trusted. They own a
metric set they did not always write, they get asked to certify numbers that are about to drive a
decision, and they need a defensible way to say "not yet" — one that survives a room full of people
who would rather ship. They arrive with a metric pack and a deadline.

There is one audience. Others read the output — PMs, execs, data teams — but the tool is designed
for the person who has to sign off.

## Product Purpose

A review tool for metric definitions, used before those metrics are treated as decision-ready. It
validates a metric pack, scores it, surfaces measurement debt, maps the decisions each metric is
supposed to support, and exports the review. The win is concrete: **a metric marked
not-decision-ready before it drives a call.** Catching it here costs a conversation; catching it
after the decision costs the decision.

## Positioning

Metrics are treated as decision-ready by default. This says which ones have actually earned it.

## Brand Personality

Rigorous, welcoming, practical. The voice is an honest analyst briefing a decision-maker, not a
vendor pitching one: it states the method, names its own limits out loud, and assumes the reader is
smart but not a statistician. Closest in feel to FT / Economist interactives — editorial numeracy,
where the chart and the prose argue together and the honest caveat is part of the argument rather
than a footnote.

## Anti-references

A raw Streamlit default: unstyled widgets, stock primary colours, the look of a prototype nobody
cared about. If the interface reads as "someone's weekend notebook with a slider on it", the
method's credibility goes with it.

## Design Principles

- **"Not ready" is the valuable verdict.** The tool exists to say no with evidence. A failed check
  is the product working, not the product complaining — present it that way.
- **Say the limit out loud.** Where a score is soft or a check is heuristic, the interface says so
  at the point of reading. Honesty is the trust mechanism.
- **The verdict must survive the room.** Every finding is exportable and quotable, because the user
  has to defend it to people who want a different answer.
- **Meet a non-specialist where they stand.** Every score, band, and debt category carries a
  plain-language definition within reach. Jargon that cannot explain itself does not ship.
- **One system across the Lab.** This app is one of three Product Decision Lab surfaces
  (`product-decision-under-uncertainty`, `experiment-architect`,
  `measurement-maturity-framework`). They must read as one family, so the design system is a
  shared contract, not a local choice — see the constraint below. A visual idea that cannot travel
  to the other two does not ship here.

## Design system constraint (cross-repo)

`mmf/theme-tokens.css` is the shared source of truth and is **byte-identical** in all three repos
(stored at `mmf/` here, `static/` in product-decision-under-uncertainty, `ui/` in
experiment-architect). Also shared: the pinned light Streamlit base with `primaryColor #4f6dff`,
the periwinkle/mint radial app background, the dark gradient sidebar, glassy light panels, pill
tabs and buttons, and the Avenir Next stack.

Rules:

- Never edit the `--ds-*` tokens for this app alone. A token change is a three-repo change: edit it
  here, then copy the file verbatim into the other two.
- Local names (`--mmf-*`) may only alias `--ds-*` tokens, never redefine the palette.
- Per-app variation is allowed only in the branded hero (`.mmf-hero`, vs `.app-hero` and
  `.editorial-hero`) and in app-specific components. Everything else stays in the family vocabulary.

## Accessibility & Inclusion

WCAG 2.1 AA. Body text ≥4.5:1 and large text ≥3:1 against its surface (the dark sidebar and the dark
hero included), full keyboard navigation, `prefers-reduced-motion` honoured, and severity — the
pass/warn/fail vocabulary this app is built on — never carried by colour alone. Every verdict pairs
its colour with an icon or a label.
