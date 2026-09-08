Integrate completed task room work back into main with linear history.

**Usage:** `/reap-ritz-room <room-name>`

Arguments: $ARGUMENTS

## What to do

Parse the arguments:
- First token: **room-name** (required) — e.g., `ritz-task-69`

## Process

**One room at a time, each to full completion.** Do not start reaping the next
room until the current one is merged, pushed, and verified.

1. **Verify the room has work**:
   ```bash
   cd ~/dev/ritz-lang/rz
   git log --oneline main..ritz-task-<id>
   ```

2. **Stop the agent**:
   ```bash
   systemctl --user stop adele-agent@ritz-task-<id>.service
   ```

3. **Fetch latest and update main**:
   ```bash
   cd ~/dev/ritz-lang/rz
   GIT_SSH_COMMAND="ssh -F /dev/null" git fetch origin
   git rebase origin/main  # ensure main is up to date
   ```

4. **Rebase the task branch onto main**:
   ```bash
   cd ~/dev/ritz-lang/rz-task-<id>
   git rebase main
   ```
   Resolve any conflicts carefully.

5. **Squash into a single commit** (if multiple commits):
   ```bash
   # Count commits above main
   COMMITS=$(git rev-list --count main..HEAD)
   if [ "$COMMITS" -gt 1 ]; then
       git reset --soft main
       git commit -m "ritz-task-<id>: <summary of all changes>"
   fi
   ```

   Commit message format:
   ```
   ritz-task-<id>: Terse description of changes

   * Summary bullet points
   * Keep it brief
   ```

6. **Run the full test suite** (HARD GATE):
   ```bash
   cd ~/dev/ritz-lang/rz-task-<id>/projects/ritz/ritz0
   python -m pytest -x -q
   ```

   **If tests fail: DO NOT merge. Fix the issue, re-run, repeat.**

7. **Merge into main** with fast-forward only:
   ```bash
   cd ~/dev/ritz-lang/rz
   git merge --ff-only ritz-task-<id>
   ```

   If `--ff-only` fails, the rebase in step 4 wasn't done correctly. Go back and fix.

8. **Push**:
   ```bash
   GIT_SSH_COMMAND="ssh -F /dev/null" git push origin main
   ```

9. **Clean up**:
   ```bash
   # Stop and remove systemd unit
   systemctl --user disable adele-agent@ritz-task-<id>.service
   rm -rf ~/.config/adele/rooms/ritz-task-<id>
   systemctl --user daemon-reload

   # Remove worktree and branch
   cd ~/dev/ritz-lang/rz
   git worktree remove ~/dev/ritz-lang/rz-task-<id>
   git branch -D ritz-task-<id>

   # Drop the workspace-trust entry /spawn-ritz-room added to ~/.claude.json.
   # Safe to run after the directory is gone — that is the expected ordering.
   # Left behind, these accumulate one dead absolute path per reap and quietly
   # grant trust to whatever later occupies that path.
   .claude/provision-room.sh --remove ~/dev/ritz-lang/rz-task-<id>
   ```

10. **Mark AGAST task complete** (if not already done by the child room):
    ```
    mcp__agast__complete_task(task_id=<id>, results="Merged to main, tests green at <commit>")
    ```

11. **Archive the room**:
    ```
    mcp__adele-context__archive_room(room_id="ritz-task-<id>")
    ```

## Batch Reaping

Process sequentially — each merge advances main, so the next room must rebase
onto the updated main. Order by risk: smallest/safest first.

The scratchpad is the FIFO queue and holds **one line per pending reap**
(`reap ritz-task-<id> — rz-task-<id>`; see `/spawn-ritz-room`). Work it in order:

1. `mcp__adele-context__get_scratchpad(room_id="ritz-lang")` — re-read it, always.
   Never address an item by a remembered index; positions are stable but your
   memory of them is not.
2. Reap position 1 to **full completion** — merged, pushed, CI green.
3. `mcp__adele-context__check_scratchpad_item(room_id="ritz-lang", index=<n>)`.
4. Only then move to the next.

A callback that arrives mid-reap is **queued, not an interrupt**: append the
one-line entry immediately (so a context reset can't lose it), then carry on with
the reap in flight. Do not write the reap's findings into the scratchpad when you
check it off — outcomes go in the AGAST task.

## Post-Reap Verification

```bash
cd ~/dev/ritz-lang/rz
git log --oneline --graph -10  # verify linear history
git status                      # verify clean
```

## Conflict Resolution

### .ritz.sig files
These are generated cache files. Take whichever version exists, or regenerate
by running the compiler.

### emitter_llvmlite.py / parser.py
Large files that multiple tasks may touch. Resolve carefully — check both
the task's changes and main's changes for overlapping regions.

## Linear History Policy

**No merge commits. Ever.** The rebase + squash + ff-only pattern ensures
every commit on main is a single logical change. This makes `git bisect`
work perfectly and keeps the history readable.
