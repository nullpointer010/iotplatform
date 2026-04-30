# AGENTS.md

This repository builds an IoT platform for the CropDataSpace project.
The product spec is in `context/doc/`. The development plan and workflow live in `agent-workflow/`.

**Always read `agent-workflow/README.md` before doing any non-trivial work.**

## Behavior rules

### 1. Think before coding
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — do not pick silently.
- If a simpler approach exists, say so.

### 2. Simplicity first
- Minimum code that solves the problem. Nothing speculative.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that was not requested.
- No error handling for impossible scenarios.

### 3. Surgical changes
- Touch only what you must. Every changed line must trace to the active ticket.
- Do not refactor adjacent code.
- Match existing style. Do not reformat untouched code.
- Remove imports/variables your changes orphaned; do not delete pre-existing dead code unless asked.

### 4. Goal-driven execution
- Transform tasks into verifiable goals (a test that passes, a command that returns X).
- For multi-step work, write the plan in `tasks.md` of the active ticket.

## Workflow

Work happens inside **one ticket at a time** under `agent-workflow/tickets/`.
A ticket follows this loop:

1. `requirements.md` — what & why → **user approval gate**
2. `design.md` — how → **user approval gate**
3. `tasks.md` — verifiable checklist
4. Implementation, ticking tasks
5. `journal.md` — decisions and lessons
6. `review.md` — self-review + space for external review (Codex / human)

After closing a ticket, distill reusable insights into `agent-workflow/memory/`.

The active ticket is the one whose `status.md` says `in-progress`.

## Language
All workflow docs, code, comments and commit messages are in English.
The product spec under `context/doc/` is in Spanish and is the source of truth for product requirements.
