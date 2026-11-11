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

1. **Drain the reap queue** (see "Reaping"). Merges first. Only the room at
   the head of the queue ever rebases; see "One rebase at a time".
   **First, recover dropped REAPs:** a REAP turn can be interrupted by the
   next REAP's turn before it queues anything (1485 was lost this way twice).
   `get_conversation_messages(room_id="rz", message_type="chat", since=<last check>)`,
   and queue any REAP whose SHA is not on `origin/main`, not already in the
   scratchpad, and not already superseded by a newer REAP from the same room.
2. **Fill the free slots.** Slots are **per host** (see "Hosts"): omegalisk
   has **2** (user limit, 2026-10-24: 4 parallel rooms kill WSL with OOM
   from agents plus their builds and gates), and each remote host has the
   number in its row. Only hosts marked **ready** count. Never exceed a
   host's slots, survey rooms included. Spawn a new room only when a room
   on that host has merged or been paused. Fill omegalisk first; a remote
   host takes a room only when omegalisk is full.
   - **`rz-larb` (LARB retrospective, #1800) has given up its slot**
     (Aaron, 2026-10-25, after its three reviews merged), so both slots go
     to ritz task rooms. Its unit is stopped and its worktree and branch are
     kept. It's a long-lived room: bring it back for follow-up reviews only
     when Aaron asks. It doesn't take a slot when it runs (Aaron, 2026-11-07:
     the limit is for compiler CPU pressure, and LARB is a decision room), so
     brief it to stay light: no gates, one `ritz1` build or sweep at a time.
     Its REAP lines
     (`REAP rz-larb <sha>`) go through the normal queue, and after merging
     don't remove its worktree, unit or branch.
   - **Test-speed tickets from `rz-larb` (smoke tier, faster suite,
     IR/object caching; priority 90) come first**, ahead of ritz1 bug
     fixes (Aaron, 2026-10-25).
   - **Paused rooms come first.** A room whose agent unit is stopped and
     disabled (`systemctl --user disable --now adele-agent@ritz-task-<id>`) but
     whose worktree still exists is paused, not finished. Resume it
     (`enable --now`, then a message stating `main` and its last state) before
     spawning anything new. A paused remote room gets `RESUME
     ritz-task-<id>` sent to its host room (see "Hosts"), then the same
     message.
   - Otherwise pick `ready` AGAST tickets that move the current milestone
     forward (see "Where to start"), up to the limit.
   - Don't run two rooms that will rewrite the same heavily edited file
     (for example `ritz1/src/emitter*.ritz`, `ritz0/emitter_llvmlite.py`). Queue
     the second behind the first with an AGAST dependency instead.
3. **Nudge idle rooms.** A room with no journal activity for 30+ minutes and
   no REAP has probably ended its turn with work pending (#1533). Send it one
   message (`ask_claude=True`) stating its last known state and the current
   `main`, and tell it to resume.
   **A room that isn't working gets restarted, not worked around.** That
   covers 401 or expired-token errors in its journal, a `pending-mcp` file
   in its git dir (`.git/worktrees/rz-task-<id>/pending-mcp`), or no response
   to a nudge. Run `systemctl --user restart adele-agent@ritz-task-<id>`,
   then send it that nudge. It picks up the current token at startup. Never
   merge a commit the room hasn't REAPed, even with a passing gate log.
   **Remote rooms:** you can't read their journal or git dir. Send `STATUS`
   to the host room (see "Hosts") and judge from its last journal line per
   room. A room that isn't working gets `RESTART ritz-task-<id>` sent to the
   host room, then the same nudge sent to the room itself.
4. **No tickets for the milestone?** Spawn a **survey room**: it measures the
   milestone, files one AGAST ticket per defect found, and REAPs with only its
   notes (or no commit at all; see "Survey rooms").
5. **Wait.** Schedule a long fallback wakeup (`ScheduleWakeup`, 1800s,
   prompt `/rz-iterate`). REAP messages arrive with `ask_claude=True` and wake
   the room sooner.

Each turn, the report to the user is short: what merged, what's running
(and on which host), what's queued. No long write-ups.

## Hosts

Rooms run on omegalisk (this machine) or on a remote host (project Borque,
AGAST #2609). This room stays the only coordinator, and the reap queue
stays here; remote hosts only run rooms.

| Host | Host room | Ritz slots | Ready | Notes |
|---|---|---|---|---|
| omegalisk | (local: `systemctl`, `git worktree`) | 2 | yes | 12 cores, 15 GB, WSL |
| toffee | `adele-toffee` | 1 | yes (2026-11-10) | 8 cores, 14 GB, ~10 GB free. Linger on, `llvmlite` and `lld` 21 installed, smoke passes. First remote trial host |
| starbux | `adele-starbux` | 1 | yes (2026-11-10), **held** | 8 cores, 14 GB, ~11 GB free. Smoke passes; `lld` is a user-local copy (`~/.local/opt/lld-21`). No spawns until the toffee trial has reported to `adele` |
| chungus | `adele-chungus` | 1 | no | 8 cores, 14 GB, only ~5 GB free (another user's desktop session) and 47 GB disk. Smoke passes. Not ready until Aaron says so |

- **Only Aaron, or `adele` (main) on his behalf, marks a host ready** or
  changes its slots. Edit this table and commit it on `main` when they do.
  A host's first room is a small, low-risk ticket.
- **No harland/UEFI tickets on remote hosts** until an `lld`-linked harland
  build has passed there. No host has node or docker. No full gate has
  run on a remote host before the toffee trial; if a remote gate can't run,
  the room says so in place of a REAP, and nothing merges ungated.
- **One gate per host.** `run-gate.sh` locks slots under the host's own
  `~/dev/ritz-lang/gate-logs`, so a remote gate never waits on omegalisk's
  gate.
- **Which host a room is on is recorded in AGAST, in the claim's agent
  name:** `ritz-task-<id>` on omegalisk, `ritz-task-<id>@<host>` on a remote
  host. To see what's running where, list `executing` tickets and read
  `assigned_agent`. Never record hosts in the scratchpad.
- **Host room verbs** (always `send_room_message(room_id="adele-<host>",
  ..., sender_name="rz", ask_claude=True)`):
  - `SPAWN ritz-task-<id> repo=rz task=<id> callback=rz model=opus`, then
    the briefing. The host answers `SPAWNED ritz-task-<id> on <host>` or
    `SPAWN-FAILED ritz-task-<id> on <host>: <reason>`.
    `SPAWN` also fast-forwards the host's `~/dev/ritz-lang/rz` to
    `origin/main`, because `run-gate.sh` is read from there.
  - `RESTART ritz-task-<id>`: restarts a room that isn't working.
  - `TEARDOWN ritz-task-<id>`: removes the room's unit, budget, worktree and
    local branch after its merge. The host answers `TORNDOWN ritz-task-<id>
    on <host>` (one word, no hyphen); the slot is free from then. Refusal is
    `TEARDOWN-REFUSED ritz-task-<id> on <host>: <blocker>`.
  - `STATUS`: free memory, running rooms, each room's last journal line, and
    any room with a `pending-mcp` file or 401s in its journal.
  - `PAUSE` / `RESUME ritz-task-<id>`: disable and stop the unit, keeping the
    worktree and branch. Answered `PAUSED` / `RESUMED ritz-task-<id> on
    <host>`.
  - Every host answer is sent with `ask_claude=True`.
- **What to spell out in a host message.** All three hosts run the `borque`
  skill (adele `9db5b9a`, confirmed 2026-11-11), so `SPAWN` and `TEARDOWN`
  no longer need their steps written out. Until `adele` says PR #25 has
  landed and been pulled, still spell out inline:
  - the fast-forward of the host's `~/dev/ritz-lang/rz` to `origin/main`
    (first step of every `SPAWN`; refuse with `SPAWN-FAILED` if it won't
    fast-forward);
  - what `PAUSE` / `RESUME` do, if you send them.
  Every `SPAWN` still tells the host to **save the briefing with a Bash
  here-doc, never the `Write` tool**: `Write` outside the host's workspace
  waits on an approval nobody gives, and the host room stalls for up to 30
  minutes (starbux 2026-11-10, toffee 2026-11-11).
- **Git over ssh on remote hosts.** Under the agent's user namespace the
  host's `ssh_config.d` fails a permissions check, so plain `git fetch` /
  `git push` fail (toffee, 2026-11-11). Every remote briefing tells the room
  to use `GIT_SSH_COMMAND="ssh -F /dev/null"` for fetch and push, and to push
  with the explicit refspec `git push -f origin
  HEAD:refs/heads/ritz-task-<id>`. Host worktrees are created with
  `-b ... origin/main`, so the branch tracks `main`, and a bare `git push`
  would aim at `main`.
- **Shared hosts.** `adele` runs its own rooms on the same hosts (for
  example `task-2546` on toffee) within the host's slots. Never send
  `PAUSE`, `RESTART` or `TEARDOWN` for a room that isn't `ritz-task-*`. If
  a gate looks starved by one, message `adele` (main) and it will pause it.
  `adele` has ssh to every host; ask it to look if a host room goes quiet.
- **Host answers aren't REAPs.** `SPAWNED`, `SPAWN-FAILED`, `TORNDOWN`,
  `PAUSED`, `RESUMED` and `STATUS` replies never go in the scratchpad. On `SPAWN-FAILED`, release the claim
  (`release_task`), tell Aaron the reason in the turn report, and don't
  retry that host until the cause is fixed.
- **A host that doesn't answer within 10 minutes** (asleep, agent
  disconnected) is treated as not ready until Aaron says otherwise. Its
  rooms' tickets stay claimed; report them as stuck.

## What the main room may and may not do

**May:** read/claim/create/update AGAST tickets; spawn rooms; read the
scratchpad; `git fetch`, `git merge --ff-only`, `git push origin main`; clean
up reaped worktrees, branches and units; send host rooms the verbs in
"Hosts"; glance at GitHub CI (`gh run list`).

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
found". Once the room exists, give it a description from the ticket:
`update_room_description(room_id="ritz-task-<id>", description="...")`. The
room keeps the description current from then on (briefing step 0).

**Room descriptions** are one concise sentence saying what the room is doing:
about 20-30 characters, 60 at most (Aaron, 2026-10-25). For example "Lower
build priority for rooms" or "Re-gating after rebase".

**Provision every worktree** with `.claude/provision-room.sh <worktree>` after
`git worktree add` and before starting the agent. It must print "room
permissions OK". Without it the worktree is untrusted, and every `Write` blocks
for 30 minutes on an approval nobody gives (#1378). On cleanup, run
`.claude/provision-room.sh --remove <worktree>` after `git worktree remove`.

**Put every room on the machine budget** with `.claude/host-budget.sh
ritz-task-<id>` before `systemctl --user start` (it must print "host budget
OK"). It moves the room's unit into `ritz-rooms.slice`: CPUWeight=20,
MemoryHigh=3.5G / MemoryMax=5G per room, 8G for all rooms together. Gates run in
`ritz-gate.slice` at CPUWeight=100 (`run-gate.sh` does that). Without it the
gate competes with the rooms on equal terms and its wall time doubles (#1811).
The cap is per room, not per command, so a room can't bypass it by running
`make` directly. It applies from the unit's next start. On cleanup, run
`.claude/host-budget.sh --remove ritz-task-<id>`.

**Before spawning, check the ticket isn't already fixed on `main`.** Many
`ready` tickets were fixed in-session and never closed (#1369 and #1372 were
found that way). A quick grep for the fix the ticket describes is enough; if
it's there, `complete_task` with the evidence instead of spawning. Also add a
"step 0: is it already fixed?" to each briefing.

### Spawning on a remote host

You can't run `git worktree`, `systemctl`, `provision-room.sh` or
`host-budget.sh` there; the host room does all of that. What stays here:

1. **Create the room on the server first**, as above (`send_room_message`
   "Room initialized for AGAST #<id>.", then `update_room_description`), so
   the remote agent doesn't crash-loop on HTTP 400.
2. **Claim the ticket here** as `ritz-task-<id>@<host>`, so the claim records
   the host. Remote rooms have the AGAST tools (2026-11-10) and use them
   like local rooms: read, complete and file tickets themselves.
3. **Send `SPAWN`** to `adele-<host>`: the verb line, then the briefing below
   with the remote additions filled in. The host creates
   `~/dev/ritz-lang/rz-task-<id>` off `origin/main`, provisions it, puts it
   on the budget, installs, starts it and sends it the briefing.
4. **Wait for `SPAWNED`** (it wakes this room). Then check the agent woke
   by watching for its first room message or description change, not by
   reading a journal. No answer in 10 minutes: send `STATUS`.

Paths in the briefing (`~/dev/ritz-lang/...`) are the same on every host.
`run-gate.sh` is read from the host's own `~/dev/ritz-lang/rz` checkout, so
the host must keep that checkout on current `origin/main`; the SPAWN's fetch
covers it.

### The briefing (send verbatim, with the placeholders filled)

````markdown
## Task Briefing — AGAST #<id>

**<title>**

<2-3 sentence summary. The AGAST ticket is the full spec; read it.>

Room and branch `ritz-task-<id>`, worktree `~/dev/ritz-lang/rz-task-<id>`,
callback room `rz`.

### You own this: `rz` merges your commit without re-testing it

`rz` runs `git merge --ff-only` on the SHA you REAP and pushes it. Your REAP
vouches for that exact commit.

0. **Keep your room description current.** Whenever your focus changes, call
   `update_room_description(room_id="ritz-task-<id>", description="...")`: one
   concise sentence, about 20-30 characters, 60 at most ("Fix ritz1 slice
   bounds checks", "Re-gating after rebase").
1. **Already fixed on `origin/main`?** `complete_task` with the evidence and
   REAP `none`.
2. **Test first.** Write tests that fail for the reason they name, then fix.
   Mutation-check: break each part of the fix and confirm only its own tests
   go red.
3. **Subagents (Agent tool) for parallel work.** No rooms of your own.
4. **Out of scope?** File an AGAST ticket. Don't widen the change.
5. **Finish on main:** `git fetch origin && git rebase origin/main`, then
   squash to one commit: `ritz-task-<id>: 🤖 <terse description>`.
   Then run `make -C projects/ritz smoke` (≤ 2 min) before requesting a
   gate; fix anything it reports first. A gate slot is one machine-wide.
6. **Gate that commit**, detached so a new message can't kill it:
   ```bash
   LOG=$(~/dev/ritz-lang/rz/.claude/skills/rz-iterate/run-gate.sh ~/dev/ritz-lang/rz-task-<id> <id>)
   timeout 540 ~/dev/ritz-lang/rz/.claude/skills/rz-iterate/run-gate.sh --wait "$LOG"
   ```
   Run the wait in the foreground and repeat it on exit 124, which only means
   the slice ran out. It runs a clean `make -C projects/ritz ci-local` over CI's `build-all`
   and `bootstrap` jobs (#2141), one gate machine-wide, and exits with the
   gate's code (98 = no verdict, 99 = HEAD moved; neither passes). A
   `SETUP ERROR` line means a missing tool on this machine (e.g. lld-link
   for harland), not a regression: fix the machine and re-gate. The gate runs at full CPU weight; your room runs at CPUWeight=20
   under a 5G memory cap, so room builds can't starve it (#1811). Don't
   escape the cap with your own `systemd-run`. If you touched packages
   outside `projects/ritz`, also `./rz build <pkg>` and run their tests;
   compare failures against `origin/main` before calling them pre-existing.
   **Only exit 0 passes.**
   Otherwise fix, re-squash, re-run.
7. **Don't chase `main`.** REAP the commit you gated. `rz` tells you when to
   rebase.
8. **Push and REAP:** `git push -f origin ritz-task-<id>` (remote rooms:
   `GIT_SSH_COMMAND="ssh -F /dev/null" git push -f origin
   HEAD:refs/heads/ritz-task-<id>`), then exactly one:
   ```
   mcp__adele-context__send_room_message(
       room_id="rz",
       message="REAP ritz-task-<id> <full-sha> — <one line: what changed>",
       sender_name="ritz-task-<id>",
       ask_claude=True)
   ```
9. **On "your turn: rebase onto <sha7>"**: rebase, re-gate, push and REAP
   again straight away. Nothing merges until you do. Until that message, stay
   on your base, even after REAPing.

**Never end a turn with work pending:** nothing wakes you when a gate,
mutation run or subagent finishes (#1533). Wait in the foreground, in slices
under 10 minutes, for anything long. The harness ends a turn after 600s of
silence on a background wait, and a `Monitor` or wakeup can be lost with it
(#2333). The gate is detached, so `timeout` only ends the wait.

**An MCP call rejected (401, expired or invalid token)? Restart yourself.**
Don't retry, and don't work around it. Your token is read once, at startup
(#2546). Save the message you were sending, schedule your own restart, and
end your turn:
```bash
P=$(git rev-parse --git-dir)/pending-mcp   # outside the tree, never committed
printf '%s\n' "REAP ritz-task-<id> <full-sha> — <one line>" > "$P"
systemd-run --user --on-active=15 systemctl --user restart adele-agent@ritz-task-<id>.service
```
On every rejoin, check for that file first. If it's there, send its line
exactly as in step 8, then delete it.

**Never** check out or push `main`, merge anything, remove your worktree,
stop or disable your unit (the scheduled restart above is the one
exception), or delete your branch. `rz` does that after merging.
````

**Remote additions to the briefing** (only for a room on a remote host;
add them after the room line):

````markdown
You're on **<host>**, not omegalisk. `rz` can't read your files or journal,
so:

- **Your REAP must quote the gate's verdict:** add `gate <log name>
  SHA=<first 12> EXIT=0` to the REAP line, copied from the log. `rz` checks
  that the SHA matches the one you REAP.
- **AGAST:** use your AGAST tools as a local room would. The ticket text
  is also pasted below. If an AGAST call fails, say so in your REAP, list
  follow-ups there (one line each: title, file:line, why) for `rz` to file,
  and for step 1 REAP `none` with the evidence.
- **Self-restart** (the `systemd-run` above) works the same on this host.

<full AGAST ticket text>
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
   These work from `origin/ritz-task-<id>`, so they're the same for a remote
   room. A remote room's REAP must also quote `SHA=<12> EXIT=0` from its
   gate log, and that SHA must be the REAP SHA's prefix. A REAP without it
   is a room mistake (step 7). Its gate log stays on its host; ask the host
   room for it only if CI later goes red on that commit.
4. **Pass:** `git merge --ff-only <sha> && git push origin main`. Then
   `complete_task` in AGAST, `check_scratchpad_item`, and clean up
   (`systemctl --user stop/disable adele-agent@ritz-task-<id>`, remove
   `~/.config/adele/rooms/ritz-task-<id>`, `.claude/host-budget.sh --remove
   ritz-task-<id>`, `git worktree remove`,
   `git branch -D`, `git push origin --delete ritz-task-<id>`).
   **Remote room:** send `TEARDOWN ritz-task-<id>` to its host room instead
   of the local steps, and still run `git push origin --delete
   ritz-task-<id>` here. Its slot is free once the host answers `TORNDOWN`.
5. **Not on current main (the usual case):** this room is next, so it gets
   the turn. Send it one line with `ask_claude=True`:
   "your turn: rebase onto <sha7>, re-gate and REAP again". Leave its item
   **unchecked** at the head; it keeps its place. Then **stop merging** until
   that room REAPs again, even if a later item would fast-forward cleanly.
   Merging anything else would move `main` under the rebase and waste its gate.
6. **The head room's new REAP:** check its old item and handle the new one
   next, wherever the scratchpad put it (it holds the turn). Run step 3
   again. It only fails if something else moved `main`; if so, give it the
   turn again.
7. **SHA mismatch or more than one commit:** these are the room's mistakes.
   Send it one line saying which check failed, check the item, and move on;
   its next REAP goes to the back of the queue.
8. **All items checked:** `clear_scratchpad`.

### One rebase at a time

Rebasing is serialised through the queue, not broadcast:

- **Never tell running rooms that `main` moved.** No "main moved, rebase"
  messages to rooms that aren't at the head of the queue, whether they're
  still working, gating or already REAPed. They keep their base until their
  turn. (Broadcasting made five rooms re-gate at once, filling both gate
  slots with work that was stale again by the next merge.)
- **Exactly one room holds the turn at a time**: the head of the queue. On a
  context reset, the head is the oldest unchecked scratchpad item. If its
  room was already sent "your turn", don't send it again unless the room has
  been idle for 30+ minutes (see "Nudge idle rooms").
- **A room holding the turn that goes quiet** gets the usual idle nudge. If it
  still can't produce a gated REAP (its rebase conflicts or the gate fails),
  check its item, tell it to REAP again when it's fixed, and give the turn
  to the next item.
- **Committing to `main` from this room** (skill edits and the like) doesn't
  need any rooms told; the head room finds out when its turn comes.

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
through `--ff-only`, and a room's rebase and re-gate hold up the whole queue.
