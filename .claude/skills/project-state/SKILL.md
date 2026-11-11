---
name: project-state
description: Produce the "state of the nation" breakdown of the Ritz stack (compiler → kernel → OS → desktop → productivity, plus the server/infra foundation) as widgets — a layer table, a critical-path diagram, a milestone roll-up chart and a pace chart. Use when Aaron asks "what's the project state", "where are we", "state of the nation", "progress report", "roadmap status", or wants the project-state widgets refreshed.
---

# project-state: the Ritz state of the nation

One report, four widgets, every number measured. The roadmap's own rule
(`projects/ritz/docs/ROADMAP.md`, "This document holds structure, not status")
applies here too: **status comes from commands and AGAST, never from memory or
from an earlier report.**

This skill is read-only. It may run from the `rz` main room: it does not edit
code, run gates or touch room branches.

## 1. Measure

```bash
.claude/skills/project-state/collect.sh > /tmp/project-state.json   # ~15 s
```

It fetches `origin/main` (use `--no-fetch` to skip) and outputs JSON with:

| Key | What | Feeds |
|---|---|---|
| `main` | SHA and subject being described | every widget title |
| `layers[]` | packages per layer, Ritz kLOC (live code only) | table |
| `unmapped_projects` | `projects/*` dirs not in the layer map | fix the map first |
| `ritz_parts_kloc`, `examples_kloc` | ritz1 / ritzlib split; the regression corpus (not counted as compiler) | table detail |
| `python_kloc.ritz0` | Python that M1.4 retires (`tooling` is rz/scripts) | compiler detail |
| `known_failures` | ritz0/ritz1 regression allowlists, matrix expected failures per compiler, `rz.toml` build excuses with their AGAST IDs | compiler, productivity rows |
| `pace` | commits and `ritz-task-N:` merges per month (committer date), last 7 days, today, total | pace chart |
| `ci.jobs` | per job on `main`: latest conclusion and the last green SHA in the scanned runs | CI line, corrections |
| `kernel.boot_gate_ci_files` | `.github` files that run qemu/OVMF; `[]` = **no boot gate** | kernel row |
| `kernel.lld_link_on_host` | can rooms link the UEFI loader here | kernel row |
| `rooms_live` | active `adele-agent@ritz-task-*` units | "running" line |

**The layer map lives in `collect.sh` (`LAYERS`), not here.** If
`unmapped_projects` is non-empty, add the package to a layer in `collect.sh`
before reporting.

## 2. Roll up the milestones (AGAST MCP)

AGAST links work to a roadmap item in one of two ways, and the IDs below use both:

- **Milestones (M1.x, M2.x) link by dependency.** Call `get_task_dependencies(task_id=ID)`:
  - total = `len(depends_on)`;
  - done = entries with `is_blocking: false`.

  For example, #1828 had 7 done of 21 on 2026-11-03.
- **Epics and phases (#46, #47, #48, #49–#52) link by subtask.** Call
  `search_tasks(parent_task_id=ID, limit=200)`:
  - total = the number of results;
  - done = results with `status == "completed"`.

  For example, #47 had 12 done of 27. Its `depends_on` holds only the previous phase.

For each ID, run both calls and use whichever finds more children. Write down
which one you used, so the next run counts the same way.

Run every call in one parallel batch. Large `search_tasks` results get saved to a
file; count them with
`jq -r '.result|fromjson|[length,(map(select(.status=="completed"))|length)]|@tsv' <file>`.
Don't read the whole file.

| Row label | AGAST | Track / epic |
|---|---|---|
| T0 Fast iter | #1801 | Track 0 |
| M1.1 Parity | #1828 | Track 1 (#46) |
| M1.2 One lang | #1829 | Track 1 |
| M1.3 Structure | #1812 (#1830 points at it) | Track 1 |
| M1.4 ritz1 default | #1831 | Track 1 |
| M2.1 Boot gate | #1839 | Track 2 (#48) |
| M2.2 ritz1 kernel | #1840 | Track 2 |
| M2.3 EC2 | #1841 | Track 2 |
| M2.4 Laptop | #1842 | Track 2 |
| M2.5 Caps | #1843 | Track 2 |
| T3 ritzlib | #47 | Track 3 |
| Tooling | #1833 | Tooling |
| P7 Desktop | #49 | parked phase |
| P8 Server stack | #50 | parked phase |
| P9 Browser | #51 | parked phase |
| P10 Self-development | #52 | parked phase |

Track totals (Track 1 "11/16" etc.) are the same roll-up on the epic IDs (#46, #48).
If the ROADMAP's track table changes, update this table from it. That table is
the authority.

**Decisions waiting on Aaron.** These are the hexagons in the diagram.
None are open as of 2026-11-10: #1854 (Drop) was decided as option (a), and
its parts are #2156–#2159. #1849 (AWS) and #1853 (laptop) were decided on
2026-11-08 (record: #2455).

Add new ones as they appear (ticket text asks Aaron to choose, approve or provide).
To re-check one, **don't** use `search_tasks(query="#ID")`: it searches text, so
it returns tickets that *mention* the ID, not the ticket itself. A ticket also
stays open after Aaron decides it, because the implementation hangs off it.
Instead, read the ticket's own description (via a child's `parent_task_id` or
`get_task_dependencies`) for a `DECISION` / `AARON <date>` header, and search
for a decision-record ticket (`search_tasks(query="DECISIONS (Aaron")`). The
11-09 report showed three hexagons that had already been decided because of this.

## 3. Decide each layer's State

Pick the **first** rule that matches, top to bottom:

| State | Accent | Rule |
|---|---|---|
| Self-hosts | success | the layer's main artifact builds itself and a CI job checks it (compiler: `ci.jobs.bootstrap` green) |
| Works on ritz0 | success | builds and tests pass under ritz0; the ritz1 build is unmeasured or partial |
| Builds, never booted in CI | warning | builds, but needs to boot and `kernel.boot_gate_ci_files` is `[]` |
| Builds, boot unverified | warning | userland that builds but has no boot or run test in CI |
| Parked | warning | the roadmap parks it (PHASE 7–10) and it is not broken outright |
| Mostly broken | danger | a core package is in `known_failures.build_excused`, or its tests fail in `test-all` |

If the evidence for a state is older than this run (e.g. "ritz1 builds 3/7
infra packages, measured Sep 12"), say so in `detail` with the date.

## 4. Emit the widgets

Send them in this order, in one message, after a one-line correction section
if anything earlier was wrong. Load `/widget` if the schema is unfamiliar. Fill
`<…>` from steps 1–3. Titles always carry `main <sha7>` and the measured date.

### 4a. Layer table

```json
{
  "widget_type": "table", "schema_version": 1,
  "title": "Ritz stack: the state of each layer (main <sha7>, <YYYY-MM-DD HH:MM> UTC)",
  "fallback_text": "<one sentence per layer: name, state, milestone count>",
  "data": {
    "columns": [
      { "key": "layer", "label": "Layer" },
      { "key": "pkgs", "label": "Packages" },
      { "key": "kloc", "label": "Ritz kLOC", "align": "right", "format": "number", "sortable": true },
      { "key": "milestone", "label": "Roadmap (done/total)" },
      { "key": "state", "label": "State", "conditional": { "rules": [
        { "op": "eq", "value": "Self-hosts", "accent": "success" },
        { "op": "eq", "value": "Works on ritz0", "accent": "success" },
        { "op": "eq", "value": "Builds, never booted in CI", "accent": "warning" },
        { "op": "eq", "value": "Builds, boot unverified", "accent": "warning" },
        { "op": "eq", "value": "Parked", "accent": "warning" },
        { "op": "eq", "value": "Mostly broken", "accent": "danger" }
      ] } }
    ],
    "rows": [
      { "layer": "<layers[i].layer>", "pkgs": "<packages, comma-separated>", "kloc": <ritz_kloc>,
        "milestone": "<Track/epic #id: done/total>", "state": "<step 3>",
        "detail": "**Done:** …\n\n**Open:** …\n\n**Today:** <merges touching this layer>" }
    ]
  }
}
```

Leave out the "Not a layer" row. In the compiler row's `detail`, give the ritz1
known-failure count against the previous report, the matrix excuses, and the
ritz0 Python kLOC.

### 4b. Critical path (mermaid)

Nodes are the milestones with `done/total`, and edges follow the ROADMAP's
dependency notes. Decisions waiting on Aaron are hexagons `{{…}}` with class `you`.

```
graph LR
  T0["T0 Fast iteration d/t"]:::<cls> --> M11["M1.1 ritz1 parity d/t"]:::<cls>
  T0 --> M21
  U1{{"#1854 Drop decision"}}:::you --> M12["M1.2 One language d/t"]:::<cls>
  M11 --> M14["M1.4 ritz1 by default d/t"]:::<cls>
  M12 --> M14
  M12 --> M22["M2.2 ritz1 builds kernel d/t"]:::<cls>
  M13["M1.3 Structural d/t"]:::<cls> --> M22
  K1844["#1844 land harland-main"]:::<cls> --> M21["M2.1 QEMU boot gate d/t"]:::<cls>
  M21 --> M22
  M21 --> M23["M2.3 EC2 d/t"]:::<cls>
  U2{{"#1849 AWS creds"}}:::you --> M23
  M23 --> M24["M2.4 Laptop d/t"]:::<cls>
  U3{{"#1853 laptop model"}}:::you --> M24
  M21 --> P7["P7 Desktop: parked"]:::parked
  T3["T3 ritzlib d/t"]:::<cls> --> P8["P8 Server stack d/t"]:::parked
  P7 --> P9["P9 Browser: parked"]:::parked
  P8 --> P9
  P9 --> P10["P10 Self-development"]:::parked
  M14 --> P10
  classDef near fill:#1f7a3f,color:#fff
  classDef wip fill:#1d4e89,color:#fff
  classDef ready fill:#2f6f8f,color:#fff
  classDef todo fill:#555,color:#fff
  classDef stuck fill:#8a5a00,color:#fff
  classDef parked fill:#3a3a3a,color:#bbb,stroke-dasharray:4
  classDef you fill:#8b1e1e,color:#fff
```

Node classes:
- `near`: at least 90% done;
- `wip`: some done, not near;
- `ready`: 0 done, startable now;
- `todo`: 0 done, waiting on an upstream milestone;
- `stuck`: waiting on a `you` hexagon;
- `parked`: PHASE 7–10.

Widget: `{"widget_type":"diagram","schema_version":1,"title":"Critical path: what blocks what (hexagons need you)","fallback_text":"<edges in prose>","data":{"format":"mermaid","source":"<above>"}}`.

### 4c. Milestone roll-up (bar)

```json
{ "widget_type": "chart", "schema_version": 1,
  "title": "Roadmap milestones: AGAST children done vs open", "style": { "accent": "info" },
  "fallback_text": "Done/open: <label d/o, …>",
  "data": { "chart_type": "bar",
    "x_axis": { "label": "Milestone", "key": "m" }, "y_axis": { "label": "Tickets" },
    "series": [ { "name": "Done", "key": "done" }, { "name": "Open", "key": "open" } ],
    "records": [ { "m": "<row label from step 2>", "done": <d>, "open": <o> } ] } }
```

Use the step-2 rows T0 to Tooling. Leave out the parked phases; the diagram shows them.

### 4d. Pace (bar)

The same shape as 4c, with `"accent": "success"` and the title "Pace: commits and
ticket branches merged to main". There's one record per month from `pace.by_month`,
with `{"month": "Mon", "commits": c, "tasks": t}`. Collapse runs of empty months
into a single label (e.g. "Jun–Aug" = 0/0); `by_month` omits them. Give the
current partial month as "Nov 1–3". Put `tickets_total`, `tickets_last_7d` and
`tickets_today` in the fallback text.

## 5. Prose after the widgets (short)

1. **Main points:** 3–4 bullets. Which layer moves fastest, what is blocked and on
   whom, and what is parked by design.
2. **Since last report:** merges and regressions, with ticket IDs.
3. **CI:** for each job, whether it is green or red on `main.sha`. For a red job,
   give `last_green` (or "not green in the last N runs").
4. **Needs you:** the open hexagon decisions, one line each.

## Rules

- **Every number has a source:** a `collect.sh` key or an AGAST call made this
  run. If you can't measure something now, write "last measured <date>" or leave
  it out. Never carry a figure over from an earlier report.
- **Corrections go first.** If this run contradicts something said earlier
  (a CI job you called green, a count), the report opens with the correction.
- **Compare like with like.** kLOC leaves out `projects/ritz/examples` (the corpus)
  and `docs/archive`, and Python counts only `projects/ritz/ritz0`. If you change
  the counting, say so in the report; the numbers won't be comparable with earlier ones.
- **Name tickets and packages, not just numbers.** "M1.2 1/17, waiting on #1854" is
  useful; "M1.2 6%" is not.
- **No status in files.** Don't write the results into ROADMAP.md or any doc. The
  report is the message; the method is this skill.
