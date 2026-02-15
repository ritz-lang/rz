# ritz-stats

Source code analytics for Ritz projects. Similar to cloc/sloccount but tailored for Ritz with language-specific metrics.

## Features

- **Line counting**: Total, code, comment, and blank lines
- **Function metrics**: Line count, cyclomatic complexity, nesting depth
- **Definition tracking**: Functions, structs, enums, imports
- **Hotspot detection**: Identifies high-complexity functions
- **Per-file breakdown**: Detailed stats for each source file
- **JSON output**: For CI/CD integration

## Usage

```bash
# Analyze a directory
ritz-stats src/

# Verbose output with per-file details
ritz-stats -v .

# JSON output for tooling
ritz-stats --json src/ > stats.json

# Show help
ritz-stats --help
```

## Output Example

```
============================================================
                    RITZ SOURCE STATISTICS
============================================================

LINES OF CODE
----------------------------------------
  Total lines:      12,847
  Code lines:       9,234 (71.9%)
  Comment lines:    1,456 (11.3%)
  Blank lines:      2,157 (16.8%)

DEFINITIONS
----------------------------------------
  Functions:        287
  Structs:          45
  Enums:            23
  Files:            34

COMPLEXITY
----------------------------------------
  Avg function length:     32.2 lines
  Avg cyclomatic complexity: 4.7
  Max cyclomatic complexity: 28
  Deepest nesting:         6 levels

HOTSPOTS (High Complexity Functions)
------------------------------------------------------------
  CC 28 | 156 lines | src/parser.ritz:234 parse_expression
  CC 19 | 89 lines  | src/codegen.ritz:567 emit_match
  CC 15 | 67 lines  | src/lexer.ritz:123 scan_token
```

## Metrics Explained

### Cyclomatic Complexity (CC)

Measures the number of independent paths through the code:

| CC | Risk Level | Action |
|----|------------|--------|
| 1-4 | Low | Simple, well-tested |
| 5-10 | Moderate | More attention needed |
| 11-20 | High | Consider refactoring |
| 21+ | Very High | Split into smaller functions |

Counted decision points:
- `if`, `elif` statements
- `while`, `for`, `loop` loops
- Match arms (`=>`)
- Logical operators (`and`, `or`)
- Error propagation (`?`)

### Nesting Depth

Maximum indentation level within functions. Deep nesting (>4 levels) often indicates:
- Complex conditionals that could be simplified
- Missing early returns
- Functions doing too much

## JSON Schema

```json
{
  "total_lines": 12847,
  "code_lines": 9234,
  "comment_lines": 1456,
  "blank_lines": 2157,
  "function_count": 287,
  "struct_count": 45,
  "enum_count": 23,
  "file_count": 34,
  "avg_function_length": 32.2,
  "avg_cyclomatic_complexity": 4.7,
  "max_cyclomatic_complexity": 28,
  "deepest_nesting": 6
}
```

## Integration

### GitHub Action

```yaml
name: Code Stats
on: [push]
jobs:
  stats:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ritz-stats
        run: |
          ritz-stats --json src/ > stats.json
          cat stats.json
```

### Pre-commit (complexity guard)

Fail commits with overly complex functions:

```bash
#!/bin/bash
# .git/hooks/pre-commit
MAX_CC=15
stats=$(ritz-stats --json src/)
max=$(echo "$stats" | grep max_cyclomatic_complexity | grep -o '[0-9]*')
if [ "$max" -gt "$MAX_CC" ]; then
    echo "Error: Max cyclomatic complexity ($max) exceeds threshold ($MAX_CC)"
    ritz-stats src/ | grep "HOTSPOTS" -A 20
    exit 1
fi
```

## Building

```bash
cd $RITZ_PATH/larb/tools/ritz-stats
ritz build
```

## See Also

- [ritz-lint](../ritz-lint/) - AI-powered code linter
- [PR_CHECKLIST.md](../../docs/PR_CHECKLIST.md) - PR readiness process
