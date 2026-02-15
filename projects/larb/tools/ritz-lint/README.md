# ritz-lint

AI-powered Ritz code reviewer that catches "C developer code in Ritz clothing".

## What It Catches

| Anti-Pattern | Idiomatic Ritz |
|--------------|----------------|
| `fn foo(x: *T)` | `fn foo(x: T)` (const borrow) |
| `fn foo(x: *mut T)` | `fn foo(x:& T)` (mutable borrow) |
| `c"string"` | `"string"` (StrView default) |
| `@test` | `[[test]]` |
| `&&` / `\|\|` / `!` | `and` / `or` / `not` |
| `if ptr != null` | `match opt { Some(x) => ... }` |
| Missing `defer` | Resource cleanup with `defer` |
| Excessive `var` | Prefer `let` (immutable by default) |

## Requirements

- `claude` CLI installed and authenticated
- Works with Claude Max subscription (no API key needed)

## The Purist

This linter is **intentionally strict**. It's not here to make suggestions — it's here to enforce idiomatic Ritz. If your code looks like C, it will tell you. Harshly.

See [PR_CHECKLIST.md](../../docs/PR_CHECKLIST.md) for the full PR readiness process.

## Usage

```bash
# Lint a file
python ritz_lint.py handler.ritz

# Lint a directory
python ritz_lint.py src/

# JSON output (for CI)
python ritz_lint.py src/ --json

# No color (for pipes)
python ritz_lint.py src/ --no-color
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No issues (or only suggestions) |
| 1 | Warnings found |
| 2 | Errors found |

## Example Output

```
⚠ handler.ritz:5: [no-raw-pointers]
  Function parameter uses raw pointer instead of borrow
  fn process(data: *Data)
  → fn process(data: Data)  # const borrow

⚠ handler.ritz:12: [no-c-strings]
  Unnecessary c"" prefix, use StrView default
  print(c"Hello\n")
  → print("Hello\n")

→ handler.ritz:25: [prefer-keywords]
  Use keyword operators for readability
  if a && b || !c
  → if a and b or not c

Checked 1 file(s): 3 issue(s)
  2 warning(s), 1 suggestion(s)
```

## Integration

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ritz-lint
        name: ritz-lint
        entry: python tools/ritz-lint/ritz_lint.py
        language: python
        files: \.ritz$
        additional_dependencies: [anthropic]
```

### GitHub Action

```yaml
# .github/workflows/lint.yml
name: Ritz Lint
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install anthropic
      - run: python tools/ritz-lint/ritz_lint.py src/
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Pre-commit Hook

Install automatic linting on every commit:

```bash
$RITZ_PATH/larb/tools/ritz-lint/install-hook.sh
```

To bypass (not recommended):
```bash
git commit --no-verify
```

## How It Works

1. Collects all `.ritz` files from the target path
2. Sends code to Claude (via `claude` CLI) with a purist system prompt
3. Parses the structured JSON response
4. Outputs formatted lint results with harsh but helpful feedback

The system prompt embeds the current Ritz idioms and enforces them strictly.

## Cost

Uses your Claude Max subscription via the `claude` CLI — no additional API costs.
