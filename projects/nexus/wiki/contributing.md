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
- Track issues in GitHub Issues
- Investigate test flakiness immediately
- Treat compiler warnings as bugs

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

### Clone the Ecosystem

```bash
mkdir -p ~/dev/ritz-lang
cd ~/dev/ritz-lang
git clone https://github.com/ritz-lang/ritz.git ritz
# Clone other projects as needed
git clone https://github.com/ritz-lang/squeeze.git squeeze
git clone https://github.com/ritz-lang/cryptosec.git cryptosec
git clone https://github.com/ritz-lang/valet.git valet
```

### Set RITZ_PATH

```bash
export RITZ_PATH=~/dev/ritz-lang
export PATH="$RITZ_PATH/ritz:$PATH"
```

Add to your `~/.bashrc` or `~/.zshrc`.

---

## Workflow

### Working on a Feature

```bash
# 1. Go to the relevant project
cd $RITZ_PATH/ritz         # or squeeze, valet, etc.

# 2. Create a branch
git checkout -b feature/my-feature

# 3. TDD: write failing test
# edit src/mymodule.ritz

# 4. Run tests (should fail)
make test

# 5. Implement the feature
# edit src/mymodule.ritz

# 6. Run tests (should pass)
make test

# 7. Commit
git add -p
git commit -m "ritzlib: 🤖 Add vec_sort_by function

* Enables custom comparator for Vec sorting
* 3 tests covering normal, reverse, and stable sort"

# 8. Push and open PR
git push -u origin feature/my-feature
gh pr create --title "Add vec_sort_by function" --body "..."
```

### Fixing a Bug in a Dependency

If you're working in `myapp` and find a bug in `squeeze`:

```bash
cd $RITZ_PATH/squeeze
git checkout -b fix/deflate-edge-case

# Write failing test for the bug
# Fix the bug
# Verify tests pass

git push -u origin fix/deflate-edge-case
gh pr create ...

# Continue working in myapp — it already sees the fix
cd $RITZ_PATH/myapp
```

---

## Which Repository?

| Change | Repository |
|--------|------------|
| Language feature or syntax | `ritz` |
| Standard library (ritzlib) | `ritz` |
| Test framework | `ritzunit` |
| Compression | `squeeze` |
| Cryptography | `cryptosec` |
| HTTP server | `valet` |
| App server | `zeus` |
| Database | `mausoleum` |
| Cache | `tome` |
| Web framework | `spire` |
| Kernel | `harland` |
| Language standards/docs | `larb` |
| This wiki | `nexus` |

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

Before submitting a PR:

```bash
# Run all tests
make test

# For memory safety (if applicable)
make valgrind

# Run with specific filter
ritz test . --filter test_my_feature
```

Tests must pass. The CI will verify.

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

See [related concept](../language/ownership.md) for details.

Or link to a project: [Valet](../projects/valet.md).
```

---

## Finding Work

- **GitHub Issues** — Each repository has an issues list
- **TODO.md** — Each project has a `TODO.md` with planned work
- **DONE.md** — Each project has a `DONE.md` for reference

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
