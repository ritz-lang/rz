# Contributing to Ritz

Welcome! Ritz is an open-source project and contributions are welcome across all 20+ ecosystem repositories.

---

## Core Doctrines

Before contributing, understand the two core doctrines that guide all Ritz development:

### No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

If you find something you cannot express cleanly in Ritz, the right answer is to fix the language — not to work around it. Every awkward pattern is an opportunity to improve Ritz.

When you encounter a limitation:
1. Check if there's an idiomatic way you may have missed
2. If not, implement the feature in `ritz/ritzlib` with proper tests
3. Submit the change upstream via pull request
4. Then use it in your project

### Ghost Doctrine

> "Warnings are the ghosts of future production outages."

- Fix anomalies when you discover them, not later
- Track issues in AGAST, the task tracker
- Investigate test flakiness immediately
- Treat compiler warnings as bugs
- Distrust a green result you did not watch go red first

---

## Test-Driven Development

All contributions must follow strict TDD:

1. **Write failing tests first** — Define the expected behavior before implementing
2. **Implement to make tests pass** — Write the minimum code needed
3. **Refactor with confidence** — Clean up while tests stay green
4. **All tests must pass before committing**

```
TDD Cycle:
1. SPEC   → Write a failing test
2. FAIL   → Run test, verify it fails correctly (not accidentally passing)
3. IMPL   → Write minimal implementation
4. PASS   → Run test, verify it passes
5. REFAC  → Clean up code
6. VERIFY → Run full test suite
7. COMMIT → Document the change
```

---

## Setup

### Clone the monorepo

Everything lives in one repository. The per-project repos this page used to tell
you to clone (`ritz`, `squeeze`, `cryptosec`, `valet`, …) were consolidated on
2026-02-15; they are private and frozen at that date, so cloning them gets you a
stale snapshot.

```bash
git clone git@github.com:ritz-lang/rz.git
cd rz
```

### RITZ_PATH

You usually do not need to set it. The workspace-root `./rz` CLI sets `RITZ_PATH`
itself, and overrides whatever you exported.

You only need it when invoking the compiler or build system directly, and the
correct value is the ritz package root — **not** the workspace root and not the
`ritzlib` directory:

```bash
RITZ_PATH=$PWD/projects/ritz python3 projects/ritz/build.py build <path/to/package>
```

Without it, anything importing ritzlib fails with `Cannot find module: ritzlib.io`,
which reads like a broken package rather than a missing variable.

---

## Workflow

### Working on a Feature

All commands run from the repository root — there is one repo, one branch, one
history.

```bash
# 1. Create a branch
git checkout -b feature/my-feature

# 2. TDD: write the failing test first
#    edit projects/<project>/test/test_mymodule.ritz

# 3. Run it and confirm it fails for the RIGHT reason
./rz test <project>

# 4. Implement
#    edit projects/<project>/lib/mymodule.ritz

# 5. Run again — should pass
./rz test <project>

# 6. Commit
git add -p
git commit -m "ritzlib: 🤖 Add vec_sort_by function

* Enables custom comparator for Vec sorting
* 3 tests covering normal, reverse, and stable sort"

# 7. Push and open a PR
git push -u origin feature/my-feature
gh pr create --title "Add vec_sort_by function" --body "..."
```

Step 3 is not optional. A test that passes before you implement anything is
testing nothing, and that has happened here often enough to be worth a step of its
own.

### Fixing a bug in a dependency

Dependencies are directories in this repo, not separate checkouts. Fix
`projects/squeeze` in the same branch as the caller that needed it, and add the
regression test next to the fix. There is no cross-repo PR dance and no version to
bump.

---

## Which directory?

One repository; these are paths within it. `./rz list` prints the authoritative
set of buildable projects.

| Change | Path |
|--------|------|
| Language feature or syntax | `projects/ritz/ritz0` (and `ritz1` for the self-hosted compiler) |
| Standard library (ritzlib) | `projects/ritz/ritzlib` |
| Language standard / style | `projects/ritz/docs/LANGUAGE_SPEC.md`, `projects/ritz/docs/STYLE.md` |
| Test framework | `projects/ritzunit` |
| Compression | `projects/squeeze` |
| Cryptography | `projects/cryptosec` |
| HTTP server | `projects/valet` |
| App server | `projects/zeus` |
| Database | `projects/mausoleum` |
| Cache | `projects/tome` |
| Web framework | `projects/spire` |
| Kernel | `projects/harland` |
| This wiki | `projects/nexus/wiki` |

`projects/larb` is a documentation-only directory and is not a buildable project;
the language standard moved into `projects/ritz/docs/` on 2026-09-03.

---

## Code Style

### Ritz Code

- **Indentation:** 4 spaces (no tabs)
- **Line length:** 100 characters max
- **Functions and variables:** `snake_case`
- **Types and structs:** `PascalCase`
- **Constants:** `SCREAMING_SNAKE`
- **Logical operators:** `and`, `or`, `not` (not `&&`, `||`, `!`)
- **String literals:** `"string"` (not `c"string"` except for FFI)
- **Test attributes:** `[[test]]` (not `@test`)

### Ownership

Use the correct ownership modifier:

```ritz
# Correct
fn process(data: Vec<u8>) -> Summary     # Const borrow
fn update(config:& Config)               # Mutable borrow
fn consume(conn:= Connection)            # Move

# Wrong — do not use raw pointer style
fn process(data: *Vec<u8>)               # Never do this
fn update(config: *mut Config)           # Never do this
```

### Comments

```ritz
# Good: comment the WHY, not the WHAT
# We use mmap instead of malloc to avoid glibc dependency
let ptr = mmap(null, size, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_PRIVATE, -1, 0)

# Bad: restates the code
# Call mmap with size
let ptr = mmap(null, size, ...)
```

---

## Commit Messages

```
<scope>: 🤖 <short description>

* Summary bullet if needed
* Keep it brief

Co-Authored-By: Claude <noreply@anthropic.com>
```

Examples:
- `ritzlib: 🤖 Add sort_by to Vec<T>`
- `valet: 🤖 Fix keepalive connection leak`
- `cryptosec: 🤖 Implement Ed25519 signature verification`
- `harland: 🤖 Add page table fault handling`

---

## Testing

Before submitting a PR, from the repository root:

```bash
# Tests for one project
./rz test <project>

# The compiler's full gate — exactly what CI runs, in CI's order
make -C projects/ritz ci-local

# Memory safety (only projects/ritz has this target)
make -C projects/ritz valgrind
```

Tests must pass. CI will verify.

Two traps this page used to walk into, both of which report success while doing
nothing:

- `make -C projects/<project> test` exits 0 with "Nothing to be done for 'test'"
  for most projects, because only a handful have a Makefile and `make` matches the
  existing `test/` *directory* as an already-up-to-date target. Use `./rz test`.
- There is no `ritz` binary, so `ritz test . --filter …` exits 127.

---

## Pull Request Guidelines

### Title

Keep it concise (under 70 characters). Describe what changes, not implementation details.

- "Add vec_sort_by for custom comparators" (good)
- "Implement the sort_by method on Vec<T> generic collection" (too long)

### Body

```markdown
## What

Short description of what this changes.

## Why

Why this change is needed. What problem does it solve?

## Test Plan

- [ ] Unit tests for the new function
- [ ] Edge cases: empty vec, single element, duplicate values
- [ ] Existing tests still pass
```

### Reviews

- All PRs require at least one review before merging
- Address all review comments
- Keep the PR focused — one feature or fix per PR

---

## Contributing to This Wiki

The wiki content lives at `/home/aaron/dev/ritz-lang/rz/projects/nexus/wiki/`.

To add or update content:

1. Edit the relevant `.md` file
2. Preview in any Markdown viewer
3. Submit a PR to the `nexus` repository

Wiki pages use standard Markdown with internal links:

```markdown
# My Page

See [related concept](language/ownership.md) for details.

Or link to a project: [Valet](projects/valet.md).
```

---

## Finding Work

- **AGAST** — the task tracker, and the single source of truth for what is open,
  what is blocked, and why. Work is claimed and completed there.
- **The regression allowlists** — `projects/ritz/scripts/regression-known-failures*.txt`
  list the examples each compiler cannot yet handle. Each entry is a claim about
  the compiler, with its reasoning in the file's header comments.

Per-project `TODO.md` / `DONE.md` files used to be listed here. They were deleted
on 2026-09-12 after going seven months stale — several listed work as unstarted
that had already shipped. Do not recreate them.

Good first contributions:
- Add tests for untested edge cases
- Fix a bug from the Issues list
- Improve documentation for a confusing API
- Add a missing standard library function

---

## Getting Help

- GitHub Discussions on each repository
- GitHub Issues for bug reports and proposals
- LARB (Language Architecture Review Board) for language-level questions

---

## The Flat Ecosystem

All projects share a flat directory structure under `RITZ_PATH`. There are no nested submodules. When you change `ritz`, all projects immediately see the change. This design:

- Eliminates dependency hell (one copy of each project)
- Makes cross-project refactoring easy
- Encourages upstream contribution

---

*Thank you for contributing to Ritz!*
