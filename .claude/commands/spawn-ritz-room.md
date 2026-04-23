Spawn a new Adele agent room for parallel ritz development tasks.

**Usage:** `/spawn-ritz-room <task-id> [model]`

Arguments: $ARGUMENTS

## What to do

Parse the arguments:
- First token: **task-id** (required) — AGAST task ID (e.g., `69`). Room name will be `ritz-task-<id>`.
- Second token (optional): **model** — `haiku`, `sonnet` (default), or `opus`

## Prerequisites

**CRITICAL: Commit all changes before spawning.** The worktree gets a snapshot of HEAD,
not the working directory. Uncommitted changes will NOT be in the worktree.

```bash
# Check for uncommitted changes FIRST
git status
# If dirty: commit or stash before proceeding
```

Also: `git fetch origin && git rebase origin/main` to ensure we're on latest.

## Process

1. **Fetch the AGAST task** to get title/description:
   ```
   mcp__agast__search_tasks(query="", status="ready")
   ```

2. **Create the Django room** (must exist before agent connects):
   ```
   mcp__adele-context__send_room_message(
       room_id="ritz-task-<id>",
       message="Room initialized for AGAST #<id>.",
       sender_name="Adele (ritz-lang)"
   )
   ```

3. **Create a git worktree** as a sibling to the monorepo:
   ```bash
   cd ~/dev/ritz-lang/rz
   git worktree add ~/dev/ritz-lang/rz-task-<id> -b ritz-task-<id>
   ```

   **Location convention:** `~/dev/ritz-lang/rz-task-<id>` — sibling to `rz/`.

4. **Install the room** using `adele install`:
   ```bash
   adele install --room ritz-task-<id> \
       --name ritz-task-<id> \
       --workspace ~/dev/ritz-lang/rz-task-<id> \
       --model <model> \
       --display-name "Adele" \
       --server wss://adele.lab.amazingland.live
   ```

5. **Start the agent**:
   ```bash
   systemctl --user start adele-agent@ritz-task-<id>.service
   ```

6. **Claim the AGAST task**:
   ```
   mcp__agast__claim_task(task_id=<id>, agent_name="ritz-task-<id>")
   ```

7. **Send the briefing** with verification commands and merge rules:

   ````markdown
   ## Task Briefing

   **{task_title}**

   {task_description}

   | Parameter | Value |
   |-----------|-------|
   | AGAST Task | `#{task_id}` |
   | Branch | `ritz-task-{id}` |
   | Worktree | `~/dev/ritz-lang/rz-task-{id}` |
   | Monorepo | `~/dev/ritz-lang/rz` (DO NOT modify) |
   | Compiler | `projects/ritz/ritz0/` |
   | Model | `{model}` |

   ---

   ### Verification

   Before signaling completion, run these commands and confirm all pass:

   ```bash
   cd ~/dev/ritz-lang/rz-task-{id}/projects/ritz/ritz0
   python -m pytest -x -q
   ```

   Do NOT send the completion callback until every command exits 0.

   ---

   ### DO NOT self-merge

   **You must NOT merge into main, push to main, or clean up your own worktree.**
   Your job ends when you commit on YOUR branch and send the callback below.
   The parent room (`ritz-lang`) orchestrates all merges, rebases, and cleanup.

   Do NOT:
   - `git checkout main` or `git merge` into main
   - `git push origin main`
   - `git worktree remove`
   - `systemctl --user stop/disable` your own unit
   - `git branch -D`

   ### On Completion

   When all work is done and tests pass, send a callback:

   ```
   mcp__adele-context__send_room_message(
       room_id="ritz-lang",
       message="REAP ritz-task-{id} — worktree ~/dev/ritz-lang/rz-task-{id} ready.",
       sender_name="ritz-task-{id}",
       ask_claude=True
   )
   ```

   Also complete the AGAST task:
   ```
   mcp__agast__complete_task(task_id={id}, results="<summary of what was done>")
   ```
   ````

   Send with `ask_claude=True`:
   ```
   mcp__adele-context__send_room_message(
       room_id="ritz-task-<id>",
       message=briefing_message,
       sender_name="Adele (ritz-lang)",
       ask_claude=True
   )
   ```

8. **Verify** the room is running:
   ```bash
   adele status
   ```

## Batch Spawning

When spawning multiple rooms, commit first, then create all worktrees, install all,
start all, then send all briefings. Order matters:

```bash
# 1. Commit everything first!
git add ... && git commit ...

# 2. Create worktrees
git worktree add ~/dev/ritz-lang/rz-task-69 -b ritz-task-69
git worktree add ~/dev/ritz-lang/rz-task-70 -b ritz-task-70

# 3. Install + start
adele install --room ritz-task-69 ...
adele install --room ritz-task-70 ...
systemctl --user start adele-agent@ritz-task-69.service
systemctl --user start adele-agent@ritz-task-70.service

# 4. Send briefings (with ask_claude=True)
```

## SSH Workaround

If `git push` fails with SSH config errors, use:
```bash
GIT_SSH_COMMAND="ssh -F /dev/null" git push origin main
```
