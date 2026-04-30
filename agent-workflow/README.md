# agent-workflow

This folder is the operating manual for the agent (and any human contributor)
working on this repository. It implements a **spec-driven, ticket-based workflow**
with persistent memory.

## Why this exists

The IoT platform described in `context/doc/` is large and multi-phase.
Building it in a single agent session is unrealistic. We need:
- A stable plan that survives across sessions.
- A clear "active task" so the agent does not drift.
- A trail of decisions, lessons and reviews per task.
- A memory of patterns and traps that grows over time.

## File map

| Path | Purpose |
|---|---|
| `README.md` | This file. Entry point. |
| `charter.md` | Project vision, scope and out-of-scope. |
| `architecture.md` | Target architecture. Filled progressively. |
| `roadmap.md` | Ordered list of tickets per phase. Most are TODO stubs. |
| `memory/patterns.md` | Patterns that worked, worth reusing. Starts empty. |
| `memory/gotchas.md` | Traps encountered. Starts empty. |
| `memory/glossary.md` | Domain terms (NGSI, QuantumLeap, etc.). |
| `templates/*.md` | Boilerplate copied into each new ticket. |
| `tickets/NNNN-<slug>/` | One folder per ticket. |

## The loop

Each ticket goes through six phases. Phases 1 and 2 have **explicit user
approval gates** — the agent must stop and ask.

```
        ┌───────────────────────────────────────────────────┐
        │  1. requirements.md  ← drafted by agent           │
        │     ─── USER APPROVAL ───                         │
        │  2. design.md        ← drafted by agent           │
        │     ─── USER APPROVAL ───                         │
        │  3. tasks.md         ← verifiable checklist       │
        │  4. Implementation   ← tick tasks as you go       │
        │  5. journal.md       ← decisions + lessons        │
        │  6. review.md        ← self-review + external     │
        │     ─── USER APPROVAL TO CLOSE ───                │
        │  7. Distill lessons → memory/                     │
        └───────────────────────────────────────────────────┘
```

## Status states

`status.md` of each ticket holds one of:
- `planning` — requirements being drafted
- `in-progress` — design approved, implementation underway
- `review` — implementation done, awaiting review
- `done` — closed
- `abandoned` — dropped (keep folder; record why in `journal.md`)

**Only one ticket may be `in-progress` at a time.**

## How to start the next ticket

1. Pick the next item from `roadmap.md`.
2. Create `tickets/NNNN-<slug>/` by copying every file from `templates/`.
3. Set `status.md` to `planning`.
4. Fill `requirements.md`. Stop. Ask the user to approve.
5. After approval, set `status.md` to `in-progress` and continue with `design.md`.

## Memory propagation

When closing a ticket, before marking `done`:
- Append reusable patterns to `memory/patterns.md`.
- Append discovered traps to `memory/gotchas.md`.
- Append new domain terms to `memory/glossary.md`.

Memory entries are short bullets, not essays. One line per insight where possible.

## Approval shorthand

When the agent says **"Approval gate: please review and confirm"**,
no further work happens until the user replies with `approved`, `changes:`,
or `reject`.
