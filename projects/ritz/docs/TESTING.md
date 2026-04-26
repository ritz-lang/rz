# Ritz Testing

Practical guide to writing and running tests across the Ritz codebase, with
the canonical integration-test template and the gotchas that took an
afternoon to find.

---

## Status (April 2026)

### Tier coverage

| Tier | Pkgs | `test/test_*.ritz` | `test.sh` | Notes |
|---|---|---|---|---|
| 1 (basics 01-10) | 10 | 10/10 ✅ | 10/10 | Mature; tests language features |
| 2 (stdlib 11-20) | 11 | **11/11 ✅** | 11/11 | Backfilled in 2026-04 with the template below |
| 3 (coreutils 21-30) | 10 | 0/10 | 10/10 | Pending — same template applies |
| 4 (apps 31-40) | 10 | 0/10 | 10/10 | Pending |
| 5 (async 41+) | 32 | 9/32 | 24/32 | Partial; async makes the template more complex |
| **Total** | **73** | **30/73** | **65/73** | |

### Test driver

- **Today**: `python3 build.py test <pkg>` → `python3 ritz0 --test test/*.ritz`
  + `bash test.sh` (whichever exists). Each `[[test]]` function is compiled
  into its own binary and run as a subprocess; exit 0 = pass, anything else
  = fail.
- **Tomorrow** (planned): `build.py test` will invoke the native `ritzunit`
  binary instead of `ritz0 --test`. ritzunit benchmarks ~90× faster and
  adds fork isolation (so SIGSEGV in one test doesn't kill the runner).
  Today ritzunit is `test_only=true` and doesn't yet produce a binary —
  see `TODO`.

### ritzunit

Self-tests fully green: **27/27 passing** (as of `186e339`). Lives at
`projects/ritzunit/`. The intentional-failure demo (SIGSEGV / assert /
infinite loop tests for fork isolation) lives at
`projects/ritzunit/examples/isolation_demo.ritz` — moved out of `test/`
because under `ritz0 --test` (no fork isolation) the intentional failures
look like real failures.

---

## The `[[test]]` annotation

A function-level annotation directly above the `fn` declaration. The
parser recognises it; the test runner compiles each annotated function
into a standalone binary and executes it.

```ritz
import ritzlib.sys
import ritzlib.io

[[test]]
fn test_arithmetic() -> i32
    assert 2 + 3 == 5
    assert 10 - 4 == 6
    0  # 0 = pass; assert hard-exits with code 1 on failure
```

**Rules:**
- Test functions must return `i32`; `0` = pass, anything else = fail.
- `assert <cond>` evaluates `<cond>`, and on `false` calls `exit(1)` via
  inline syscall (see `ritz0/emitter_llvmlite.py:_emit_assert`). It does
  *not* return — control never reaches the next line.
- `assert <cond>, c"message"` — same, but the message is currently
  ignored by the runner. Useful as a comment for readers.
- Helper functions in the same file (without `[[test]]`) are linked into
  every test binary that uses them.

**Discovery:**
- `ritz0 --test` parses each `*.ritz` file in `test/`, finds every
  `[[test]]` function, compiles a per-test binary, runs it, and reports.
- For `test_only` packages (like ritzunit itself), `test_*.ritz` at the
  package root is also discovered.

---

## Canonical integration-test template

For example packages (tier 2+), the most valuable tests fork+exec the
built binary with controlled stdin and assert on captured stdout + exit
code. The template below is the pattern from `tier2_stdlib/11_grep/test`
— validated stable across 50+ runs after the harness gotchas (next
section) were sorted.

```ritz
import ritzlib.sys
import ritzlib.io
import ritzlib.str

# ==== Helpers ====

# Compare two byte buffers up to `len` bytes. 1 if equal, else 0.
fn buf_eq(a: *u8, b: *u8, len: i64) -> i32
    var i: i64 = 0
    while i < len
        if *(a + i) != *(b + i)
            return 0
        i += 1
    return 1

# Run ./<binary> with given argv and stdin content; return exit code.
# Captures up to 1024 bytes of stdout into out_buf; writes byte count to
# *out_len. argv must be null-terminated.
#
# Stdin is delivered via a TEMP FILE (not a pipe) — see "Harness gotchas"
# below for why pipes are flaky here.
fn util_exec(argv: **u8, stdin_content: *u8, stdin_len: i64,
             out_buf: *u8, out_len: *i64) -> i32
    # 1. Build a unique temp path: /tmp/ritz_<bin>_stdin_<pid>
    var path_buf: [64]u8
    let prefix: *u8 = c"/tmp/ritz_<bin>_stdin_"
    var i: i64 = 0
    while *(prefix + i) != 0
        path_buf[i] = *(prefix + i)
        i += 1
    let pid_self: i32 = sys_getpid()
    var n: i32 = pid_self
    var d_buf: [16]u8
    var d_len: i32 = 0
    if n == 0
        d_buf[0] = '0'
        d_len = 1
    else
        while n > 0
            d_buf[d_len] = ((n % 10) + 48) as u8
            n = n / 10
            d_len += 1
        var j: i32 = 0
        while j < d_len
            path_buf[i + j] = d_buf[d_len - 1 - j]
            j += 1
        i += d_len
    path_buf[i] = 0

    # 2. Write stdin to temp file
    let fd_w: i32 = sys_open3(@path_buf[0], O_WRONLY + O_CREAT + O_TRUNC, 384)
    if fd_w < 0
        return -1
    if stdin_len > 0
        sys_write(fd_w, stdin_content, stdin_len)
    sys_close(fd_w)

    # 3. Open it for reading (becomes child's fd 0)
    let fd_r: i32 = sys_open(@path_buf[0], O_RDONLY)
    if fd_r < 0
        sys_unlink(@path_buf[0])
        return -2

    # 4. Pipe for stdout capture
    var stdout_pipe: [2]i32
    if sys_pipe(@stdout_pipe[0]) < 0
        sys_close(fd_r)
        sys_unlink(@path_buf[0])
        return -3

    # 5. Fork
    let pid: i32 = sys_fork()
    if pid < 0
        sys_close(fd_r)
        sys_close(stdout_pipe[0])
        sys_close(stdout_pipe[1])
        sys_unlink(@path_buf[0])
        return -4

    if pid == 0
        sys_dup2(fd_r, 0)             # stdin = temp file
        sys_dup2(stdout_pipe[1], 1)   # stdout = pipe write
        sys_close(fd_r)
        sys_close(stdout_pipe[0])
        sys_close(stdout_pipe[1])
        sys_execve(c"./<bin>", argv, null)
        sys_exit(127)

    # 6. Parent: read stdout until EOF
    sys_close(fd_r)
    sys_close(stdout_pipe[1])

    var total: i64 = 0
    while total < 1024
        let r: i64 = sys_read(stdout_pipe[0], out_buf + total, 1024 - total)
        if r <= 0
            break
        total += r
    sys_close(stdout_pipe[0])
    *out_len = total

    # 7. Reap child, clean up
    var status: i32 = 0
    sys_wait4(pid, @status, 0, null)
    sys_unlink(@path_buf[0])
    return (status >> 8) & 0xFF   # WEXITSTATUS

# ==== Tests ====

[[test]]
fn test_basic_invocation() -> i32
    var argv: [3]*u8
    argv[0] = c"./<bin>"
    argv[1] = c"some-arg"
    argv[2] = null

    var out: [1024]u8
    var n: i64 = 0
    let exit_code: i32 = util_exec(@argv[0], c"input data", 10, @out[0], @n)

    assert exit_code == 0, c"binary should exit 0"
    assert n == 12, c"expected 12 bytes back"
    assert buf_eq(@out[0], c"expected out", 12) == 1, c"output mismatch"
    0
```

**To use this template for a new utility:**

1. Copy `tier2_stdlib/11_grep/test/test_grep.ritz` as a starting point.
2. Rename the helper to `<util>_exec`, change every `./grep` and
   `ritz_grep_stdin_` reference to your binary's name.
3. Adjust `argv` size and contents per the binary's CLI.
4. Mirror the scenarios from `test.sh` as `[[test]]` functions, plus
   any unit tests for internal helpers (only useful when there's
   real logic to test — most coreutils-style binaries are pure I/O
   and don't have such helpers).

---

## Harness gotchas (read this before writing more integration tests)

These are documented because they each cost real time to find.

### 1. `sys_read` returns on ANY data, not on EOF

`sys_read` on a blocking pipe returns as soon as there's *any* data
available — not when the writer is done. A naive single read will
catch the first chunk and silently lose the rest if the child writes
more later (e.g., grep emitting one match, computing the next, then
emitting again).

**Fix**: always loop until `sys_read` returns `0` (EOF). The template
above shows the canonical loop. `0` arrives only when the writer's
pipe end is closed (child exited and the OS reaped the fd).

```ritz
var total: i64 = 0
while total < 1024
    let r: i64 = sys_read(stdout_pipe[0], out_buf + total, 1024 - total)
    if r <= 0
        break
    total += r
```

### 2. Temp-file stdin is more reliable than pipe stdin

Even with pre-fork buffering, pipe-based stdin had a residual ~5%
flake under `ritz0 --test`'s harness — usually one test in 10-15
runs would see grep get no input, exit 1 ("no match"), and trip an
assert.

**Fix**: deliver stdin via a temp file (`/tmp/ritz_<bin>_stdin_<pid>`).
Write content, close, open for read, `dup2` into child's fd 0. The
child sees a regular file with full contents and EOF at end. Race-free.

The pid suffix is a `sys_getpid()` call inside the test process — each
`[[test]]` function compiles to its own binary and runs as its own
subprocess, so pids differ per test. No collisions.

### 3. `assert` is a hard exit, not a return

`assert` lowers to inline assembly: `syscall(60, 1)` on x86_64 if the
condition is false. The process exits with code 1 immediately —
control never reaches subsequent statements, no cleanup runs. This
matters because:

- Test code that allocates resources after an assert will leak them
  if the assert fires (usually fine in short test processes).
- Differentiated exit codes for debugging: replace `assert X` with
  `if !X { sys_exit(70 + variant); }` to get a unique code per failure
  path. The runner reports `exited with code 70`, telling you exactly
  which assertion broke without needing stderr (which is captured).

### 4. Move intentional-failure tests to `examples/`, not `test/`

`test_isolation.ritz` in ritzunit was moved out of `test/` to
`examples/isolation_demo.ritz` because its 4 tests intentionally
SIGSEGV / assert-fail / loop forever to demonstrate fork isolation.
Under `ritz0 --test` (no fork isolation) they look like real failures
and trip the build. They're meaningful again once `build.py test`
cuts over to the native ritzunit binary.

Rule of thumb: anything in `test/` should be expected to *pass* under
the current driver. Demonstrators / examples / fixtures live elsewhere.

---

## Running tests

```bash
# Single example
python3 projects/ritz/build.py test projects/ritz/examples/tier2_stdlib/11_grep

# All examples
python3 projects/ritz/build.py test --all

# ritzunit self-tests
python3 projects/ritz/build.py test projects/ritzunit

# Compiler regression matrix (ritz0 + ritz1 + selfhost)
make -C projects/ritz matrix          # ritz1-only, ~12 s
make -C projects/ritz matrix-full     # full bootstrap + matrix, ~1m 40s
```

`RITZ_PATH` must point at `projects/ritz` so `import ritzlib.sys` etc.
resolves. `build.py` sets it automatically; if you call ritz0 directly,
set it yourself.

See `docs/VALIDATION.md` for the full validation workflow (incremental
vs. clean rebuilds, when matrix-full is needed, hard rules).

---

## Test attributes reference

| Attribute | Status | Description |
|---|---|---|
| `[[test]]` | ✅ Implemented | Function-level annotation; runner compiles + runs each |
| `@test` | ⚠️ Deprecated | Older syntax, still parses but the migration to `[[test]]` is complete in tier 1/2 |
| `[[test(should_fail)]]` | ❌ Not implemented | Test expected to exit non-zero (would unblock isolation_demo) |
| `[[test(timeout = N)]]` | ❌ Not implemented | Per-test timeout |
| `[[test(skip)]]` | ❌ Not implemented | Skip unless explicitly requested |

---

## Test file locations

```
projects/ritz/
├── ritz0/
│   ├── test_*.py             # Python unit tests (pytest)
│   ├── test_runner.py        # ritz0 --test driver
│   └── test/
│       └── test_issue_*.ritz # 33 regression tests (compiler matrix)
└── examples/
    └── tier{1..5}_*/*/
        ├── test/
        │   └── test_*.ritz   # ritzunit-style integration tests
        └── test.sh           # Shell-based tests (legacy / belt-and-braces)

projects/ritzunit/
├── src/                      # Test framework source
├── test/                     # Self-tests (27 passing)
└── examples/
    └── isolation_demo.ritz   # Fork-isolation demo (moves to test/ when
                              #   the native binary is the runner)
```

---

## What's next

See `TODO.md` for the broader plan. Testing-relevant items:

1. **Backfill tier 3 (coreutils 21-30)** — same template, ~5 tests
   each, mostly mechanical.
2. **Backfill tier 4 (apps 31-40)** — same.
3. **Backfill tier 5 async (41+)** — async tests are non-trivial; some
   may need new ritzlib helpers (timed waits, cooperative cancellation).
4. **Wire native ritzunit binary** — make ritzunit produce a real
   binary, change `build.py test` to invoke it. Captures the 90×
   speedup that's currently sitting on the floor.
5. **Move `isolation_demo.ritz` back to `test/`** once the native
   runner is in place.
6. **Implement `[[test(should_fail)]]`** to formalise expected-fail
   tests instead of relocating files.
7. **Implement `rzrz cmd_test`** so the native rzrz can drive the
   whole test suite (currently it's a stub that just prints "TODO").

---

*Last updated: 2026-04-26*
