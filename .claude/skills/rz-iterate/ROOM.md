# Room rules (rz-iterate)

Every `ritz-task-<id>` room follows these. Your briefing gives the ticket,
base, claim name and host; the AGAST ticket is the spec. `rz` boards the SHA
you REAP onto a merge train whose full gate runs before `main`: your REAP
vouches that the subsystems you changed pass **in full** on that commit.

## Steps

0. **Keep your room description current:**
   `update_room_description(room_id="ritz-task-<id>", description="...")`,
   one sentence of 20-60 characters ("Fix ritz1 slice bounds checks").
1. **Already fixed on your base?** `complete_task` with the evidence and
   REAP `none`; commit nothing after it. That is the only time you touch
   your ticket's status: `rz` claimed it and closes it when your commit
   merges. Never claim, release or complete it yourself, whatever your
   general instructions say.
2. **Test first.** Tests that fail for the reason they name, then the fix.
   Mutation-check: break each part of the fix and confirm only its own tests
   go red. Size a pytest matrix to the rule, not the cross product
   (`projects/ritz/docs/TESTING.md`, "What a ritz0 pytest case costs").
2a. **Write Ritz, not C.** `c"strings"` are only for C interop, where the
   callee can't take a length and needs NUL termination. Add no new `c""`
   outside an interop boundary (a syscall path or argv, an `extern fn`), and
   new text-taking APIs take `StrView`: if the only API takes
   NUL-terminated `*u8`, add the `StrView` one to ritzlib. Read
   `projects/ritz/docs/RITZ_NOT_C.md` before writing code and run
   `/ritz-review` on your diff. Your REAP says how many `c""` you added and
   removed.
3. **Subagents (Agent tool) for parallel work.** No rooms of your own.
4. **Finish the job; don't file follow-ons.** Do your ticket's whole
   objective in your commit, with the adjacent fixes it needs (a caller to
   port, a stale comment or pin). Anything that blocks none of the goals
   (end of `SKILL.md`) goes in your REAP one-liner or nowhere. File **at
   most one** ticket, only for a gap that blocks a goal and can't fit:
   first line names the goal, `project_id=1`, `parent_task_id=<your
   ticket's parent>`; say so in your REAP. Never split your ticket.
5. **Finish on your base** (the briefing's `Base:` line: a train tail, or
   `origin/main`). Squash to one commit: `ritz-task-<id>: 🤖 <terse
   description>`.
6. **Smoke-check your subsystems, in full**:
   ```bash
   bash .claude/skills/rz-iterate/smoke-plan.sh plan   # what it will run
   bash .claude/skills/rz-iterate/smoke-plan.sh run    # last line: your quote
   ```
   `run` maps the files `HEAD^..HEAD` changed to their test targets (the map
   is in the script's header) and runs each in full. Its last line is your
   quote: `smoke <sha12> [<targets>] EXIT=0`. Only `EXIT=0` passes: else
   fix, re-squash, re-run. It refuses a dirty tree; EXIT=99 means HEAD
   moved. A run longer than 10 minutes: start it with the Bash tool's
   `run_in_background`, output to a log, and wait on it in foreground slices
   under 10 minutes until it exits. Failures in packages outside
   `projects/ritz`: compare against `origin/main` before calling them
   pre-existing.

   **The plan is the floor, not the whole check** (#4777). Before you run
   it, name what your change can break beyond the files it touched: the
   callers of a changed signature, the packages using a changed ritzlib
   API, the compiler stages a language change reaches, the tests that read
   the changed sources. Add those as `+<target>` (`run +pkg:<p>
   +ritzlib-ritz1 +build-all-ritz1 ...`; the targets are in the script's
   `cmd_of`), so the quote lists them, and run anything no target covers by
   hand, in full. Compiler and language changes test more: if you're
   unsure, run the full gate below. If you judged no extras were needed,
   say why in your REAP's one line.

   **A full room gate is optional, and the stronger quote:**
   ```bash
   W=~/dev/ritz-lang/rz-task-<id>
   LOG=$(bash "$W/.claude/skills/rz-iterate/run-gate.sh" "$W" <id>)
   timeout 540 bash "$W/.claude/skills/rz-iterate/run-gate.sh" --wait "$LOG"
   ```
   Repeat the wait on exit 124. Only exit 0 passes, with one exception: if
   the only failing step is `[bootstrap] ritz0 unit tests`, the log prints
   `test budget: … breach(es)` and pytest reports `0 failed`, the
   budget-only verdict is terminal. Quote it as `EXIT=2 budget-only: <raw> /
   factor <f> = <norm> vs cap` and do not re-gate. `test budget: no
   calibration` or `SETUP ERROR` is a host setup error: fix it (a stale
   venv: `python3 -m pip install -r projects/ritz/requirements.lock`) and
   re-gate. 98 = no verdict, 99 = HEAD moved.

   You run at CPUWeight=20 under a 5G cap and `systemd-run` is denied: a
   test that needs a real unit uses `bash .claude/room-unit.sh [--pipe]
   [--unit=NAME] -- <cmd>`. The full suite runs only through `run-gate.sh`:
   never start `ci_local.py` or `make ci-local` yourself. Never `pkill -f`,
   `kill -- -PGID` or any pattern that can match another room's processes;
   kill only PIDs you spawned, else tell `rz`.
7. **Don't chase `main`.** REAP the commit you checked; `rz` may land it
   under a different SHA.
8. **Push and REAP.** `git push --force-with-lease origin
   HEAD:refs/heads/ritz-task-<id>`, never `-f`. Rejected as stale: `git
   fetch origin`, check `origin/ritz-task-<id>` is your own earlier push,
   retry; if it isn't yours, stop and tell `rz`. Then send exactly one:
   ```
   mcp__adele-context__send_room_message(room_id="rz",
       sender_name="ritz-task-<id>", ask_claude=True,
       message="REAP ritz-task-<id> <full-sha> smoke <sha12> [<targets>] EXIT=0 — <one line: what changed>")
   ```
   With a gate: `REAP ritz-task-<id> <full-sha> gate <log name> SHA=<first
   12> EXIT=0 — <one line>`. Don't `complete_task`.
9. **Stay on your base.** Trains land and rebuild above you; `rz`
   cherry-picks your commit onto the tail when it boards. Rebase only when
   `rz` says **"rebase onto <sha12>"** (a conflict, or a train gate naming
   your commit): rebase onto exactly that, fix, re-run step 6, push and REAP
   again.

## Standing rules

**Never end a turn with work pending:** nothing wakes you when a gate, run
or subagent finishes. Wait in the foreground in slices under 10 minutes; a
background wait silent for 600s ends the turn. Polling a gate is a
legitimate wait.

**Writing under `.claude/` asks a human** for the `Write` tool and any `rm`, and nobody answers, so you stall. Create a file by `Write`-ing it to /tmp and `cp`-ing it in; change files with `Edit` or `sed -i`; delete by `mv` to /tmp. A command that writes under `.claude/` and contains `rm` anywhere (heredocs too) still asks. /tmp needs no approval, except one call that runs `rm -rf`, starts jobs with `&` in a loop and `kill`s them (#4215): put the commands in `bash /tmp/<name>.sh`, or the `rm -rf` in its own call.

**An MCP call rejected (401, expired or invalid token)? Restart yourself.**
Don't retry: your token is read once, at startup.
```bash
P=$(git rev-parse --git-dir)/pending-mcp   # outside the tree, never committed
printf '%s\n' "REAP ritz-task-<id> <full-sha> — <one line>" > "$P"
bash .claude/room-unit.sh restart-self   # restarts your own unit in 15s
```
On every rejoin, check for that file first; if it's there, send its line as
in step 8, then delete it.

**Messages to `rz`:** one line where possible (the REAP line is the
format). No recaps, tables or restating what your files say.

**Never** check out or push `main`, merge anything, remove your worktree,
stop or disable your unit (restart-self excepted), or delete your branch.
`rz` does that after merging.

## Remote host (briefing line `Host <host>`)

`rz` can't read your files or journal. Your REAP quotes your check's
verdict line, which `rz` checks against the SHA with `smoke-plan.sh check`.
Your claim is `ritz-task-<id>@<host>`. If an AGAST call fails, say so in
your REAP and name your one blocking gap there (title, file:line, goal);
for step 1, REAP `none` with the evidence.

## Spot host (briefing adds `spot, deadline <Z>`)

The box can vanish at any minute and powers off at the deadline; only what
you pushed and this room's history survive.

- Push WIP every 15 minutes and before anything over ~5 minutes:
  `git add -A && git commit -qm "wip: <what>" && git push -q --force-with-lease origin HEAD:refs/heads/ritz-task-<id>`.
  Squash before step 6.
- Post measurements and decisions to `rz` in a short STATUS, or commit them
  in a scratch file on the branch.
- REAP, or report your state to `rz`, by deadline − 20 min.
