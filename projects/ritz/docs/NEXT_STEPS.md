# Next Steps - Ritz Language Development

**Last Updated:** Post ritzlib.args refactoring + code review

---

## Completed This Session

- **Fixed `argz` → `args` typo** across entire codebase (ritzlib, examples, docs)
- **Refactored 27 examples** to use `ritzlib.args` for declarative argument parsing
- **Fixed multi-positional bug** in args library (affected `tr`, `grep`, `uniq`)
- **Identified limitation**: `find` uses single-dash long options (`-type`) which args library doesn't support
- **Closed GitHub Issue #38** - Refactor remaining examples to use ritzlib imports
- **Verified all 147 language tests pass**
- **Tested examples compile and run correctly** (tr, ls, grep verified)

---

## Build System Notes

**Current toolchain:**
- LLVM 20.1 (Ubuntu) for IR compilation
- Clang for linking (recommended - GNU assembler has DWARF5 compatibility issue)

**Compilation:**
```bash
# Compile Ritz → LLVM IR
python3 ritz0/ritz0.py source.ritz -o output.ll

# Link with clang (recommended)
clang output.ll -o binary -nostdlib

# Alternative (may fail with DWARF debug info):
# llc output.ll -o output.s && as output.s -o output.o && ld -o binary output.o
```

**Known issue:** GNU binutils 2.45 doesn't support DWARF5's enhanced `.file` directive syntax.

---

## Immediate Next Steps

### 1. Process Examples (Tier 4 Extension)

The original Tier 4 was network services, but we need process management first:

| Example | Description | New Features Needed |
|---------|-------------|---------------------|
| `kill` | Send signals to processes | `sys_kill()` syscall |
| `ps` | List processes | `/proc` parsing |
| `pgrep` | Search for processes | Pattern matching + `/proc` |
| `nohup` | Run command immune to hangups | `fork()`, `exec()`, signal handling |
| `timeout` | Run command with time limit | Alarm signals |
| `env` | Run with modified environment | Environment manipulation |
| `xargs` | Build commands from stdin | Process spawning, argument building |

**Prerequisites:**
- Add `sys_fork()`, `sys_execve()`, `sys_waitpid()` to `ritzlib/sys.ritz`
- Add `sys_kill()`, `sys_signal()` for signal handling
- Consider adding `ritzlib/proc.ritz` for process utilities

### 2. ritzlib.args Improvements

**Known limitations to address:**

1. **Single-dash long options** (GNU find style)
   - Current: `-type` is parsed as `-t` with value `ype`
   - Fix: Add support for single-dash long options as an opt-in

2. **Subcommand support**
   - Needed for: `git`-style CLIs with subcommands
   - Pattern: `tool <subcommand> [options]`

3. **Repeatable options**
   - Current: Each option can only appear once
   - Needed for: `-v -v -v` verbose levels, multiple `-e` patterns

4. **Option groups**
   - Mutually exclusive options (e.g., `-q` and `-v`)
   - Dependent options (e.g., `-R` requires `-f`)

### 3. Code Quality Items

- [ ] Add test cases for `ritzlib/args.ritz` functionality
- [ ] Document the args library API in `docs/RITZLIB.md`
- [ ] Consider extracting common patterns from examples into ritzlib

---

## Phase 2 Completion Checklist

### Tier 2 Text Processing (11-20)

All examples implemented, but TODO.md shows some as incomplete:

| Example | Status | ritzlib.args | Notes |
|---------|--------|--------------|-------|
| 11_grep | ✅ Works | ✅ | Fixed positional args |
| 12_tac | ✅ Works | ✅ | Needs test with large files |
| 13_sort | ✅ Works | ✅ | Needs numeric sort (-n) |
| 14_uniq | ✅ Works | ✅ | Fixed positional args |
| 15_cut | ✅ Works | ✅ | |
| 16_tr | ✅ Works | ✅ | Fixed positional args |
| 17_expand | ✅ Works | ✅ | |
| 18_nl | ✅ Works | ✅ | |
| 19_base64 | ✅ Works | ✅ | |
| 20_xxd | ✅ Works | ✅ | |

**Update TODO.md:** Mark all Tier 2 examples as complete.

### Tier 3 Filesystem Utilities (21-30)

| Example | Status | ritzlib.args | Notes |
|---------|--------|--------------|-------|
| 21_ls | ✅ Works | ✅ | |
| 22_mkdir | ✅ Works | ✅ | |
| 23_rm | ✅ Works | ✅ | |
| 24_cp | ✅ Works | ✅ | |
| 25_mv | ✅ Works | ✅ | |
| 26_touch | ✅ Works | ✅ | |
| 27_stat | ✅ Works | ✅ | |
| 28_chmod | ✅ Works | ✅ | |
| 29_du | ✅ Works | ✅ | |
| 30_find | ✅ Works | ⚠️ | Single-dash options not supported |

---

## Language Features to Consider

Based on patterns observed during refactoring:

### High Priority

1. **Character literals** - `'a'` instead of `97`
   - Many examples use ASCII codes: `c == 97` vs `c == 'a'`
   - Improves readability significantly

2. **Bitwise operations** - `&`, `|`, `^`, `~`
   - Currently using arithmetic workarounds
   - Needed for: chmod, permission handling, bit flags

3. **Compound assignment** - `+=`, `-=`, `*=`
   - Reduces boilerplate: `i = i + 1` → `i += 1`

### Medium Priority

4. **Method syntax** - `obj.method()` as sugar for `fn(obj)`
   - Pattern: `charset_add(cs, c)` → `cs.add(c)`
   - Would clean up examples significantly

5. **Const expressions** - Compile-time evaluation
   - Pattern: `const BUFSIZE = 4096`
   - Currently using magic numbers or vars

6. **Default parameter values**
   - Pattern: `fn read(fd: i32, buf: *u8, len: i64 = 4096)`

---

## Issues to File

1. **args library validation** - Only validates first positional definition
2. **Single-dash long options** - Not supported (GNU find incompatibility)
3. **Character literal syntax** - Not implemented
4. **Bitwise operators** - Not implemented (using arithmetic workarounds)

---

## Testing Strategy

Before moving to Tier 4:

1. **Run all examples** against real-world inputs
2. **Valgrind check** - Ensure no memory leaks
3. **Edge cases** - Empty input, large files, special characters
4. **Error handling** - Invalid arguments, missing files, permission denied

```bash
# Build and test all examples
make examples
make valgrind

# Test specific examples
echo "hello world" | examples/16_tr/tr l r  # Expected: herro worrd
examples/11_grep/grep pattern file.txt
examples/30_find/find . --type f --name "*.ritz"
```

---

## Decision Points

1. **Tier 4 direction**: Network services or process management first?
   - Recommendation: Process management (more useful for system tools)

2. **String type**: When to implement proper `String` type?
   - Current: Using `*u8` everywhere
   - Consideration: Wait until generics for `Vec<u8>`-based String

3. **Self-hosting timeline**: When to revisit ritz1?
   - Current recommendation: After Tier 4, when language is more stable
