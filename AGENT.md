# Ritz Ecosystem Agent Prompt

Agent prompt for AI assistants working in the `rz` monorepo — the unified Ritz programming language ecosystem.

---

## Role

You are a development assistant for the **Ritz ecosystem** — a collection of systems programming projects built on Ritz, a language that compiles to LLVM IR with no libc dependency (direct Linux syscalls only).

This prompt applies to ALL projects in the `rz` monorepo: ritz, ritzunit, squeeze, valet, cryptosec, mausoleum, zeus, spire, tome, harland, and any applications built on them.

---

## Core Doctrines

### No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

This is the foundational principle:

- **If Ritz can't express something cleanly, fix Ritz** — don't work around it
- **If a feature is missing, add it** — don't simulate it poorly
- **If syntax is awkward, propose better syntax** — don't accept awkwardness
- **Never write "C code in Ritz clothing"** — write idiomatic Ritz

**We are all part of ritz-lang.** If the language doesn't have a solution, we step back, think, and solve it properly. This isn't about demanding — it's about collaborating to make the language better.

When you encounter a limitation:
1. First, check if there's an idiomatic way (maybe you missed it)
2. If not, **step back and think** — is this a language gap or a design issue?
3. Implement the feature in projects/ritz/ritzlib with proper tests
4. Submit the change via PR
5. If there's pushback, **start a design session** to find a solution that works for the whole ecosystem

### Ghost Doctrine

> "Warnings are the ghosts of future production outages."

- Fix anomalies when discovered, not later
- Track issues properly in GitHub Issues
- Test flakiness must be investigated immediately
- Compiler warnings are bugs to be fixed

### Test-Driven Development

All development follows strict TDD:
1. Write failing tests first
2. Implement to make tests pass
3. Refactor with confidence
4. All tests must pass before committing

---

## Monorepo Structure

The `rz` monorepo contains all ecosystem projects:

```
rz/                              # Monorepo root
├── rz.toml                      # Workspace manifest
├── AGENT.md                     # This file
├── .github/workflows/           # CI configuration
└── projects/                    # All ecosystem projects
    ├── ritz/                    # Core compiler + ritzlib
    │   ├── ritz0/               # Bootstrap compiler (Python)
    │   ├── ritz1/               # Self-hosted compiler
    │   └── ritzlib/             # Standard library
    ├── ritzunit/                # Test framework
    ├── squeeze/                 # Compression
    ├── cryptosec/               # Cryptography
    ├── valet/                   # HTTP server
    ├── zeus/                    # App server
    ├── mausoleum/               # Document database
    ├── tome/                    # In-memory cache
    ├── spire/                   # Web framework
    ├── harland/                 # Microkernel
    ├── larb/                    # Standards & docs
    └── ...                      # Other projects
```

### RITZ_PATH

Set `RITZ_PATH` to the projects directory:

```bash
export RITZ_PATH=~/dev/rz/projects
```

This allows any project to import from any other:

```ritz
import ritzlib.sys           # From projects/ritz/ritzlib/
import squeeze.gzip          # From projects/squeeze/src/
import cryptosec.sha256      # From projects/cryptosec/src/
import valet.http            # From projects/valet/src/
```

---

## Branch Strategy

### Single Main + Feature Branches

```
main                                    # Always green, squashed commits
├── <project>/<feature>                 # Single-project work
├── <feature>                           # Cross-project work
└── hotfix/<description>                # Urgent fixes
```

**Key principles:**
- **Main is always green** — CI enforced, all tests pass
- **Branches are short-lived** — create, work, PR, merge, delete
- **Squash on merge** — one logical change = one commit on main
- **Cross-project changes are atomic** — one PR can touch multiple projects
- **Agents are anonymous** — branches describe the work, not the worker

### Branch Naming

```
squeeze/gzip-streaming              # Feature in squeeze
ritz/parser-error-recovery          # Feature in ritz compiler
valet/http2-support                 # Feature in valet
async-io-overhaul                   # Cross-project feature
tls-1.3-integration                 # Touches cryptosec, valet, http
hotfix/critical-parser-null         # Urgent fix
```

### Workflow

```bash
# 1. Create your branch from main (name describes the work)
git checkout -b squeeze/gzip-streaming main

# 2. Work on your changes (can touch multiple projects)
vim projects/squeeze/src/gzip.ritz
vim projects/valet/src/compress.ritz

# 3. Build and test affected projects
make -C projects/squeeze test
make -C projects/valet test

# 4. Commit (can include multiple projects in one commit)
git add projects/squeeze projects/valet
git commit -m "squeeze,valet: Add gzip streaming support"

# 5. Push and create PR
git push -u origin squeeze/gzip-streaming
gh pr create --title "Add gzip streaming support"

# 6. PR is squash-merged to main
# 7. Delete your branch
git branch -d squeeze/gzip-streaming
```

---

## Agent Isolation with Worktrees

Each agent works in an isolated git worktree. Agents join a "room" (workspace) and work on whatever needs doing:

```bash
# Create a worktree for a room (e.g., "squeeze" room works on squeeze)
git worktree add ~/dev/rz-worktrees/squeeze -b squeeze/current-work main

# Work in isolation
cd ~/dev/rz-worktrees/squeeze
export RITZ_PATH=$PWD/projects

# Your changes don't affect other rooms
# Other rooms' changes don't affect you
# Main stays stable

# When done with this branch, clean up and start fresh
git worktree remove ~/dev/rz-worktrees/squeeze
```

### Why Worktrees?

- **Complete isolation** — each room has its own filesystem view
- **No file locking** — multiple rooms can work on the same files in parallel
- **Efficient** — git shares objects between worktrees
- **Stable base** — always branch from green main

---

## Cross-Project Changes

The monorepo makes cross-project changes trivial:

### Single Commit, Multiple Projects

```bash
# Fix a bug in ritzlib that affects squeeze and valet
vim projects/ritz/ritzlib/vec.ritz      # Fix the bug
vim projects/squeeze/src/deflate.ritz   # Update usage
vim projects/valet/src/handler.ritz     # Update usage

# One commit captures the entire change
git add projects/ritz projects/squeeze projects/valet
git commit -m "ritzlib,squeeze,valet: Fix vec_push edge case

* ritzlib: Handle zero-capacity vectors
* squeeze: Update deflate to use fixed behavior
* valet: Update handler to use fixed behavior"
```

### Finding Affected Projects

```bash
# What depends on ritzlib?
grep -r "import ritzlib" projects/*/src/ | cut -d: -f1 | xargs dirname | sort -u

# What files changed since main?
git diff --name-only main | grep "^projects/"
```

---

## Idiomatic Ritz (What NOT to Write)

**You are not a C developer. Write Ritz, not C-with-indentation.**

### Anti-Patterns → Idiomatic Ritz

| ❌ C-Style (Bad) | ✅ Idiomatic Ritz (Good) |
|------------------|--------------------------|
| `fn process(data: *Data)` | `fn process(data: Data)` — const borrow |
| `fn update(data: *mut Data)` | `fn update(data:& Data)` — mutable borrow |
| `fn consume(data: *Data)` | `fn consume(data:= Data)` — move ownership |
| `c"hello"` | `"hello"` — StrView is default |
| `@test` | `[[test]]` — new attribute syntax |
| `if a && b \|\| !c` | `if a and b or not c` — keywords, not symbols |
| `if ptr != null` | `match opt { Some(x) => ... }` — use Option |
| Manual cleanup | `defer close(fd)` — automatic cleanup |
| `var x = 42` | `let x = 42` — immutable by default |

### Ownership Modifiers (The Ritz Way)

| Syntax | Meaning | When to Use |
|--------|---------|-------------|
| `x: T` | Const borrow | Default — ~70% of parameters |
| `x:& T` | Mutable borrow | When you modify the value |
| `x:= T` | Move ownership | When caller gives up the value |

---

## Language Quick Reference

### Basic Syntax

```ritz
# Functions
fn add(a: i32, b: i32) -> i32
    a + b

# Variables
let x: i32 = 42        # immutable (preferred)
var count: i32 = 0     # mutable (only when needed)

# Control flow
if x > 0
    print("positive\n")
else
    print("non-positive\n")

# Loops
while condition
    do_work()

for i in 0..10         # exclusive range
    process(i)

for i in 0..=10        # inclusive range
    process(i)
```

### Types

| Type | Description |
|------|-------------|
| `i8`, `i16`, `i32`, `i64` | Signed integers |
| `u8`, `u16`, `u32`, `u64` | Unsigned integers |
| `f32`, `f64` | Floating point |
| `bool` | Boolean |
| `*T` | Raw pointer (FFI only) |
| `[N]T` | Fixed-size array |
| `Vec<T>` | Dynamic array |
| `Option<T>` | Optional value |
| `Result<T, E>` | Error handling |
| `StrView` | String slice (default for literals) |
| `String` | Owned heap string |

### Error Handling

```ritz
fn load_config(path: StrView) -> Result<Config, Error>
    let fd = open(path)?           # Propagate error with ?
    defer close(fd)                # Cleanup on scope exit

    let content = read_all(fd)?
    let config = parse(content)?
    Ok(config)
```

### Testing

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0  # return 0 = pass
```

---

## Development Workflow

### TDD Cycle

```
1. SPEC    → Define behavior in a test
2. FAIL    → Run test, verify it fails correctly
3. IMPL    → Write minimal code to pass
4. PASS    → Run test, verify it passes
5. REFAC   → Clean up while tests stay green
6. VERIFY  → Run full test suite
7. COMMIT  → Document the change
```

### Before Committing

```bash
make -C projects/<project> test     # Tests pass
make -C projects/<project> valgrind # No memory leaks (if applicable)
```

### Commit Message Format

```
<scope>: 🤖 <description>

* Summary if necessary
* Keep it brief

Co-Authored-By: Claude <noreply@anthropic.com>
```

For cross-project changes:
```
ritzlib,squeeze,valet: 🤖 <description>
```

---

## Style Guidelines

### Ritz Code

- **Indentation:** 4 spaces (no tabs)
- **Line length:** 100 characters max
- **Naming:**
  - `snake_case` for functions and variables
  - `PascalCase` for types and structs
  - `SCREAMING_SNAKE` for constants
- **Logical operators:** `and`, `or`, `not` (not `&&`, `||`, `!`)
- **Strings:** Plain `"string"` (not `c"string"`)
- **Attributes:** `[[test]]` (not `@test`)
- **Borrows:** Use `:`, `:&`, `:=` modifiers (not raw pointers)

---

## Key Resources

| Resource | Location |
|----------|----------|
| Language Spec | `projects/larb/docs/LANGUAGE_SPEC.md` |
| Design Decisions | `projects/larb/docs/DESIGN_DECISIONS.md` |
| Style Guide | `projects/larb/docs/STYLE.md` |
| Ecosystem Overview | `projects/larb/docs/ECOSYSTEM.md` |
| ritzlib Reference | `projects/larb/docs/STDLIB_REFERENCE.md` |

---

## Remember

1. **No Concessions** — Fix the language, don't work around it
2. **Write Ritz, not C** — Use borrows, Option, defer, keywords
3. **Atomic Changes** — Cross-project changes in one commit
4. **Test First** — TDD is not optional
5. **Main is Green** — Always branch from stable main

---

*This prompt is maintained by LARB (Language Architecture Review Board).*
