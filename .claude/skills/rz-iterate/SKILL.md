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
4. **Keep the AGAST tree whole** (Aaron, 2026-11-17 restructure). Every
   open ritz ticket is in project 1 with a parent that leads to one of the
   six roots: #46 Language (M1.1 #1828, M1.2 #1829 + LARB R54–R67 #3786,
   M1.3 #1830 → #1812, M1.4 #1831 + ritz0 maintenance #3787), #48 Kernel
   (M2.1–M2.5), #47 ritzlib, #1833 Tooling & gate, #50 Foundation, or the
   parked #49/#51/#52.
   - **Empty Triage (#3788) every cycle:** re-parent each child under its
     milestone (`update_task(parent_task_id=...)`), fold it into an
     existing ticket, or close it.
   - **Catch orphans:** `search_tasks(project_id=1, parent_task_id=0,
     completed=False, count_only=True)` should return 8 (the root tickets
     themselves). `search_tasks(project_id=0, completed=False, query="ritz")`
     finds ritz tickets filed with no project. It should return only
     #2508 and #2986 (DOKS work, which has no project of its own). AGAST
     work lives in project 70 "AGAST" (#1297 moved there 2026-11-18).
     Place anything else you find.
   - **Briefing `<milestone>`** is the parent of the ticket being worked
     (Triage #3788 if it has none).
5. **No tickets for the milestone?** Spawn a **survey room**: it measures the
   milestone, files one AGAST ticket per defect found, and REAPs with only its
   notes (or no commit at all; see "Survey rooms").
6. **Wait.** Schedule a long fallback wakeup (`ScheduleWakeup`, 1800s,
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
| toffee | `adele-toffee` | 2 | yes (2026-11-10) | 8 cores, 14 GB, ~10 GB free. Linger on, `llvmlite` and `lld` 21 installed, smoke passes. First remote trial host. **2 slots from 2026-11-14** (Aaron) |
| starbux | `adele-starbux` | 2 | yes (2026-11-10) | 8 cores, 14 GB, ~9 GB free beside `adele`'s rooms. Smoke passes; `lld` is a user-local copy (`~/.local/opt/lld-21`). Hold lifted by Aaron 2026-11-11 (first room #2577). **2 slots from 2026-11-14** (Aaron) |
| chungus | `adele-chungus` | 2 | yes (2026-11-12) | 8 cores, 14 GB, ~5-8 GB free (another user's desktop session) and 47 GB disk free (95% used). Smoke passes. `clang`/`lld`/`llvm` 21.1.8; `lld` is a user-local copy (`~/.local/opt/lld-21`). Approved by Aaron 2026-11-12. **1 slot while minecraft is running** (Aaron, 2026-11-14). **2 slots from 2026-11-16 04:50Z** (Aaron, with minecraft stopped). No host.env, so both rooms share the default 7G/8G slice. Watch the disk |
| huburght | `adele-huburght` | 8 | yes (2026-11-11) | 12 cores, 47 GB (~42 GB free), WSL2 (gone if Windows sleeps). ssh `aaron@10.0.0.191` (name doesn't resolve). Smoke 38 s. `clang`/`lld`/`llvm` 21.1.2 installed 2026-11-11. 2 slots from 2026-11-12 (Aaron: "tons of memory free"; #2582 and #2780 merged cleanly). **6 slots from 2026-11-14 01:04Z** (Aaron, 2026-11-13; omegalisk stays at 2): #2998 landed as 62c9082a and huburght's `~/.config/rz/host.env` sets rooms 28G high / 32G max and 2 gate slots (`host-budget.sh --verify <room>` there shows them). **8 slots from 2026-11-15 16:50Z** (Aaron, while bangerang leaves the LAN: "maybe it can handle 8 rooms … even 12 would work"; go to 12 once 8 has run cleanly). **16 slots from 2026-11-16 04:50Z** (Aaron). **12 slots, spawn while load1 < 25, from 2026-11-16 05:47Z** (Aaron: slower rooms and gates are fine, because more run in parallel; at 16 the load sat at 18–25 on 12 cores and load1 < 14 held spawns back). **8 slots from 2026-11-16, draining** (Aaron: "it seems to be struggling … ease back to 8 and don't go over"): the 12 rooms running then finish normally; nothing is cancelled. No new huburght spawn until fewer than 8 rooms are running, then never more than 8. Baseline at 5 rooms + 2 gates: agents ~0.8 GiB RSS each, gates ~2.5–3 GiB each in `ritz-gate.slice` (no memory cap there; `RZ_GATE_SLOTS` bounds it), 35 GiB free. Coarse mtime clock (#2689) |
| bangerang | `adele-bangerang` | 6 | yes (2026-11-16) | 10.0.0.224, 61 GiB, ~39 GB disk free (92% used): watch the disk. Ubuntu 26.04, qemu 10.2.1, OVMF 2025.11. **6 slots** (Aaron, 2026-11-16: "bangerang is up and ready"). `/tmp` `noexec` removed; host key `SHA256:jEVBo2Sd…mYI6Q` checked. Full gate passes apart from lexis (`bangerang-setup-d43dae956cb1-4.log`). The test-uefi-boot step stalled once in firmware (1 of 6 runs, cause unknown): send `adele` the gate log if it recurs. `host.env` 20G / 24G, 2 gate slots. First room #1540; its gate runs (venv found). Ramp up from 1 room. **Disk: ~20 GB free is enough** (Aaron, 2026-11-18: "20GB is plenty"; no spawn hold for disk at that level). When it gets tight, clear Ritz caches there (`~/.cache/ritz`, old `/tmp/pytest-of-aaron` runs, orphaned `rz-task-*` worktrees) rather than holding spawns: 6 GB freed that way on 2026-11-18 (20 → 26 GB) |
| skronk, skronk-2, skronk-3 | `adele-skronk`, `adele-skronk-2`, `adele-skronk-3` | 16 each | yes (2026-11-18), **ephemeral** | **Three boxes from 2026-11-18 ~21:00Z** (Aaron: "register skronk-2 and skronk-3 for work, same specs as skronk"): skronk-2 was spot-terminated ~20:15Z (us-east-1c again; 10 of its 15 rooms had REAPed, the other 5 were re-spawned on bangerang) and relaunched; skronk-3 is new. Deadlines: skronk and skronk-2 02:54Z, skronk-3 08:55Z (`terraform output deadlines_utc`), so long tickets go on skronk-3. Each host's `public_ips` entry goes in `~/.ssh/rz_hosts`. **16 rooms per box from 2026-11-18 15:42Z** (Aaron). At 24, skronk-2 sat at load 119-126 on 36 vCPUs with memory fine (40G free), and gates went false-red on time-outs (#3554's `[Test workspace]` got SIGTERM with every test passing). A box over 16 drains: its rooms finish, and it takes no SPAWN until it's below 16. Spawn on the box with fewer rooms first. **Relaunched 14:54Z 2026-11-18** after both boxes were lost (likely a spot reclaim, ~09:20Z): new IPs in `~/.ssh/rz_hosts`, deadline 02:54Z (both). **Since 06:54Z 2026-11-18: two boxes, EC2 spot c5.9xlarge (36 vCPU, 72 GiB / 68 usable, 200 GB gp3)**, `instance_count = 2`. skronk dies 15:59Z, skronk-2 18:19Z (each counts from its own first apply). **24 rooms per box** (Aaron, 07:00Z), no load hold (spawn unless MemAvailable < 10 GiB). `host.env` 44G / 50G rooms, `RZ_GATE_SLOTS=6` (4 room + 2 train), the Terraform defaults. **Spot losses on 2026-11-18, all in us-east-1c:** the first c5.9xlarge at about 06:15Z (19 rooms), then a c5.12xlarge pair (06:20–06:50Z, 32 rooms + 2 train slots each, 64 rooms lost within 30 minutes). Pin another AZ at the next launch (Aaron: "elsewhere"; the boxes are ephemeral, so no disk has to follow). After the second loss, 23 of 63 rooms had pushed work. Those plus the 25 highest-priority of the rest came back, and the other 15 were released to ready. 12xlarge sizing, for reference: 60G / 66G rooms. Don't add `RZ_TRAIN_SLOTS` to `host.env` until #4031 lands: the parser rejects unknown keys, and every gate on the box, train gates included, fails to start (`gate --next skronk-2`, 06:33Z). Train 2's speculative gate can run on a skronk (`train.sh gate --next skronk-2`). **Spot loss (06:15Z):** the first skronk was terminated while Aaron applied the second box and took `adele-skronk` and 19 rooms with it. Those rooms were re-spawned under the same room IDs: a re-spawned room reads its original briefing from its own room history and resets to its pushed `ritz-task-<id>` branch if there is one, and its claim moves to `ritz-task-<id>@<new box>`. That's why briefings tell rooms to push every commit. Long-running tickets go on the box with the later deadline. Before 06:20Z: one c5.9xlarge (36 vCPU, 72 GiB, 200 GB gp3), Ubuntu 26.04, built and torn down by Terraform in `~/dev/nevelis/lab/skronk` (AGAST #3996; Aaron runs `terraform apply`/`destroy`). **It dies at a deadline** (`terraform output deadline_utc`; `/run/skronk-minutes-left` on the box): it powers itself off then, and EventBridge terminates it 10 minutes later. Unpushed work is lost, so every briefing says to push often and to report by deadline − 20 min; tear rooms down (or let them go) before the deadline, and `release_task` anything that didn't REAP. The public IP changes every launch: update `Host skronk` in `~/.ssh/rz_hosts` from `terraform output rz_hosts_entry`. Remotes are https via `gh`. `host.env` 48G / 54G, 4 gate slots. First run 2026-11-18 04:25Z: 12 rooms at load1 ~13. Smoke 28.6 s. **24 slots from 2026-11-18 05:50Z** (Aaron: "crank skronk up … go to 24"): `ttl_minutes` 720 (deadline 15:59Z) and `root_volume_gb` 200 applied in place, root grown online (growpart + resize2fs) |

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
- **A slow host's suite budget: `RZ_TEST_BUDGET_SCALE=1.5` in `host.env`**
  (AGAST #4138, for #4004's budget false reds). This is a number > 0, and
  `host.env` refuses anything else. The gate's ritz0 suite budget
  (`tools/check_test_budget.py`, `[suite] cpu_s` and every per-file cap) is
  multiplied by it on that host. `run-gate.sh` puts it in the gate unit's
  environment and logs it in the header (`BUDGET_SCALE=`). main.yml's ritz0
  step then takes it out of the environment and hands it to the budget check
  alone, as `RITZ_TEST_BUDGET_SCALE`, so no pytest sees it. `RZ_TEST_BUDGET_SCALE`
  in the caller's environment overrides the file for one gate. **Never
  `systemctl --user set-environment RITZ_TEST_BUDGET_SCALE=...`** (what #4004
  did at 17:35Z on 2026-11-18). Every process in every unit inherits it.
  `tools/test_check_test_budget.py` now deletes it per test, but other tests
  may not.
- **One room's memory: `.claude/host-budget.sh --room-memory <room> <high>
  <max>`** (AGAST #3971), e.g. `--room-memory ritz-task-3965 10G 12G`, and
  `--clear-room-memory <room>` to go back to 3500M / 5G. **Only with Aaron's
  OK.** The `ritz-rooms.slice` cap is what protects the machine, so the
  override has to fit under it: high ≤ max ≤ the slice's MemoryMax, or it is
  refused. Don't use `systemctl --user set-property --runtime`: its
  `50-Memory*.conf` sorts before `50-ritz-host-budget.conf`, and the next
  `daemon-reload` (every reap's `--remove` runs one) silently puts 5G back.
  The script writes `/run/user/$UID/systemd/user.control/adele-agent@<room>.service.d/90-rz-room-memory.conf`,
  which sorts after the budget file and survives reloads but not a reboot.
  `--verify <room>` reports it, and `--remove <room>` deletes it at the reap.
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
  gate. Waiting gates get a free slot first come, first served (#3364); the
  train gate goes ahead of room gates (#3317). A gate log's `WAITING` lines
  show its queue position.
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
    `SPAWN` creates the worktree off `origin/main`; the room gates with
    its own worktree's `run-gate.sh` (briefing step 6), not the host's
    `~/dev/ritz-lang/rz` checkout (Aaron, 2026-11-16 20:35).
  - `RESTART ritz-task-<id>`: restarts a room that isn't working.
    **Exec-capable TMPDIR (bangerang, 2026-11-17):** bangerang's `/tmp` is
    `noexec` and room units run with `PrivateTmp=yes`, so a hand-run
    `pytest` that execs a built ritz1 from `tmp_path` fails (#1334). Gates
    are fine (`run-gate.sh` sets its own exec-capable TMPDIR, #3704). At
    SPAWN the host makes `~/tmp/rz-room-<id>` and sets
    `TMPDIR=/home/aaron/tmp/rz-room-<id>` in a systemd drop-in,
    `adele-agent@ritz-task-<id>.service.d/60-rz-room-tmpdir.conf`, before
    the unit starts. Not `room.env`: `adele room spawn` rewrites it at
    install and starts the unit at once. TEARDOWN deletes the drop-in and
    the dir.
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
  - what `PAUSE` / `RESUME` do, if you send them;
  - that `adele room spawn` takes `--repo ~/dev/ritz-lang/rz`. Without it
    spawn branches from the host's adele checkout, leaves a stray
    `ritz-task-<id>` branch there and fails with `fatal: '…/rz-task-<id>'
    already exists` (huburght, 6 stray branches, 2026-11-14). `repo=rz` on
    the verb line isn't enough. It also takes `--worktree
    ~/dev/ritz-lang/rz-task-<id>`. Without it spawn defaults to
    `<repo>-<name>` (`rz-ritz-task-<id>`), and if the host made
    `rz-task-<id>` first it fails with "'ritz-task-<id>' is already used by
    worktree". Spawn reuses an existing worktree when `--worktree` names it
    (huburght, starbux and toffee, 2026-11-18).
  - that `adele room rm` (TEARDOWN, dry run and real) also takes `--repo
    ~/dev/ritz-lang/rz`. Its ownership guard accepts an `rz-task-<id>`
    worktree only through the branch rule inside `--repo`. Without it,
    `rm` refuses with "not named for ritz-task-<id>" (bangerang #1540,
    2026-11-16, then cleaned up by hand). A refusal with `--repo` comes
    back as `TEARDOWN-REFUSED`; never a manual teardown.
  Every `SPAWN` still tells the host to **save the briefing with a Bash
  here-doc, never the `Write` tool**: `Write` outside the host's workspace
  waits on an approval nobody gives, and the host room stalls for up to 30
  minutes (starbux 2026-11-10, toffee 2026-11-11).
- **ssh from this room: always `ssh -F ~/.ssh/rz_hosts <host>`.** The
  sandbox maps only uid 1000 into its user namespace, so root-owned
  `/etc/ssh/ssh_config.d/*.conf` shows up as owned by `nobody` and plain
  `ssh` dies with "Bad owner or permissions". It will keep coming back
  (Aaron, 2026-11-15), so don't try to fix the files. `-F` skips the system
  config entirely. `~/.ssh/rz_hosts` also maps huburght, starbux, toffee and
  chungus to their LAN IPs, which don't resolve by name here, and sets
  `BatchMode yes`. If a host's DHCP lease moves, update the IP there. Use
  ssh only to look (`uptime`, `systemctl --user status`, logs); changes on
  a host still go through its host room's verbs. **One exception:**
  `train.sh gate --next` / `wait` / a discarding `build` run the
  speculative train gate over this ssh (AGAST #3988; "Merge trains" step
  4b). They touch only `~/dev/ritz-lang/rz-train-remote` (a detached
  worktree of the host's `~/dev/ritz-lang/rz`), `run-gate.sh`'s own gate
  dir and the `ritz-gate-train` unit; never run those by hand.
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
Each room runs `run-gate.sh` from its own worktree (briefing step 6), so a
gate fix on `main` reaches a room only when it rebases. Nothing reads the
host's `~/dev/ritz-lang/rz` checkout for the gate.

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
4. **Out of scope?** File an AGAST ticket. Don't widen the change. File it
   with `project_id=1` and `parent_task_id=<milestone>` (the parent of your
   own ticket). If it fits no milestone, use the Triage bucket `#3788`.
   Never file a ritz ticket with no project or no parent.
5. **Finish on main:** `git fetch origin && git rebase origin/main`, then
   squash to one commit: `ritz-task-<id>: 🤖 <terse description>`.
   Then run `make -C projects/ritz smoke` (≤ 2 min) before requesting a
   gate; fix anything it reports first. A gate slot is one machine-wide.
6. **Gate that commit**, detached so a new message can't kill it, with
   your own worktree's gate script (a branch may carry gate fixes for itself;
   Aaron, 2026-11-16, Borque #3724):
   ```bash
   W=~/dev/ritz-lang/rz-task-<id>
   LOG=$(bash "$W/.claude/skills/rz-iterate/run-gate.sh" "$W" <id>)
   timeout 540 bash "$W/.claude/skills/rz-iterate/run-gate.sh" --wait "$LOG"
   ```
   A gate fix on `main` reaches you only when you rebase. No room reads
   `~/dev/ritz-lang/rz` any more, so it works unchanged under Borque's hostd.
   Run the wait in the foreground and repeat it on exit 124, which only means
   the slice ran out. It runs a clean `make -C projects/ritz ci-local` over CI's `build-all`
   and `bootstrap` jobs (#2141), one gate machine-wide, and exits with the
   gate's code (98 = no verdict, 99 = HEAD moved; neither passes). A
   `SETUP ERROR` line means a missing tool on this machine (e.g. lld-link
   for harland), not a regression: fix the machine and re-gate. The gate runs at full CPU weight; your room runs at CPUWeight=20
   under a 5G memory cap, so room builds can't starve it (#1811). Your
   permissions deny `systemd-run` (it would take a build out of the cap).
   A test that needs a real unit runs it through
   `bash .claude/room-unit.sh [--pipe] [--unit=NAME] -- <cmd>`, which keeps
   it in `ritz-rooms.slice` under a 1G, 15-minute cap and shares your /tmp
   (#3568). Builds never go through it. If you touched packages
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

**Writing under `.claude/` asks a human** for the `Write` tool and any `rm`,
whatever your permissions say (#3568). Nobody answers a room, so you stall.
To create a file there, `Write` it to /tmp and `cp` it in. Change files
with `Edit` or `sed -i`. To delete one, `mv` it to /tmp. A command that
writes under `.claude/` and contains the word `rm` anywhere (heredoc bodies
included) still asks. /tmp scratch (mktemp, cp, rm) needs no approval.

**An MCP call rejected (401, expired or invalid token)? Restart yourself.**
Don't retry, and don't work around it. Your token is read once, at startup
(#2546). Save the message you were sending, schedule your own restart, and
end your turn:
```bash
P=$(git rev-parse --git-dir)/pending-mcp   # outside the tree, never committed
printf '%s\n' "REAP ritz-task-<id> <full-sha> — <one line>" > "$P"
bash .claude/room-unit.sh restart-self   # restarts your own unit in 15s
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
- **Self-restart** (`room-unit.sh restart-self` under "An MCP call
  rejected", below) works the same on this host.

<full AGAST ticket text>
````

**Ephemeral (spot) hosts add this too** (skronk*, Aaron 2026-11-18: "commit &
push more often"). Spot boxes were terminated three times on 2026-11-18, the
c5.12xlarge pair within 30 minutes, which lost 64 rooms. Only pushed branches
and room history survived.

````markdown
- **<host> is an EC2 spot box. It can vanish at any minute, and it powers
  off at <deadline>Z in any case.** All that survives is what you've pushed
  and what's in this room's history.
  - **Push WIP at least every 15 minutes**, and before anything that runs
    longer than about 5 minutes (a gate, a corpus sweep, a full pytest):
    `git add -A && git commit -qm "wip: <what>" && git push -q --force-with-lease origin HEAD:refs/heads/ritz-task-<id>`.
    Squash to one commit before you gate for the REAP (step 5).
  - **Write measurements down when you get them.** Post sweep counts,
    bisect results and decisions in a short STATUS to `rz`, or commit them
    in a scratch file on the branch, so a replacement agent can pick up
    from them.
  - REAP (or report state to `rz`) by **<deadline − 20 min>Z** at the latest.
````

**Re-spawning after a spot loss:** keep the room ID, and send the host a
resume briefing that points at the room's own history (the original
`## Task Briefing` message) and says to `git fetch origin ritz-task-<id> &&
git reset --hard FETCH_HEAD` if a branch exists. A room with nothing pushed
can replay its predecessor's recorded edits from the room history (#1444
recovered 16 edits that way, 2026-11-18).

## Reaping

**The scratchpad is the reap queue and nothing else.** One line per request,
nothing more than it takes to act on it:

```
reap ritz-task-1450 1a2b3c4
```

### Gate coverage: what runs before a merge (AGAST #1838, #3969)

`.github/workflows/main.yml` is the only workflow, and it runs on push to
`main`, i.e. **after** the merge. Before the merge, the only check is the gate:
`make -C projects/ritz ci-local` over main.yml's `build-all`, `test-all` and
`bootstrap` jobs (room gate and train gate, both through run-gate.sh's
default command), plus `train.sh pkgs test` on the packages a train touches.
So:

| main.yml job | before merge | after merge (CI) |
|---|---|---|
| `build-all` (`./rz build --all`) | yes (#2141) | yes |
| `test-all` (`./rz test --all`) | yes (#3969, Aaron 2026-11-18) | yes |
| `bootstrap` (matrix-full, regression.sh, ...) | yes | yes |

`test-all` runs between build-all and bootstrap, in workflow order, on the
CAS build-all just warmed. It's main.yml's own job, not a copy of its
command, so the gate and CI can't drift. The sweep prints one verdict line
per package, `PKG PASS|KNOWN|XPASS|SETUP|FAIL <id>`, with the failures last
so `run-gate.sh --wait` (`grep '^PKG '`, `tail -20`) shows them.
`build` entries in `known-failures/` stay advisory (`PKG KNOWN`); any other
failure fails the gate. pr.yml (a pull_request workflow that never fired,
since nothing lands by PR) and the advisory `lint-all` job were deleted.
ritz-lint is a local pre-commit hook
(`projects/ritz/tools/ritz-lint/install-hook.sh`).

Evidence (#3969, 2026-11-18): 5/5 clean `./rz test --all -j 28` runs on main
472d77bb on bangerang (28/28 packages each time, no flakes; 40 s cold, 9 s
warm). A planted failing `[[test]]` in a scratch package passed every
build-all step and failed the room gate at `[Test workspace]`
(`PKG FAIL zz_plant3969`, EXIT=2).

Added gate wall time: on bangerang (28 cores, gate slice), the
`[Test workspace]` step took 23.6 s in the gate (a fresh tree, after
build-all), against a ci-local total of 491 s for a pre-#3969 gate (#1838's).
On omegalisk: not measured in-gate yet. #1838 measured `rz test --all` at
142 s there (`-j 6`, room CPU weight, with a gate running: room load, the
worst case). The first omegalisk train gate after #3969 lands prints the
in-gate figure (`[Test workspace] END ... <secs>s`). If that's over ~180 s,
cap `-j` or reuse the cache.

### Merge trains (Aaron, 2026-11-12)

Every REAP is one squashed commit that its room already gated on its own
base. Rather than have each room rebase and re-gate in turn (one ~25-minute
gate per merge), `rz` stacks every queued commit on `origin/main` in queue
order and gates only the top of the stack. If that passes, every commit
below it has passed too, and they all land in one push. This is the one
gate `rz` runs; it still never edits, rebases or fixes a room's commit.

`.claude/skills/rz-iterate/train.sh` does the git work in its own
worktrees, one per train in flight: `~/dev/ritz-lang/rz-train`, then
`rz-train-2`, `rz-train-3`, ... as trains stack (created on first use,
detached HEAD, never a room's; reused once their train lands). Each train has its own worktree and state,
so building the next train never touches the one gating. Tests:
`bash .claude/skills/rz-iterate/test-train.sh`.

**Terms:** a **car** is one room's REAPed commit (one squashed commit),
cherry-picked onto a train. A **train** is a stack of cars gated once, at
its top. The **tail** is the train's top commit. **A train holds at most 8
cars** (Aaron, 2026-11-17). If more than 8 are queued, cars 9 onward go into
a new train stacked on the first train's tail. That train is gated and
landed separately, after the first one. Every car is still cherry-picked;
no room is asked to rebase because a train was full.

**The rule (Aaron, 2026-11-17): never fast-forward rooms one at a time, and
never send a room back to rebase onto `main` just because `main` moved.**
On 2026-11-17 three REAPs that stacked cleanly were each sent to rebase and
re-gate after one merge. That cost three gates where one train needed one.
This is also how Borque's conductor works.

- **No train in progress:** a REAP that arrives builds a train straight
  away, with every queued car, and gates it.
- **A train is gating:** REAPs that arrive form the **next** train, stacked
  on the gating train's tail, not on `main`. Build it as cars arrive so a
  conflict shows up at once. **Gate it at once on a remote host,
  speculatively** (AGAST #3988, step 4b): it is tested on the gating
  train's tail while that train is still being tested. If the first train
  passes, both land in order. If the second passes first, it lands both at
  once and the first one's gate is cancelled (step 5). If the first fails, the second train's verdict is
  thrown away and it is rebuilt and re-gated on the new base. **At most 2
  trains in flight** (one here, one remote); REAPs that arrive while both
  gate form train 3, which gates once train 1 lands.
- **A car conflicts** (e.g. ABCD is in the train, E arrives, and E conflicts
  with C): bounce E to its room with the exact commit to rebase onto, the
  tail (D's train SHA), not `main`. The room resolves the conflict on D,
  re-gates and REAPs again, and E joins the back of the train.
- **A train fails:** find the culprit by reasoning first, bisection second
  (step 6).

`train.sh` numbers trains in landing order: **train 1** is the one gating
(or about to), train 2 is stacked on its tail, and so on (AGAST #3809).
`gate` always acts on train 1. `land <log>` lands the train whose tip the
log passed, and every train below it (step 5), then promotes the next one
to train 1.

1. **REAP arrives:** (this section, not `/reap-ritz-room`, handles it)
   `append_scratchpad_item` immediately, even while a train is gating, then
   say in one line what's queued. Never add to a train that's gating: a REAP
   that arrives then rides the next train, stacked on the gating train's
   tail.
2. **Check each REAP line before it boards.** A remote room's REAP must
   quote `SHA=<12> EXIT=0` from its gate log, and that SHA must be the REAP
   SHA's prefix. Without it, it's a room mistake (step 7). (`train.sh build`
   checks the rest: the branch tip is the REAP SHA, and it's one commit.)
3. **Build the train** from the unchecked items, oldest first
   (`get_scratchpad` first, never from memory).
   **No train gating:** every unchecked item, on `origin/main`:
   ```bash
   .claude/skills/rz-iterate/train.sh build ritz-task-2593:3f42ab80 ritz-task-1844:4b699a83 ...
   ```
   **A train is gating:** `--next` keeps train 1 untouched and stacks the
   given cars on its tail as train 2. If train 2 is gating speculatively
   (its state has a `SPEC=` line, step 4b) `--next` keeps it too and stacks
   the cars on *its* tail as train 3. Pass every unchecked item that is not
   in a kept train (`train.sh show` lists each train's `ITEM`s), and run it again
   each time a REAP arrives, so a conflict shows up at once; each run
   rebuilds trains 2+ from scratch (same cars on the same tail give the same
   SHAs: picks keep the car's committer date):
   ```bash
   .claude/skills/rz-iterate/train.sh build --next ritz-task-2601:9c1d03ee ...
   ```
   Either way it prints one line per item (`KEPT`, `APPLIED`, `CONFLICT`,
   `EMPTY`, `BAD`) and one `TRAIN <k> base=<12> tip=<12> n=<cars>
   gate=<needed|not-needed>` line per train. Past 8 cars it starts the next
   train on the last one's tail by itself (10 cars: `TRAIN 1 ... n=8`, then
   `TRAIN 2 base=<train 1's tip> ... n=2`). A car whose branch sits on an
   unlanded train commit (step 7's bounce) boards: `KEPT` when its parent
   is the tail it lands on (its own gate ran on that tree), `APPLIED` when
   it sits on the same patches at other SHAs; `BAD ... not in the train`
   only if a commit under it is in no train. `rz-larb` boards like any room
   (`rz-larb:<sha>`).
4. **Gate train 1, unless `gate=not-needed`** (only cars already on its
   base or on each other: their own gates cover them). Train 2 gates
   remotely at the same time (4b):
   ```bash
   LOG=$(.claude/skills/rz-iterate/train.sh gate)
   .claude/skills/rz-iterate/train.sh wait "$LOG"    # Bash run_in_background
   ```
   (`train.sh wait` on a local log is `run-gate.sh --wait`.)

   **4b. Gate train 2 speculatively on a remote host** (AGAST #3988) as soon
   as `build --next` prints `TRAIN 2 ... gate=needed`, while train 1 gates:
   ```bash
   LOG2=$(.claude/skills/rz-iterate/train.sh gate --next)   # huburght; or: gate --next <host>
   .claude/skills/rz-iterate/train.sh wait "$LOG2"         # Bash run_in_background
   ```
   omegalisk can't take two gates (15 GB WSL), so train 2 runs on a host
   in `~/.ssh/rz_hosts` (default huburght, `RZ_TRAIN_REMOTE`; 2 gate
   slots, 47 GB). **The contract**, all in `train.sh` (header and
   `REMOTE_SH`):
   1. `gate --next` pushes train 2's tail to origin
      `refs/heads/rz-train/<tip12>`, then runs `ssh -F ~/.ssh/rz_hosts
      <host> bash -l -s -- start ...` with the script on stdin. On the host
      it fetches that ref into `~/dev/ritz-lang/rz`, refuses unless it is
      exactly the tip, checks it out detached in
      `~/dev/ritz-lang/rz-train-remote` (created on first use), and starts
      **that tree's** `run-gate.sh` with `RZ_GATE_TRAIN=1` (train priority,
      FIFO and reservation on that host, #3317/#3364/#3427, against that
      host's own room gates) and the package tests (#3363) as
      `RZ_GATE_AFTER`. Its base, for the package tests and ci-local's
      `--diff-base`, is `main` (train 1's base), not train 1's tail: a
      pass lands train 1 too, so it must cover train 1's cars (#4151). It records `SPEC=<host> <ref> <remote log> <local
      log>` in train 2's state and prints the local log path,
      `gate-logs/train-<tip12>-<n>@<host>.log`. stderr says `SPEC train 2
      tip=<12> on <host>: <remote log>`.
   2. `wait <local log>` runs the host's `run-gate.sh --wait` over ssh in
      9-minute slices (an ssh failure retries 5 times, 30 s apart, then is
      **no verdict**, exit 1), copies the remote log to the local path,
      and checks its `SHA=` is train 2's tip (else `REFUSED`, exit 3). It
      prints `gate <log> SHA=<12> EXIT=<rc>` and exits with the gate's
      code. `land` then checks `SHA=<tip>` and `EXIT=0` exactly as for a
      local log.
   3. The ref is deleted when the train lands, when a deeper train's pass
      lands it (a `CANCELLED speculative gate on <host> ...` line), or when
      a `build` replaces the train (a `DISCARDED speculative gate on <host>
      ...` line). Both lines also stop the host's `ritz-gate-train` unit.

   Refusals: no train 2 (`gate` is for train 1), `gate=not-needed` (land
   it after train 1), or train 2 already gating (**at most 2 in flight**).
   `gate` refuses a train 1 that is gating remotely (`train.sh wait` its
   log). If the host can't start the gate (`the remote gate on <host> did
   not start`), let train 2 gate here after train 1 lands, as before. If a
   remote gate dies or the host goes away, rebuild with the same cars (a
   plain `build` of trains 1 and 2: same cars on the same tail give the
   same tips) and gate again. Trains still land in order, but a passed
   train 2 lands train 1 with it (step 5): don't wait for train 1's gate.
   Run the wait with `run_in_background`, so it wakes this room when the gate
   ends, and keep the usual 1800 s fallback wakeup. Carry on with the loop
   (slots, nudges, `build --next` for REAPs that arrive) meanwhile. On a
   context reset, `train.sh show` prints every train (`== train <k>` then
   its state), and the highest-numbered `gate-logs/train-<sha12>-<n>.log` holds the gate. The
   train gate uses omegalisk's one gate slot. It may wait for a room gate
   that already holds the slot, but it takes the next free one ahead of any
   waiting room gate (`.train-waiting`, #3317; FIFO otherwise, #3364).
   **It also tests the packages the train touches** (AGAST #3363). #3290's
   bug got through a green train because build-all + bootstrap don't run
   the workspace projects' own tests. `train.sh gate` prints `PKGS <dirs>`
   on stderr. Once build-all and bootstrap pass, the gate runs
   `train.sh pkgs test <base>`: `./rz test` on each touched package (the
   deepest `ritz.toml` above each changed file under `projects/`). It skips
   `projects/ritz/**` and `[workspace.exclude]` dirs, so a compiler-only
   train costs what it did before. **Except a ritzunit train**: a change
   to `projects/ritzunit` (its own package, not `inventory`) or to
   `ritz0/test_runner.py` selects every package `rz test --all` sweeps,
   `projects/ritz/**` members included (#3735). ritzunit is the `main` of
   every test binary, and #2072, ritzunit-only, broke ritzlib/tests and
   zeus through a green train. Each package gets one line, and
   `--wait` shows them:
   `PKG PASS`, `PKG KNOWN` (a `build` entry in `known-failures/`: advisory, as in
   `rz test --all`), `PKG PRE-EXISTING` (fails on the base too, so it was
   re-run in a temp worktree of the base: not this train's) or `PKG FAIL`
   (passes on the base, or a new package): the gate fails. Treat a
   `PKG FAIL` like any other red gate. Since #3969 the gate's own
   `test-all` job runs every package first, so this step only re-runs
   packages that already passed. A package failure stops the gate at
   `[Test workspace]` before the PRE-EXISTING base re-run gets a chance
   (follow-up: #3970).
   `train.sh pkgs list <base>` (run in the train worktree) previews the set.
   **When the train gate ends, pass or fail, it reserves the slot for the
   next train** (`gate-logs/.train-reserved`, #3427), before it lets go of
   it. Reading the verdict and running `land` takes 30-60 s, and a room
   gate first in the FIFO used to take the slot in that gap: five times on
   2026-11-15, ~20 min of train time each. A failed gate reserves too,
   because the halved train (step 6) gates next. Room gates queue but take
   no slot until the next `train.sh gate` starts, or for 10 minutes at most
   (`RZ_GATE_TRAIN_HOLD`), so read the verdict and act on it promptly.
   **Except a starved room gate** (AGAST #3578). While REAPs keep coming,
   train priority plus the reservation kept omegalisk's one slot for
   trains, and #3448/#3517 sat at queue position 1 for 2h+ through seven
   trains. Once the oldest waiting room gate has waited 45 minutes
   (`RZ_GATE_STARVE`, 2700 s), its log says `STARVED`. It ignores the
   reservation and `.train-waiting`, and train gates queue behind it, so it
   runs before the next train. As it takes the slot, it stamps
   `gate-logs/.room-override`, which restarts every room's 45-minute clock.
   So at most one room gate per 45 minutes jumps ahead of the trains,
   and trains still get the slot in between. Keep building and gating
   trains as usual: a train gate that queues behind a starved room gate
   just waits one room gate (its log shows queue position 2). Don't hold
   trains back by hand any more.
5. **Gate passes (exit 0), or `gate=not-needed`:**
   ```bash
   .claude/skills/rz-iterate/train.sh land "$LOG"      # no log when not needed
   ```
   **Land the deepest train that passed** (AGAST #4151, #4130). `$LOG` may be
   any train's: train k is built on train k-1's tail, so a pass of train k's
   tip tested every car of trains 1..k, and `land` lands them all in one
   push. Trains 1..k-1's gates only repeat that verdict, so `land` cancels
   them: it stops the local `ritz-gate-train` unit and clears its
   `.train-waiting` (the slot frees at once, `CANCELLED local gate ...`),
   and stops a remote one and deletes its ref (`CANCELLED speculative gate
   on <host> ...`). So when train 2's remote gate passes while train 1 still
   gates here, land train 2's log straight away. A red train 1 doesn't
   block a green train 2 either: train 2 passed on exactly the tree that
   lands, so train 1's red was a flake or was fixed by a later car (read it
   before you move on). The 8-car cap is per gate, so landing 16 cars at
   once this way is fine. A red train k changes nothing.
   It refuses if the log isn't for any train's tip, didn't pass, a train
   1..k moved since the build or isn't on the tail below it, or `main`
   moved since the build; then rebuild and re-gate.
   It pushes train k's tip to `main` (never forced), fast-forwards
   `~/dev/ritz-lang/rz`, and prints `MERGED <branch> <room sha12> as <main
   sha12>` per commit of trains 1..k. If a train was stacked behind train k,
   it prints `NEXT base=<12> tip=<12> n=<cars> gate=<...>`: that train is train 1 now, its
   base (the tail just pushed) is `main`, so gate it straight away (step 4),
   or land it with no log if `gate=not-needed`. If it was gating remotely
   (4b) the line ends `spec=<local log>`: don't gate it again, `train.sh
   wait` that log (if not done yet) and land it with that log. Then gate
   the new train 2, if any, with `gate --next` (4b). It also
   renews the gate's reservation (#3365), so the 10 minutes count from the
   push: build and gate the next train promptly. A `build` with
   `gate=not-needed` drops the reservation; if nothing else is queued, just
   let it expire. For each:
   `complete_task` (`Merged to main as <main sha8> (train <tip sha8>). <REAP
   line>`; if refused, see "Who owns the ticket"), `check_scratchpad_item`,
   and clean up (`systemctl --user stop/disable adele-agent@ritz-task-<id>`,
   remove `~/.config/adele/rooms/ritz-task-<id>`, `.claude/host-budget.sh
   --remove ritz-task-<id>`, `git worktree remove`, `git branch -D`,
   `git push origin --delete ritz-task-<id>`).
   **Archive every MERGED room on the server** (Aaron, 2026-11-14), local
   or remote, in one call once the train has landed:
   ```bash
   .claude/skills/rz-iterate/archive-rooms.py ritz-task-2593 ritz-task-1844 ...
   ```
   It prints `ARCHIVED <room>` per room (history kept; `unarchive_room`
   reverses it). Do the same for a ticket closed by a REAP `none`. To catch
   up on rooms that were missed, run `archive-rooms.py --from-git 400`
   (dry run; add `--apply`). It reads the `ritz-task-<id>:` subjects on
   `main` and archives only rooms whose ticket is `completed`.
   **Remote room:** send `TEARDOWN ritz-task-<id> merged=<main sha12>` to its
   host room instead of the local steps, and still delete the branch on
   GitHub here. Spell out in the message that the commit was cherry-picked,
   so `git cherry origin/main ritz-task-<id>` prints `- <sha>` (same patch),
   not nothing; a `+` line is fine only if `<main sha12>`'s subject matches
   the branch tip's. The slot is free once the host answers `TORNDOWN`.
6. **Gate fails: reason first, then bisect.** Read the failing lines
   (`train.sh wait` / `run-gate.sh --wait` prints them; a remote gate's
   whole log is the fetched `...@<host>.log`) against each car's diff
   (`git show --stat <car>`, then the hunks near the failure): which car
   touches the failing test, file, compiler stage or package? If one car
   is the clear suspect, rebuild the train without it and gate that. If it
   passes, land it and gate the suspect alone on the new `main`. If no car
   stands out, or the guess was wrong (the train still fails without it),
   fall back to halving. With `k` cars, rebuild with the first `ceil(k/2)`
   and gate that (a plain `build`, which drops every stacked train too;
   pass their cars after the halved ones and the rest stack behind it as
   train 2). If it passes, land it, and the rest ride the next train.
   If it fails, halve again. Reasoning only picks which car to drop; `rz`
   still never edits, fixes or debugs a car. A single car that fails on
   top of `main` goes back to its room: check its item and send it one
   line, "rebase onto <main sha7>: your commit fails the gate on top of
   `main`", with the gate's failing lines. Its fixed REAP goes to the back
   of the queue.
   **With two trains in flight** (AGAST #3988): if **train 1 fails**,
   train 2's verdict is worthless whatever it says (its base was train 1's
   tail). Don't wait for it: the plain `build` for the bisect replaces
   train 2, prints `DISCARDED speculative gate ...`, stops the remote gate
   and deletes its ref. Pass train 2's cars after the halved ones as usual,
   so they stack on the new tail, and gate them with `gate --next` again.
   If **train 1 passes and train 2 fails**, land train 1 (step 5), then
   bisect train 2 (now train 1) as above. A stale verdict can't land
   anything by mistake: it names the old tip, and `land` refuses a log for
   another commit.
7. **`CONFLICT`:** bounce it now, not after the train lands. The line names
   what it hit: `CONFLICT <branch> <sha12> with <car>[,<car>] on
   <file>[,<file>]` (the train cars touching the conflicted files, or
   `main` when no train car does). Check its item and send its room one
   line: "your commit conflicts with <car> on <files> in the train; rebase
   onto <tail sha12>, resolve, re-gate and REAP". `<tail>` is the `tip=` of
   the last `TRAIN` line, so the rebased car stacks onto the back of the
   trains; `build` then accepts it (step 3). Its next REAP joins
   the back of the queue. **`BAD` or a missing gate quote** leave that
   item out too: tell its room which check failed. **`EMPTY`** means the
   patch is already on `main`: check the item, then close and clean up as
   in step 5.
8. **All items checked:** `clear_scratchpad`.

**Never tell running rooms that `main` moved.** A room rebases only when its
own commit conflicted or failed (steps 6 and 7). Broadcasting made five rooms
re-gate at once, filling both gate slots with work that was stale again by
the next merge. Committing to `main` from this room (skill edits and the
like) needs no message either; it just becomes the next train's base.

GitHub CI: glance at `gh run list -L 3` each turn. Red on an already-known
failure set is normal (`known-failures/` reds). A **new** failure becomes a
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
   `known-failures/` has no `regression` ritz1 entries (20 entries at
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
