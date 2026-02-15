# PR Readiness Checklist

Before submitting a PR to any ritz-lang project, complete this checklist. No exceptions.

---

## The Three Gates

Every PR must pass three gates before it's ready for review:

### Gate 1: Tests Pass

```bash
make test
```

All tests must pass. No flaky tests. No skipped tests. No "it works on my machine."

If tests fail:
1. Fix the code, not the tests (unless the test is wrong)
2. If you're adding new functionality, add new tests
3. Run again until green

### Gate 2: Memory Clean

```bash
make valgrind
```

Or manually:

```bash
valgrind --leak-check=full --error-exitcode=1 ./build/your_binary
```

Zero leaks. Zero errors. Zero "still reachable" (unless explicitly documented as intentional).

**What to look for:**
- `definitely lost` — MUST fix
- `indirectly lost` — MUST fix
- `possibly lost` — investigate and fix
- `still reachable` — usually OK, but verify it's intentional
- `Invalid read/write` — CRITICAL, fix immediately
- `Use of uninitialised value` — MUST fix

### Gate 3: Lint Clean

```bash
python $RITZ_PATH/larb/tools/ritz-lint/ritz_lint.py src/
```

The linter is a **purist**. It will flag:

| Issue | Severity | Action |
|-------|----------|--------|
| Raw pointers (`*T`, `*mut T`) | Error | Convert to borrows (`: T`, `:& T`, `:= T`) |
| C-strings (`c"..."`) | Error | Use `"..."` (StrView default) |
| Old attributes (`@test`) | Error | Use `[[test]]` |
| Symbol operators (`&&`, `\|\|`, `!`) | Error | Use `and`, `or`, `not` |
| Null checks (`if x != null`) | Error | Use `Option<T>` + match |
| Excessive `var` | Warning | Use `let` when possible |
| Missing `defer` | Warning | Add cleanup |

**Exit codes:**
- `0` — Clean (or suggestions only) — OK to proceed
- `1` — Warnings found — should fix before PR
- `2` — Errors found — MUST fix before PR

---

## The Full Sequence

```bash
# 1. Run tests
make test

# 2. Check for memory issues
make valgrind

# 3. Run the linter
python $RITZ_PATH/larb/tools/ritz-lint/ritz_lint.py src/

# 4. If all pass, commit
git add -p                    # Stage carefully
git commit -m "scope: Description

Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Push and create PR
git push -u origin your-branch
gh pr create
```

---

## Quick Alias Setup

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
export RITZ_PATH=~/dev/ritz-lang

# Lint alias
alias ritz-lint="python \$RITZ_PATH/larb/tools/ritz-lint/ritz_lint.py"

# Full PR check
ritz-check() {
    echo "=== Gate 1: Tests ===" && make test && \
    echo "=== Gate 2: Memory ===" && make valgrind && \
    echo "=== Gate 3: Lint ===" && ritz-lint src/ && \
    echo "=== All gates passed! Ready for PR ==="
}
```

Then just run:

```bash
ritz-check
```

---

## Pre-commit Hook (Optional)

For automatic linting on every commit:

```bash
$RITZ_PATH/larb/tools/ritz-lint/install-hook.sh
```

This installs a git hook that runs the linter on staged `.ritz` files.

To bypass (not recommended):
```bash
git commit --no-verify
```

---

## Common Failures and Fixes

### "Raw pointer in function signature"

```ritz
# BAD
fn process(data: *Request) -> i32

# GOOD
fn process(data: Request) -> i32      # const borrow (most common)
fn process(data:& Request) -> i32     # mutable borrow
fn process(data:= Request) -> i32     # move ownership
```

### "C-string literal"

```ritz
# BAD
print(c"Hello\n")

# GOOD
print("Hello\n")
```

### "Symbol operator"

```ritz
# BAD
if a && b || !c

# GOOD
if a and b or not c
```

### "Old attribute syntax"

```ritz
# BAD
@test
fn test_foo() -> i32

# GOOD
[[test]]
fn test_foo() -> i32
```

### "Null check instead of Option"

```ritz
# BAD
if ptr != null
    use(ptr)

# GOOD
match maybe_value
    Some(value) => use(value)
    None => handle_missing()
```

---

## Philosophy

> "Warnings are the ghosts of future production outages."

We don't ship warnings. We don't ship leaks. We don't ship C code in Ritz clothing.

The checklist exists because:
1. **Tests** prove correctness
2. **Valgrind** proves safety
3. **Lint** proves idiomaticity

All three are required. No shortcuts.

---

## When You Hit a Language Limitation

> "We are all part of ritz-lang. If the language doesn't have a solution, we step back, think, and solve it."

If the linter flags something and there's no idiomatic way to fix it:

1. **Don't work around it** — workarounds become tech debt
2. **Step back and think** — is this a language gap or a design issue?
3. **Implement the feature** — add it to ritz/ritzlib with tests
4. **Submit upstream** — create a PR to the ritz repo
5. **If maintainers push back** — start a design session:
   - Reduce coupling between components
   - Respect responsibility boundaries between *behavior*, not data
   - Find a solution that works for the whole ecosystem

The language grows through contribution, not workarounds.

---

*This checklist applies to all ritz-lang ecosystem projects.*
