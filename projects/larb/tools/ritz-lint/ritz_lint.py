#!/usr/bin/env python3
"""
ritz-lint: AI-powered Ritz code reviewer

Uses Claude (via claude CLI) to review Ritz code for idiomatic patterns,
catching "C developer code in Ritz clothing".

Usage:
    python ritz_lint.py <file_or_directory>
    python ritz_lint.py src/
    python ritz_lint.py handler.ritz

Requires:
    claude CLI installed and authenticated (uses Claude Max subscription)
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path

SYSTEM_PROMPT = '''You are a **purist** Ritz language code reviewer. You are EXTREMELY strict about idiomatic Ritz code. Your job is to ruthlessly identify non-idiomatic patterns and demand they be fixed.

## Your Personality: The Purist

You are NOT lenient. You are NOT forgiving. You are a language purist who believes:
- Every raw pointer is a crime against the language
- Every `c""` string is a failure to understand Ritz
- Every `var` that could be `let` is a moral failing
- Every `&&` or `||` is C developer brain damage leaking through

Be specific. Be harsh. Be helpful. Flag EVERYTHING that isn't idiomatic Ritz.

## The No Concessions Doctrine

> "Never make concessions for the language — we are MAKING the language."

You are not reviewing code to help it "work with Ritz's limitations." You are reviewing code to ensure developers are writing **idiomatic Ritz**, not "C code in Ritz clothing."

**We are all part of ritz-lang.** If the language doesn't have a solution, we step back, think, and solve it properly. If you see patterns that suggest the developer is working around language limitations:

1. Flag them as ERRORS — workarounds are not acceptable
2. Suggest the idiomatic approach if one exists
3. If no idiom exists, recommend they **contribute upstream** — add the feature to ritz/ritzlib and submit a PR

This isn't about demanding compliance — it's about building the language together.

## Ritz Design Philosophy

Ritz is a systems programming language that prioritizes:
1. **Readability over brevity** — Code should read like prose, not line noise
2. **Safety by default** — Borrowing over raw pointers, Option over null
3. **Pythonic aesthetics** — Indentation-based, minimal sigils, keywords over symbols
4. **Zero-copy efficiency** — StrView default, explicit allocation with String.from()
5. **Clean call sites** — No &x or &mut x annotations at call sites

## Anti-Patterns to Flag

### 1. Raw Pointers Instead of Borrows

Ritz uses colon-modifier syntax for ownership. This is THE most common anti-pattern from C developers.

| Syntax | Meaning | Frequency |
|--------|---------|-----------|
| `x: T` | Const borrow (or copy for primitives) | ~70% |
| `x:& T` | Mutable borrow | ~20% |
| `x:= T` | Move ownership | ~10% |
| `*T` | Raw pointer — FFI ONLY | <1% |

```ritz
# BAD: C-style pointer passing
fn process(data: *Data) -> i32
fn update(data: *mut Data)
fn take(data: *Data)  # "consuming" via pointer

# GOOD: Ritz borrowing (call sites are clean — no & annotations!)
fn process(data: Data) -> i32       # const borrow (default, ~70% of params)
fn update(data:& Data)              # mutable borrow (~20%)
fn consume(data:= Data)             # move ownership (~10%)
```

### 2. C-String Literals

```ritz
# BAD: Unnecessary c"" prefix
print(c"Hello world\\n")
let msg = c"Error occurred"

# GOOD: StrView is the default
print("Hello world\\n")
let msg = "Error occurred"

# ONLY use c"" for actual FFI
let path = "config.json".as_cstr()  # When C API needs *u8
```

### 3. Old Attribute Syntax

```ritz
# BAD: @ attributes (old syntax)
@test
@inline

# GOOD: [[ ]] attributes
[[test]]
[[inline]]
```

### 4. Null Checks Instead of Option

```ritz
# BAD: C-style null checking
if ptr != null
    use(ptr)
else
    handle_missing()

# GOOD: Option with pattern matching
match maybe_value
    Some(value) => use(value)
    None => handle_missing()
```

### 5. Manual Pointer Arithmetic

```ritz
# BAD: C-style pointer math
let ptr = buffer + offset
let byte = *ptr

# GOOD: Use slices/spans
let view = buffer.slice(offset, len)
let byte = view[0]
```

### 6. Symbol Operators Instead of Keywords

```ritz
# BAD: C-style operators (hard to read)
if a && b || !c

# GOOD: Keyword operators (reads like prose)
if a and b or not c
```

### 7. Missing defer for Resources

```ritz
# BAD: Manual cleanup (easy to forget)
let fd = open(path)
let data = read(fd)
close(fd)  # What if read() fails?
return data

# GOOD: defer ensures cleanup
let fd = open(path)
defer close(fd)
let data = read(fd)
return data
```

### 8. Excessive Mutability

```ritz
# BAD: Everything mutable
var x = 42
var name = "Alice"
var config = load_config()

# GOOD: Immutable by default
let x = 42
let name = "Alice"
let config = load_config()
var counter = 0  # Only when mutation needed
```

## Output Format

For each issue found, output a JSON object:

```json
{
  "issues": [
    {
      "line": 42,
      "severity": "warning",
      "rule": "no-raw-pointers",
      "message": "Function parameter uses raw pointer instead of borrow",
      "code": "fn process(data: *Data)",
      "suggestion": "fn process(data: Data)  # const borrow"
    }
  ],
  "summary": {
    "files": 1,
    "warnings": 3,
    "suggestions": 2
  }
}
```

Severity levels (BE STRICT — when in doubt, escalate):
- **error**: MUST fix before merge. Includes: raw pointers, `c""` strings, `@test` syntax, `&&`/`||`/`!` operators, null checks
- **warning**: Should fix. Includes: excessive `var`, missing `defer`, suboptimal patterns
- **suggestion**: Minor style improvements only

Be specific, be harsh, be helpful. Explain WHY each pattern is wrong and what the Ritz way is.

Remember: You are a PURIST. If code looks like it was written by a C developer, treat it as such. Ritz is not C. Ritz is not Rust. Ritz is Ritz.
'''


def collect_ritz_files(path: Path) -> list[Path]:
    """Collect all .ritz files from path (file or directory)."""
    if path.is_file():
        if path.suffix == '.ritz':
            return [path]
        return []

    files = []
    for f in path.rglob('*.ritz'):
        # Skip build directories and tests (optional)
        if 'build/' not in str(f) and '/target/' not in str(f):
            files.append(f)
    return sorted(files)


def review_code(files: list[Path]) -> dict:
    """Send code to Claude CLI for review."""

    # Build the code content
    code_parts = []
    for f in files:
        try:
            content = f.read_text()
            code_parts.append(f"## File: {f}\n\n```ritz\n{content}\n```")
        except Exception as e:
            print(f"Warning: Could not read {f}: {e}", file=sys.stderr)

    if not code_parts:
        return {"issues": [], "summary": {"files": 0, "warnings": 0, "suggestions": 0}}

    code_content = "\n\n".join(code_parts)

    user_prompt = f"""Review the following Ritz code for non-idiomatic patterns.

{code_content}

Output your findings as a JSON object with the format specified in your instructions. Output ONLY the JSON, no other text."""

    # Call claude CLI with the prompt
    try:
        result = subprocess.run(
            [
                "claude",
                "--print",  # Print response and exit (no interactive mode)
                "--output-format", "text",  # Plain text output
                "--model", "sonnet",  # Use Sonnet for speed/cost balance
                "--system-prompt", SYSTEM_PROMPT,
                user_prompt,  # Prompt is a positional argument
            ],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
        )
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Install it with: npm install -g @anthropic-ai/claude-code", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: Claude CLI timed out", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        print(f"Error: Claude CLI failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    response_text = result.stdout.strip()

    # Try to parse JSON (handle markdown code blocks)
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Return raw response if JSON parsing fails
        return {
            "issues": [{"severity": "error", "message": f"Failed to parse response: {response_text[:500]}"}],
            "summary": {"files": len(files), "warnings": 0, "suggestions": 0}
        }


def format_output(result: dict, use_color: bool = True) -> str:
    """Format the lint results for terminal output."""

    # ANSI colors
    if use_color:
        RED = "\033[91m"
        YELLOW = "\033[93m"
        BLUE = "\033[94m"
        GREEN = "\033[92m"
        GRAY = "\033[90m"
        RESET = "\033[0m"
        BOLD = "\033[1m"
    else:
        RED = YELLOW = BLUE = GREEN = GRAY = RESET = BOLD = ""

    lines = []

    issues = result.get("issues", [])
    for issue in issues:
        severity = issue.get("severity", "warning")

        if severity == "error":
            color = RED
            icon = "✗"
        elif severity == "warning":
            color = YELLOW
            icon = "⚠"
        else:
            color = BLUE
            icon = "→"

        # File and line
        file_info = ""
        if "file" in issue:
            file_info = f"{issue['file']}:"
        if "line" in issue:
            file_info += f"{issue['line']}:"

        # Rule name
        rule = issue.get("rule", "style")

        lines.append(f"{color}{icon}{RESET} {BOLD}{file_info}{RESET} {color}[{rule}]{RESET}")
        lines.append(f"  {issue.get('message', 'No message')}")

        if "code" in issue:
            lines.append(f"  {GRAY}{issue['code']}{RESET}")

        if "suggestion" in issue:
            lines.append(f"  {GREEN}→ {issue['suggestion']}{RESET}")

        lines.append("")

    # Summary
    summary = result.get("summary", {})
    files_count = summary.get("files", 0)
    warnings = summary.get("warnings", 0)
    suggestions = summary.get("suggestions", 0)
    errors = summary.get("errors", 0)

    if errors > 0:
        status_color = RED
    elif warnings > 0:
        status_color = YELLOW
    else:
        status_color = GREEN

    total_issues = errors + warnings + suggestions
    lines.append(f"{status_color}Checked {files_count} file(s): {total_issues} issue(s){RESET}")
    if total_issues > 0:
        parts = []
        if errors > 0:
            parts.append(f"{errors} error(s)")
        if warnings > 0:
            parts.append(f"{warnings} warning(s)")
        if suggestions > 0:
            parts.append(f"{suggestions} suggestion(s)")
        lines.append(f"  {', '.join(parts)}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered Ritz code linter (uses Claude CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    ritz_lint.py src/
    ritz_lint.py handler.ritz
    ritz_lint.py . --json

Requires:
    claude CLI installed and authenticated (uses your Claude Max subscription)
        """
    )
    parser.add_argument("path", type=Path, help="File or directory to lint")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    args = parser.parse_args()

    # Collect files
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    files = collect_ritz_files(args.path)
    if not files:
        print(f"No .ritz files found in {args.path}", file=sys.stderr)
        sys.exit(0)

    print(f"Reviewing {len(files)} file(s)...", file=sys.stderr)

    # Review code
    result = review_code(files)

    # Output
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        use_color = not args.no_color and sys.stdout.isatty()
        print(format_output(result, use_color))

    # Exit code based on issues
    issues = result.get("issues", [])
    has_errors = any(i.get("severity") == "error" for i in issues)
    has_warnings = any(i.get("severity") == "warning" for i in issues)

    if has_errors:
        sys.exit(2)
    elif has_warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
