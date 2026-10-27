# Wiring native ritzunit as build.py's test driver

**Status (2026-04-26)**: ritzunit binary now builds (was `test_only=true`,
now ships a `[[bin]]` target).  Full integration with `build.py test`
deferred — needs a per-package compile-and-link mode that doesn't exist
yet.  This doc captures the plan.

## Why this matters

`ritz0 --test` recompiles everything for each test file (`run_test_file`
in `ritz0/test_runner.py` loops one file at a time).  ritzunit's own
self-tests (27 tests across 6 files) currently take **33 s** under
`make test ../ritzunit`.  ritzunit's README claims 90× speedup via ELF
symbol-table discovery; in practice we'd expect those 27 tests to run
in well under 1 s once wired.

For tier 1-4 backfill (28 test files, currently ~30 s each in matrix
runs), the win is substantial: ~14 min → ~10 s for `make test --all`.

## What landed (2026-04-26)

### `projects/ritzunit/ritz.toml`

```toml
sources = ["src"]

[[bin]]
name = "ritzunit"
entry = "runner::main"

[[lib]]
name = "ritzunit"

[build]
target = "x86_64-linux"
# test_only=true removed — both [[bin]] and [[lib]] are produced now.

[dependencies]
# ritzlib has no nested src/, so override the default sources=["src"]
# to point at the dep root.
ritzlib = { path = "../ritz/ritzlib", sources = ["."] }
```

### `projects/ritzunit/src/{json_reporter,junit_reporter,reporter,types}.ritz`

Mechanical `&x` → `@x` migration (13 sites total).  Required because
the binary build path goes through current ritz0 which rejects legacy
`&x`.  Test path was using a different ritz0 mode that grandfathered
some of those — now uniform.

### Verification

* `RITZ_PATH=$(pwd) python3 build.py build ../ritzunit` → ✓ ELF binary
* `./build/debug/ritzunit --help` → prints help (so argv parsing works)
* `./build/debug/ritzunit` → "No tests found." (correct — no user tests
  linked into this stand-alone binary)
* `RITZ_PATH=$(pwd) python3 build.py test ../ritzunit` → 27/27 still
  pass via the legacy `ritz0 --test` path.

## What does NOT work yet

The ritzunit binary self-discovers tests from `/proc/self/exe`'s ELF
symbol table.  That means ritzunit **must be linked into a binary that
also contains the user's `[[test]]` functions** — running the standalone
ritzunit binary against an external test file would do nothing because
the test symbols aren't in `/proc/self/exe`.

So the integration needs a per-test-target build:

```
package/
├── src/main.ritz       # binary code under test
├── test/test_*.ritz    # [[test]] functions
└── (output) build/debug/<pkg>-tests   # links: src + test + ritzunit lib
```

Today `build.py test` doesn't have this mode.  It runs:

```python
subprocess.run([RITZ0, "--test", *test_files], cwd=pkg_dir, ...)
```

…which produces N temporary harness binaries (one per test file).

## What needs to change

In `build.py:run_tests` (around line 1466), when ritzunit is available
and the package has `[[test]]` functions:

1. Compile **all** of (`src/**/*.ritz` + `test/test_*.ritz` +
   `ritzunit/src/runner.ritz`) into one binary, e.g.
   `build/debug/<pkg>-tests`.
2. Run that binary; ritzunit's runner self-discovers the `[[test]]`
   functions and exec'd them with fork isolation.
3. Parse exit code (0 = pass, non-zero = fail with stderr).

### Concrete sketch

```python
# In build.py (new helper):
def run_tests_via_ritzunit(pkg_dir, ritzunit_path, ...):
    # Build the test binary once.
    test_bin = compile_test_binary(
        pkg_src=pkg_dir/"src",
        test_dir=pkg_dir/"test",
        ritzunit_lib=ritzunit_path/"src",
        out=pkg_dir/"build"/"debug"/f"{pkg_name}-tests",
    )
    if test_bin is None:
        return False
    # Run it; ritzunit's runner main does the discovery + fork loop.
    result = subprocess.run([str(test_bin)], capture_output=True, text=True)
    return result.returncode == 0
```

The trick is `compile_test_binary` — needs to:
* Treat the test files' `main()` as absent (ritzunit's runner.ritz
  provides main).
* Resolve `[[test]]` annotations the same way `ritz0 --test` does (i.e.
  parser already handles them).
* Link ritzunit's runner symbols into the same binary so
  `discover_tests()` can find user tests via `/proc/self/exe`.

### Open questions

1. **How does the test binary's `main()` get wired to ritzunit's
   `runner::main`?**  Either user test files don't have a main (ritzunit
   provides it) or build.py has to skip the user's main.  Probably
   ritzunit-as-lib + user-tests-and-pkg-src compile to .o files, then
   the linker uses ritzunit's `_start` → `runner::main`.

2. **Does `[[test]] fn x() -> i32` translate to an ELF symbol with the
   right shape?**  Need to verify ritz0's emitter exports them with the
   expected linkage and that ritzunit's `discover_tests` recognises the
   naming convention (probably `test_*` prefix per its README).

3. **What about packages that already have a `main()` (e.g. tier 3
   coreutils)?**  Their `src/main.ritz` defines `main(argc, argv)` — but
   for the test binary we want ritzunit's main, not the package's.  May
   need to compile test binary with `--no-main` or a flag to suppress
   the package's main.  Or build the test binary purely from
   `test/*.ritz` without `src/main.ritz` (just link `src/*.ritz` minus
   main as object files, which the [[test]] tests can call into).

## Effort estimate

* Read ritzunit's `discover_tests` + emitter behavior to confirm the
  symbol shape — 30 min
* Add `compile_test_binary` to build.py with the main-suppression
  logic — 1-2 h
* Wire `run_tests_via_ritzunit` as fallback when the package has tests
  AND ritzunit binary exists — 30 min
* Validate on tier 1-4 (28 packages) end-to-end — 30 min

Total: **~3-4 hours** focused work.

## Why I stopped here

Today's session ran a long thread of code-review fixes (testlib extract,
StrView migrations across tier 3+4, mtime tests, exit-code tightening,
the StrView/cache-trap red-herring, etc.).  Wiring the native runner
properly is a separate, focused job that benefits from a fresh session
with the full context above.  The intermediate state is useful: the
ritzunit binary exists, builds clean, and the wiring plan is ready to
execute.

## Files changed in this session for ritzunit binary work

* `projects/ritzunit/ritz.toml` — `sources = ["src"]`, new `[[bin]]`
  target, dropped `test_only`, fixed `[dependencies]` to override
  default `sources` for ritzlib.
* `projects/ritzunit/src/{json_reporter,junit_reporter,reporter,types}.ritz`
  — `&x → @x`.

No regressions: ritzunit's 27 self-tests still pass via the legacy
`ritz0 --test` path.
