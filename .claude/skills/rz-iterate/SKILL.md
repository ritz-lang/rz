---
name: rz-iterate
description: Run the rz room as a pure coordinator loop — spawn parallel ritz task rooms, trust their REAP callbacks, merge --ff-only in FIFO order, and keep going until ritz1 is a working self-hosted compiler.
user-invocable: true
---

# rz-iterate — the self-hosting loop

The `rz` room is a **coordinator only**. Rooms do the work and vouch for it; this
room picks the work, spawns rooms, merges their commits and keeps the pipeline
full. It keeps looping until the goal at the bottom of this file is met.

## The loop

Repeat until the goal is met:

1. **Drain the reap queue** (see "Reaping"). Merges first, because every merge
   moves `main` and the rooms still running rebase onto it.
2. **Fill free slots.** Up to **6 rooms** at once. Pick `ready` AGAST tickets that
   move the current milestone forward (see "Where to start"). Spawn every one
   that can run in parallel in the same turn.
   - Don't run two rooms that will rewrite the same heavily edited file
     (for example `ritz1/src/emitter*.ritz`, `ritz0/emitter_llvmlite.py`). Queue
     the second behind the first with an AGAST dependency instead.
3. **Nudge idle rooms.** A room with no journal activity for 30+ minutes and
   no REAP has probably ended its turn with work pending (#1533). Send it one
   message (`ask_claude=True`) stating its last known state and the current
   `main`, and tell it to resume.
4. **No tickets for the milestone?** Spawn a **survey room**: it measures the
   milestone, files one AGAST ticket per defect found, and REAPs with only its
   notes (or no commit at all; see "Survey rooms").
5. **Wait.** Schedule a long fallback wakeup (`ScheduleWakeup`, 1800s,
   prompt `/rz-iterate`). REAP messages arrive with `ask_claude=True` and wake
   the room sooner.

Each turn, the report to the user is short: what merged, what's running,
what's queued. No long write-ups.

## What the main room may and may not do

**May:** read/claim/create/update AGAST tickets; spawn rooms; read the
scratchpad; `git fetch`, `git merge --ff-only`, `git push origin main`; clean
up reaped worktrees, branches and units; glance at GitHub CI (`gh run list`).

**Must not:** edit code, run tests or gates, rebase or squash a room's branch,
or investigate a failure. Anything like that becomes an AGAST ticket and a
room. If CI on `main` goes red with a *new* failure, file it at high priority
and spawn a room for it. Don't fix it here.

## Spawning a room

Use the `/spawn-room` skill's mechanics (worktree, `adele install`,
`ADELE_NO_GATEKEEPER=1`, `systemctl --user start`, wait for connect, claim,
brief, verify the agent woke), with these ritz values:

| Parameter | Value |
|---|---|
| Room / branch / unit name | `ritz-task-<agast-id>` |
| Worktree | `~/dev/ritz-lang/rz-task-<agast-id>` (branch off `origin/main`) |
| Install from | `~/dev/nevelis/adele`, `--workspace` pointing at the worktree |
| Model | `opus` |
| Callback room | `rz` |

Create the room on the server **before** `systemctl start`, or the agent
crash-loops on HTTP 400. Use `send_room_message` ("Room initialized for AGAST
#<id>."); `update_room_description` does NOT create a room, it returns "not
found".

**Provision every worktree** with `.claude/provision-room.sh <worktree>` after
`git worktree add` and before starting the agent. It must print "room
permissions OK". Without it the worktree is untrusted, and every `Write` blocks
for 30 minutes on an approval nobody gives (#1378). On cleanup, run
`.claude/provision-room.sh --remove <worktree>` after `git worktree remove`.

**Before spawning, check the ticket isn't already fixed on `main`.** Many
`ready` tickets were fixed in-session and never closed (#1369 and #1372 were
found that way). A quick grep for the fix the ticket describes is enough; if
it's there, `complete_task` with the evidence instead of spawning. Also add a
"step 0: is it already fixed?" to each briefing.

### The briefing (send verbatim, with the placeholders filled)

````markdown
## Task Briefing — AGAST #<id>

**<title>**

<2-3 sentence summary. The ticket in AGAST is the full spec; read it.>

| Parameter | Value |
|---|---|
| AGAST Task | `#<id>` |
| Branch | `ritz-task-<id>` |
| Worktree | `~/dev/ritz-lang/rz-task-<id>` |
| Callback room | `rz` |

### You own this completely — `rz` will merge your commit WITHOUT re-testing it

`rz` trusts your REAP message. It runs `git merge --ff-only` on the SHA you send
and pushes. Nobody re-runs your tests. Your REAP vouches for that exact commit.

0. **Is it already fixed on `origin/main`?** If so, `complete_task` with the
   evidence and REAP `none`.
1. **Test first.** Write failing tests, confirm they fail for the reason they
   name, then fix. Mutation-check the fix: break each part and confirm only its
   own tests go red.
2. **Parallelise inside the room** with subagents (Agent tool) for
   independent work. Do NOT spawn rooms of your own; only `rz` merges.
3. **Out of scope?** File a new AGAST ticket and keep going. Don't widen the
   change.
4. **Finish on top of main:** `git fetch origin && git rebase origin/main`, then
   squash to **one commit** (`ritz-task-<id>: 🤖 <terse description>`).
5. **Run the gate on that commit**, detached so a new message can't kill it:
   ```bash
   LOG=$(~/dev/ritz-lang/rz/.claude/skills/rz-iterate/run-gate.sh ~/dev/ritz-lang/rz-task-<id> <id>)
   ~/dev/ritz-lang/rz/.claude/skills/rz-iterate/run-gate.sh --wait "$LOG"
   ```
   It runs a clean `make -C projects/ritz ci-local`, at most 2 gates at once
   machine-wide, and exits with the gate's code (98 = died with no verdict,
   99 = HEAD moved during the run; neither is a pass). If your change touches
   packages outside `projects/ritz`, also build them (`./rz build <pkg>`) and run
   their tests; compare any failure against `origin/main` before calling it
   pre-existing.
6. **Gate exit 0 is required.** On failure, fix, re-squash, re-run.
7. **If `origin/main` moved** while you worked, rebase again and re-run the gate.
   The SHA you report must sit directly on the current `origin/main`.
8. **Push your branch** (`git push -f origin ritz-task-<id>`), then send exactly one
   message:
   ```
   mcp__adele-context__send_room_message(
       room_id="rz",
       message="REAP ritz-task-<id> <full-sha> — <one line: what changed>",
       sender_name="ritz-task-<id>",
       ask_claude=True)
   ```
9. **If `rz` sends you back** ("rebase: main moved"), rebase onto `origin/main`,
   re-run the gate, push, and send a new REAP line.

**Never end a turn with work pending.** Nothing wakes you when a gate, subagent
or test run finishes after your turn ends (#1533). Run `run-gate.sh --wait` in
the foreground of the same turn. If you must end a turn early, schedule a
wakeup first.

**Never:** check out or push `main`, merge anything, remove your worktree, stop
your unit, or delete your branch. `rz` does all of that after merging.
````

## Reaping

**The scratchpad is the reap queue and nothing else.** One line per request,
nothing more than it takes to act on it:

```
reap ritz-task-1450 1a2b3c4
```

1. **REAP arrives:** (this section, not `/reap-ritz-room`, handles it) `append_scratchpad_item` immediately (even mid-reap), then
   say in one line what's queued. Don't interrupt a reap in progress.
2. **Take the oldest unchecked item** (`get_scratchpad` first, never from memory).
3. **Two checks only, no tests:**
   ```bash
   git fetch origin
   git rev-parse origin/ritz-task-<id>                  # must equal the REAP sha
   git merge-base --is-ancestor origin/main <sha>       # must be on current main
   test "$(git rev-list --count origin/main..<sha>)" = 1   # exactly one commit
   ```
4. **Pass:** `git merge --ff-only <sha> && git push origin main`. Then
   `complete_task` in AGAST, `check_scratchpad_item`, and clean up
   (`systemctl --user stop/disable adele-agent@ritz-task-<id>`, remove
   `~/.config/adele/rooms/ritz-task-<id>`, `git worktree remove`,
   `git branch -D`, `git push origin --delete ritz-task-<id>`).
5. **Fail (main moved, SHA mismatch, more than one commit):** don't touch the
   branch. Send the room one line with `ask_claude=True`, for example
   "rebase: main moved to <sha7>; re-gate and REAP again". Check the item
   (it's done; the room's next REAP goes to the back of the queue).
6. **All items checked:** `clear_scratchpad`.

GitHub CI: glance at `gh run list -L 3` each turn. Red on an already-known
failure set is normal (`test-all` has known reds). A **new** failure becomes a
high-priority ticket and a room. Don't block merges on CI.

## Survey rooms

When a milestone has no ready tickets, spawn `ritz-survey-<slug>` with the
same briefing, but its job is: measure, file one AGAST ticket per defect
(with repro, file:line, and suggested fix), and add dependencies between
them. If it commits nothing, its REAP line is `REAP ritz-survey-<slug> none`,
and reaping it means only cleanup.

## Goal: a working self-hosted ritz compiler

Done when all five hold on `main`:

1. **ritz1's known-failure list is empty**:
   `projects/ritz/scripts/regression-known-failures-ritz1.txt` (20 entries at
   the time of writing).
2. **ritz1 builds every package ritz0 builds** (`./rz build --all` with ritz1).
3. **ritz1 rejects everything ritz0 rejects**: same diagnostics for the
   rejection tests (e.g. `#1446`, narrowing; the else-less `if`).
4. **ritz1 has no hard-coded struct copies** (`register_builtin_structs` in
   `ritz1/src/emitter.ritz`, `#1440`); layouts come from the source.
5. **ritzlib is proper Ritz, not "C in Ritz's clothing"**: public APIs take
   slices, `String`, `Option`/`Result` and structs, not raw `*u8`/`**u8` and
   out-pointers.

### Where to start: ritzlib basics

Iterate from the bottom up:

1. **Every ritzlib module gets an example** under `projects/ritz/examples/` that
   uses it, and **both ritz0 and ritz1 compile and run it** with identical output.
   Missing examples and ritz1 failures become tickets.
2. **Start with `ritzlib/args.ritz`** (arg parsing built on `**u8` and raw pointers):
   give it an idiomatic API, keep the old one only as long as callers need it,
   and port callers in follow-up tickets.
3. Then work outward: `io`, `fs`, `buf`, `str`/`String`, `hashmap`, `json`,
   and so on, each as its own ticket.
4. In parallel, work down the ritz1 known-failure list and `#1440`.

Prefer many small tickets over one large one: small commits merge cleanly
through `--ff-only`, and a room that has to rebase repeatedly is wasted work.
