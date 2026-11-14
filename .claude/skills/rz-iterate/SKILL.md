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

1. **Drain the reap queue** (see "Reaping"). Merges first. Queued REAPs land
   together as one merge train with one gate; rooms don't rebase for it.
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
| starbux | `adele-starbux` | 1 | yes (2026-11-10) | 8 cores, 14 GB, ~9 GB free beside `adele`'s rooms. Smoke passes; `lld` is a user-local copy (`~/.local/opt/lld-21`). Hold lifted by Aaron 2026-11-11 (first room #2577) |
| chungus | `adele-chungus` | 1 | yes (2026-11-12) | 8 cores, 14 GB, ~5-8 GB free (another user's desktop session) and 47 GB disk free (95% used). Smoke passes. `clang`/`lld`/`llvm` 21.1.8; `lld` is a user-local copy (`~/.local/opt/lld-21`). Approved by Aaron 2026-11-12 |
| huburght | `adele-huburght` | 6 | yes (2026-11-11) | 12 cores, 47 GB (~42 GB free), WSL2 (gone if Windows sleeps). ssh `aaron@10.0.0.191` (name doesn't resolve). Smoke 38 s. `clang`/`lld`/`llvm` 21.1.2 installed 2026-11-11. 2 slots from 2026-11-12 (Aaron: "tons of memory free"; #2582 and #2780 merged cleanly). **6 slots from 2026-11-14 01:04Z** (Aaron, 2026-11-13; omegalisk stays at 2): #2998 landed as 62c9082a and huburght's `~/.config/rz/host.env` sets rooms 28G high / 32G max and 2 gate slots (`host-budget.sh --verify <room>` there shows them). Coarse mtime clock (#2689) |

- **Per-host budget: `~/.config/rz/host.env`** (AGAST #2998), read by
  `.claude/host-budget.sh` and `run-gate.sh`; format and validation in
  `.claude/host-env.sh`. Keys, all optional: `RZ_ROOMS_MEMORY_HIGH` and
  `RZ_ROOMS_MEMORY_MAX` (all of a host's rooms together, the
  `ritz-rooms.slice` caps) and `RZ_GATE_SLOTS` (gates at once on that host).
  No file means omegalisk's numbers, 7G / 8G / 1, unchanged: omegalisk,
  toffee, starbux and chungus have none. **huburght's file:**
  `RZ_ROOMS_MEMORY_HIGH=28G`, `RZ_ROOMS_MEMORY_MAX=32G`, `RZ_GATE_SLOTS=2`
  (32G rooms + 2 gates at ~3.5 GiB leaves ~8 GiB of 47 for the host; never
  more than 2 gates on 12 cores). After writing it, the host runs
  `.claude/host-budget.sh <room>` for any running room (or spawns one) so the
  slice is rewritten, and `.claude/host-budget.sh --verify <room>` prints the
  values in effect and where they came from. An unknown key or bad value is
  an error in both scripts, never a silent default.
- **Only Aaron, or `adele` (main) on his behalf, marks a host ready** or
  changes its slots. Edit this table and commit it on `main` when they do.
  A host's first room is a small, low-risk ticket.
- **Before a new host's first room**, check more than smoke: smoke doesn't
  use LLVM, so it passed on huburght with only LLVM 20 and the gate then
  failed at setup. Check `ls /usr/lib/llvm-21/bin/{clang,opt,llc,lld}` and
  `~/dev/.venv/bin/pip show pytest` (must be `<9.2`; 9.2.0 broke the toffee
  gate) as well.
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
  `assigned_agent`. Never record hosts in the scratchpad. Search by the
  exact claim name: `assigned_agent="ritz-task-2592"` finds nothing when
  the claim is `ritz-task-2592@toffee` (2026-11-11, a false "never
  claimed"). See "Who owns the ticket" for the whole claim-to-close path.
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
- **Push by refspec on remote hosts.** Plain `git fetch` / `git push` work
  on every host (the `ssh -F /dev/null` workaround from toffee 2026-11-11 is
  no longer needed; don't put it in briefings). Remote rooms push with the
  explicit refspec `git push --force-with-lease origin HEAD:refs/heads/ritz-task-<id>`.
  Host worktrees are created with `-b ... origin/main --no-track`, so the
  branch has no upstream and a bare `git push` has no target (and without
  `--no-track` it would aim at `main`). The explicit refspec is right
  either way; don't tell rooms their branch "tracks `main`" (huburght,
  2026-11-13).
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
"Hosts"; glance at GitHub CI (`gh run list`); build, gate and land merge
trains with `train.sh` (see "Reaping"), which cherry-picks REAPed commits
unchanged and runs `run-gate.sh` on the stack.

**Must not:** edit code, run any test or gate other than a train's, resolve a
conflict, edit, rebase or squash a room's branch, or investigate a failure.
Anything like that becomes an AGAST ticket and a room. If CI on `main` goes red with a *new* failure, file it at high priority
and spawn a room for it. Don't fix it here.

## Who owns the ticket

A ticket is closed when its code is on `main`, not when a room thinks it's
done. `rz` holds both ends; the room only works in between.

| Step | Who | What |
|---|---|---|
| Claim | `rz`, **before** anything is created | `claim_task` as `ritz-task-<id>` (omegalisk) or `ritz-task-<id>@<host>`. Check the reply says `executing` with that name; a claim conflict aborts the spawn. Spawn with `--no-claim`, and say in the briefing (and the `SPAWN`) which name holds it |
| Work | room | Reads the ticket and files new tickets for anything out of scope. **Never** claims, releases or completes its own ticket when it has a commit to REAP. The evidence goes in the REAP line |
| Close (merged) | `rz`, after `git push origin main` | `complete_task` with `Merged to main as <sha8>. <the REAP line>` |
| Close (already fixed) | room | REAP `none`: the room may `complete_task` with the evidence (briefing step 1). That's final: it makes no commit after it. If a test is still worth landing, `rz` files a new ticket for it |
| Abandon | `rz` | Torn down or `SPAWN-FAILED` without a merge: `release_task`, so the ticket is `ready` again |
| Wait on another | `rz` | `add_dependency`. The waiting room keeps its claim (e.g. #2582 holding for #2689) |

**`complete_task` refused ("must be in executing status")?** Don't move on.
Look the ticket up by its exact claim name. If the room closed it itself
(#2595 at 01:26 and #2592 17 s before its REAP, 2026-11-11), it's already
`completed`: check its `results` name the merged SHA, and if they don't, or
say something that's no longer true (#2595's said "REAP none" for a test that
then merged), append `MERGED to main as <sha8> (<date>)` to its description
with `update_task`. Then tell the room in one line that it broke "Who owns
the ticket". If it's `ready` or unclaimed instead, `claim_task` as `rz`,
then `complete_task`.

**After `TORNDOWN`**, the ticket must be `completed` (merged) or `ready`
(released). An `executing` ticket with no room behind it is a leak: fix it
in the same turn.

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

**"START poke sent" doesn't mean the room started.** Within ~2 minutes of
`adele room spawn`, check the room has posted a `claude_response` or tool use
(`get_conversation_messages`). If it's silent, re-send with
`adele room spawn <room> … --poke`. The poke is a live broadcast, not a
queued message: #2573's agent connected, lost its socket a second later and
reconnected 5 s after that, and the poke landed in the gap (2026-11-11; Aaron
had to re-poke it by hand). AGAST #2724 (adele) makes `adele room spawn`
wait for the turn to start and re-poke itself; keep this check until it has
landed and been confirmed here.

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
permissions OK". Trust is not per-worktree: for a worktree the CLI checks the
**main checkout's** key (`~/dev/ritz-lang/rz`) in
`${CLAUDE_CONFIG_DIR:-$HOME}/.claude.json`, so the script trusts that key as
well as the worktree's own (#2746). Without it the room's allow list is ignored,
and every `Write`, `rm` or `git push` waits on an approval nobody gives (#1378).
On cleanup, run `.claude/provision-room.sh --remove <worktree>` after
`git worktree remove`. That drops only the worktree's key. The main key stays,
because the parent room and every live room share it.

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

0. **Ask the host for `STATUS` first** and wait for the answer. Count its
   rooms from that reply, not from an earlier report: `adele` starts and
   stops its own rooms there, and a 1-hour-old count put #2577 on starbux as
   a 3rd room on a 2-slot host (2026-11-11). Don't send `SPAWN` and `STATUS`
   together; the host may act on the `SPAWN` before it reads the `STATUS`.
1. **Create the room on the server first**, as above (`send_room_message`
   "Room initialized for AGAST #<id>.", then `update_room_description`), so
   the remote agent doesn't crash-loop on HTTP 400.
2. **Claim the ticket here** as `ritz-task-<id>@<host>`, so the claim records
   the host, and confirm the result says `executing` with that name before
   sending `SPAWN`. The host spawns with `--no-claim`. Remote rooms have the
   AGAST tools (2026-11-10): they read the ticket and file new ones, but
   close it only for REAP `none` (see "Who owns the ticket").
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
   REAP `none`. That's final: commit nothing after it. This is the only time
   you touch your ticket's status. `rz` claimed it as `<claim name>` and
   closes it when your commit merges. Never claim, release or complete it
   yourself, even though your general instructions say to mark tasks done.
2. **Test first.** Write tests that fail for the reason they name, then fix.
   Mutation-check: break each part of the fix and confirm only its own tests
   go red. A pytest matrix is paid by every gate: size it to the rule, not
   the cross product, and read "What a ritz0 pytest case costs" in
   `projects/ritz/docs/TESTING.md` before adding hundreds of cases.
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
7. **Don't chase `main`.** REAP the commit you gated. `rz` usually lands it
   by cherry-picking it onto `main` in a batch with other rooms' commits and
   gating the batch, so it may reach `main` under a different SHA. You only
   rebase if `rz` tells you to.
8. **Push and REAP:** `git push --force-with-lease origin ritz-task-<id>`
   (remote rooms: `git push --force-with-lease origin
   HEAD:refs/heads/ritz-task-<id>`). Never `-f`/`--force`: the lease refuses
   to overwrite a branch someone else moved. If it's rejected as stale,
   `git fetch origin`, check `origin/ritz-task-<id>` is your own earlier
   push, and retry; if it isn't yours, stop and tell `rz`. Then exactly one:
   ```
   mcp__adele-context__send_room_message(
       room_id="rz",
       message="REAP ritz-task-<id> <full-sha> — <one line: what changed>",
       sender_name="ritz-task-<id>",
       ask_claude=True)
   ```
   A remote room's line also quotes its gate, before the dash:
   `REAP ritz-task-<id> <full-sha> gate <log name> SHA=<first 12> EXIT=0 — <one line>`.
   Don't `complete_task`: the REAP line is your evidence, and `rz` closes the
   ticket once your commit is on `main`.
9. **On "rebase onto <sha7>"** (your commit conflicted with `main` or failed
   the gate on top of it; the message says which, with the failing lines):
   rebase, fix if needed, re-gate, push and REAP again. Until that message,
   stay on your base, even after REAPing.

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
- **AGAST:** read your ticket and file new ones as a local room would. The
  ticket is claimed as `ritz-task-<id>@<host>`; leave its status alone
  (step 1). The ticket text is also pasted below. If an AGAST call fails, say so in your REAP, list
  follow-ups there (one line each: title, file:line, why) for `rz` to file,
  and for step 1 REAP `none` with the evidence.
- **Self-restart** (the `systemd-run` under "An MCP call rejected", below)
  works the same on this host.

<full AGAST ticket text>
````

## Reaping

**The scratchpad is the reap queue and nothing else.** One line per request,
nothing more than it takes to act on it:

```
reap ritz-task-1450 1a2b3c4
```

### Merge trains (Aaron, 2026-11-12)

Every REAP is one squashed commit that its room already gated on its own
base. Rather than have each room rebase and re-gate in turn (one ~25-minute
gate per merge), `rz` stacks every queued commit on `origin/main` in queue
order and gates only the top of the stack. If that passes, every commit
below it has passed too, and they all land in one push. This is the one
gate `rz` runs; it still never edits, rebases or fixes a room's commit.

`.claude/skills/rz-iterate/train.sh` does the git work in its own worktree,
`~/dev/ritz-lang/rz-train` (created on first use, detached HEAD, never a
room's). Tests: `bash .claude/skills/rz-iterate/test-train.sh`.

1. **REAP arrives:** (this section, not `/reap-ritz-room`, handles it)
   `append_scratchpad_item` immediately, even while a train is gating, then
   say in one line what's queued. Never add to a train that's gating: a REAP
   that arrives then rides the next train.
2. **Check each REAP line before it boards.** A remote room's REAP must
   quote `SHA=<12> EXIT=0` from its gate log, and that SHA must be the REAP
   SHA's prefix. Without it, it's a room mistake (step 7). (`train.sh build`
   checks the rest: the branch tip is the REAP SHA, and it's one commit.)
3. **Build the train** from every unchecked item, oldest first
   (`get_scratchpad` first, never from memory):
   ```bash
   .claude/skills/rz-iterate/train.sh build ritz-task-2593:3f42ab80 ritz-task-1844:4b699a83 ...
   ```
   It prints one line per item (`KEPT`, `APPLIED`, `CONFLICT`, `EMPTY`,
   `BAD`) and a `TRAIN ... n=<k> gate=<needed|not-needed>` summary.
   `rz-larb` boards like any room (`rz-larb:<sha>`).
4. **Gate it, unless `gate=not-needed`** (a lone commit already on `main`:
   its own gate covers it):
   ```bash
   LOG=$(.claude/skills/rz-iterate/train.sh gate)
   .claude/skills/rz-iterate/run-gate.sh --wait "$LOG"    # Bash run_in_background
   ```
   Run the wait with `run_in_background`, so it wakes this room when the gate
   ends, and keep the usual 1800 s fallback wakeup. Carry on with the loop
   (slots, nudges) meanwhile. On a context reset, `train.sh show` prints the
   train, and the newest `gate-logs/train-<sha12>.log` holds the gate. The
   train gate uses omegalisk's one gate slot, so it may wait behind a local
   room's gate.
5. **Gate passes (exit 0), or `gate=not-needed`:**
   ```bash
   .claude/skills/rz-iterate/train.sh land "$LOG"      # no log when not needed
   ```
   It refuses if the log isn't for the train's tip, didn't pass, or `main`
   moved since the build; then rebuild and re-gate. It pushes the tip to
   `main` (never forced), fast-forwards `~/dev/ritz-lang/rz`, and prints
   `MERGED <branch> <room sha12> as <main sha12>` per commit. For each:
   `complete_task` (`Merged to main as <main sha8> (train <tip sha8>). <REAP
   line>`; if refused, see "Who owns the ticket"), `check_scratchpad_item`,
   and clean up (`systemctl --user stop/disable adele-agent@ritz-task-<id>`,
   remove `~/.config/adele/rooms/ritz-task-<id>`, `.claude/host-budget.sh
   --remove ritz-task-<id>`, `git worktree remove`, `git branch -D`,
   `git push origin --delete ritz-task-<id>`).
   **Remote room:** send `TEARDOWN ritz-task-<id> merged=<main sha12>` to its
   host room instead of the local steps, and still delete the branch on
   GitHub here. Spell out in the message that the commit was cherry-picked,
   so `git cherry origin/main ritz-task-<id>` prints `- <sha>` (same patch),
   not nothing; a `+` line is fine only if `<main sha12>`'s subject matches
   the branch tip's. The slot is free once the host answers `TORNDOWN`.
6. **Gate fails:** find the culprit by halving. With `k` commits, rebuild
   with the first `ceil(k/2)` and gate that. If it passes, land it; the rest
   ride the next train. If it fails, halve again. A single commit that fails
   on top of `main` goes back to its room: check its item and send it one
   line, "rebase onto <main sha7>: your commit fails the gate on top of
   `main`", with the gate's failing lines (`run-gate.sh --wait` prints them).
   Its fixed REAP goes to the back of the queue. Never investigate the
   failure here.
7. **`CONFLICT`, `BAD` or a missing gate quote** leave that item out of the
   train. Once the train has landed, check the item and send its room one
   line: for `CONFLICT`, "rebase onto <new main sha7>, re-gate and REAP";
   otherwise, which check failed. Its next REAP goes to the back of the
   queue. **`EMPTY`** means the patch is already on `main`: check the item,
   then close and clean up as in step 5.
8. **All items checked:** `clear_scratchpad`.

**Never tell running rooms that `main` moved.** A room rebases only when its
own commit conflicted or failed (steps 6 and 7). Broadcasting made five rooms
re-gate at once, filling both gate slots with work that was stale again by
the next merge. Committing to `main` from this room (skill edits and the
like) needs no message either; it just becomes the next train's base.

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
through a train, and a commit that conflicts or fails sends its room back to
rebase and re-gate while the rest of the train lands.
