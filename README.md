# IoT Platform — CropDataSpace

IoT platform for the **CropDataSpace** project: ingest, store, query and
analyze agricultural sensor data.

- **Product specification (Spanish, source of truth):** [`context/doc/`](context/doc/)
- **Development plan and how this repo is built:** [`agent-workflow/`](agent-workflow/)
- **Repository remote:** https://github.com/nullpointer010/iotplatform

> The actual platform code lives under `platform/` (created during ticket
> `0001-platform-skeleton-audit`). Until that ticket lands, the only working
> draft is the historical reference under [`context/platform/`](context/platform/).

---

## How this repository is built — the agent workflow

This is **not a hand-written codebase**. It is built by an LLM agent
(Claude / GitHub Copilot) following a strict, spec-driven, ticket-based
workflow defined in [`agent-workflow/`](agent-workflow/).

The workflow has three goals:

1. **No drift.** The agent works on **one ticket at a time** and is only
   allowed to touch what that ticket scopes.
2. **No throwaway work.** Every ticket goes through `requirements → design →
   tasks → implementation → review`, with **explicit human approval gates**.
3. **Cumulative memory.** Lessons from each ticket are distilled into
   `agent-workflow/memory/` so the agent gets smarter over time instead of
   repeating mistakes.

### File map (top level)

| Path | Purpose |
|---|---|
| [`AGENTS.md`](AGENTS.md) | Behavior rules read by every agent (Copilot, Claude Code, Codex, Cursor, Aider). |
| [`.github/copilot-instructions.md`](.github/copilot-instructions.md) | One-line pointer to `AGENTS.md` for VS Code Copilot. |
| [`agent-workflow/`](agent-workflow/) | Workflow definition, charter, roadmap, templates, ticket folder. |
| [`agent-workflow/README.md`](agent-workflow/README.md) | Detailed explanation of the loop. **Read this first if you are an agent.** |
| [`agent-workflow/roadmap.md`](agent-workflow/roadmap.md) | Ordered list of tickets per phase. |
| [`agent-workflow/tickets/`](agent-workflow/tickets/) | One folder per ticket. |
| [`context/`](context/) | Frozen product spec and historical draft code. |
| `platform/` | The platform code (created by ticket 0001). |

### The loop (per ticket)

```
1. requirements.md  ─── USER APPROVAL ───
2. design.md        ─── USER APPROVAL ───
3. tasks.md         (verifiable checklist)
4. implementation   (tick tasks)
5. journal.md       (decisions + lessons)
6. review.md        (self-review + external review) ─── USER APPROVAL TO CLOSE ───
7. distill lessons → agent-workflow/memory/
```

Only the ticket whose `status.md` says `in-progress` is being implemented
right now. All others are either `planning`, `review`, `done` or stubs in the
roadmap.

---

## How to drive the agent

You (the human) are the product owner. Your role is to **approve gates** and
**answer open questions**. The agent does the rest.

### Starting a session

Open the workspace in VS Code with Copilot Chat (or any agent that respects
`AGENTS.md`) and say:

> Read `AGENTS.md` and `agent-workflow/README.md`. What is the active ticket
> and what is the next thing you need from me?

The agent will:
- locate the active ticket (the one whose `status.md` is `in-progress` or
  `planning`),
- report the current phase,
- ask for the next approval or answer it needs.

### The five things you ever say

| Situation | What to say |
|---|---|
| The agent shows you a fresh `requirements.md` | `approved`, or `changes: <what to change>`, or `reject` |
| The agent shows you a fresh `design.md` | same three options |
| The agent reports tasks completed | `next`, or `changes: <what>` |
| The agent shows `review.md` for closure | `close`, or `changes: <what>` |
| You want a new top-of-roadmap ticket | `start ticket NNNN` |

Every approval is recorded by the agent in `journal.md` with a date stamp.

### Picking the next ticket

Tickets are listed in [`agent-workflow/roadmap.md`](agent-workflow/roadmap.md).
After closing a ticket, ask:

> Pick the next ticket from the roadmap, create its folder from the
> templates, and draft `requirements.md`. Stop at the approval gate.

If you want to **change** the next ticket's scope or order, edit
`agent-workflow/roadmap.md` directly (or tell the agent to).

### Adding an external review (e.g. Codex / human)

After implementation, the agent fills the **Self-review** section of
`review.md`. You then paste any external review (from Codex, another model,
or a human) into the **External review** section of the same file and tell
the agent:

> Address the external review on ticket NNNN.

The agent will either patch the code or open follow-up tickets.

---

## Local development

The dev stack will be driven by a top-level `Makefile` after ticket 0001:

```bash
make up        # start the platform
make down      # stop it
make logs      # tail logs
make test      # run the test suite (added by ticket 0003)
```

Until ticket 0001 closes, follow the instructions in
[`context/platform/`](context/platform/) (historical draft, may be stale).

---

## Tech stack (target, end of Phase 1)

- **API:** FastAPI (Python)
- **Context broker:** FIWARE Orion + MongoDB
- **Time-series:** QuantumLeap + CrateDB
- **Relational:** PostgreSQL
- **Auth:** Keycloak
- **Frontend:** Next.js + TypeScript + Tailwind + Radix UI
- **Tests:** pytest + testcontainers-python (backend), Jest + testcontainers
  (frontend integration)
- **Orchestration:** Docker Compose for dev; Kubernetes deferred

Phase 2/3 components (MQTT, MinIO, Superset, H2O, Node-RED, NiFi, Airflow,
Prometheus/Grafana) are listed in [`agent-workflow/charter.md`](agent-workflow/charter.md)
but explicitly out of scope for v1.

---

## Language

- All code, comments, commit messages and `agent-workflow/` docs are in
  **English**.
- The product spec under `context/doc/` is in **Spanish** and is the
  authoritative source for product requirements.
