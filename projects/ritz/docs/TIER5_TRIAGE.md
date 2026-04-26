# Tier 5 backfill triage (2026-04-26 — UPDATED)

**Inventory**: 36 packages under `examples/tier5_async/`, 9 already tested
(66_for_loops through 74_autodrop), **27 missing**.

## Update after first backfill pass

The original triage identified 22/27 as "tractable with existing testlib
template" — that turned out to be optimistic.  Most packages had
**pre-existing build failures** that masked the test-writing scope.

After mass-migrating legacy `&x` → `@x` across 29 src files in tier 5,
**9 newly built cleanly**.  Tests written and passing for all 9
(commit `<TBD>`).

| Built + tested now | Failure mode masking the rest |
|---|---|
| 41_calc (10 tests) | StrView/i8* if-emit (6 pkgs: 42-46, 48) |
| 56_async_runtime (1) | async Future/i64 mismatch (3 pkgs: 53, 54, 55) |
| 57_fn_ptr (1) | uring API drift (1 pkg: 52_uring) |
| 58_closures (1) | reserved keyword "HEAP" (1 pkg: 47_lisp) |
| 61_true_async (1) | StrView/i8* (1 pkg: 49_ritzgen) |
| 62_async_compiler (1) | StrView/i8* (1 pkg: 59_async_net) |
| 63_executor (1) | server / no exit (3 pkgs: 50_http, 51_loadtest, 60_echo_server) |
| 64_async_io (1) | unstructured (1 pkg: 51_iovec) |
| 65_async_main (1) | doc-only (1 pkg: 75_async_reference) |

**Cumulative tier 5 coverage: 9 (previously) + 9 (this pass) = 18/36.**

The remaining 18 packages need:
- **6 with StrView/i8* fix** (same blocker as xargs/watch — `docs/XARGS_WATCH_BLOCKER.md`)
  → 42_json, 43_toml, 44_csv, 45_regex, 46_markdown, 48_ritzfmt, 49_ritzgen, 59_async_net
- **3 with async runtime fix** — 53_async, 54_async_fs, 55_async_state_machine
- **1 with uring API alignment** — 52_uring
- **1 with parser fix** — 47_lisp (`HEAP` is now a reserved keyword?)
- **5 special cases** (servers / fragments / docs) — out of scope for `[[test]]`

**Result**: 22 of those 27 are tractable with the existing
`ritzlib.testlib` template; 5 are special cases worth deferring or
documenting separately.

## Tractable (22 packages)

### Easy A — argv/stdin → stdout pattern (9 pkgs, ~30 min/pkg)

These are text-format parsers/formatters with deterministic CLI shape.
Each gets 3-5 `[[test]]` functions using `exec_capture`.

| Pkg | CLI | Notes |
|---|---|---|
| `41_calc` | `./calc 'expr'` | Arithmetic expression evaluator |
| `42_json` | stdin → stdout | JSON parser; existing test.sh has 8+ scenarios |
| `43_toml` | stdin → stdout | TOML parser |
| `44_csv` | stdin → stdout | CSV parser |
| `45_regex` | argv pattern + stdin | Regex matcher |
| `46_markdown` | stdin → stdout | Markdown to HTML |
| `47_lisp` | stdin → stdout | Lisp evaluator |
| `48_ritzfmt` | stdin → stdout | Ritz source formatter |
| `49_ritzgen` | grammar file → generated parser | Already tested via test.sh |

### Easy B — async self-test pattern (13 pkgs, ~5 min/pkg)

Each binary's `main()` runs internal `test_*` functions and exits 0 if
all pass.  The `[[test]]` version is one wrapper that fork+execs the
binary and asserts exit 0:

```ritz
[[test]]
fn test_async_self() -> i32
    var argv: [2]*u8
    argv[0] = c"./async_test"
    argv[1] = null
    var out: [4096]u8
    var n: i64 = 0
    let exit_code: i32 = exec_capture(c"./async_test", @argv[0], null, null, 0, @out[0], 4096, @n)
    assert exit_code == 0, "async_test self-tests should exit 0"
    0
```

| Pkg | Internal test count |
|---|---|
| `52_uring` | 1 binary, runs uring tests |
| `53_async` | 4 (test_async_no_await, …) |
| `54_async_fs` | varies |
| `55_async_state_machine` | varies |
| `56_async_runtime` | varies |
| `57_fn_ptr` | varies |
| `58_closures` | varies |
| `59_async_net` | varies |
| `61_true_async` | varies |
| `62_async_compiler` | varies |
| `63_executor` | varies |
| `64_async_io` | varies |
| `65_async_main` | varies |

## Skip / defer (5 packages)

| Pkg | Reason |
|---|---|
| `50_http` | TCP server — never exits naturally.  Test would need to spawn it, send a request, kill it.  Doable but complex. |
| `51_iovec` | No `ritz.toml` — unstructured fragment (just `main.ritz` + `test_simple.ritz` at top level).  Restructure first. |
| `51_loadtest` | HTTP load tester — needs a server target.  Could pair with 50_http but too entangled for templated test. |
| `60_echo_server` | TCP echo server — same shape as 50_http. |
| `75_async_reference` | Reference example for documentation, not a tested-feature. |

## Recommended order

If continuing the backfill:

1. **Easy B first** (13 pkgs × 5 min ≈ 1 h).  Most mechanical; each is
   essentially the same template.  Covers all the actually-async
   examples.
2. **Easy A second** (9 pkgs × 30 min ≈ 4-5 h).  Each parser needs
   carefully-chosen scenarios from its `test.sh`.
3. **Skip-pile** as a separate, scoped session.  Server-style examples
   need a "spawn-then-kill" helper added to `ritzlib.testlib`, plus
   ports / lifecycle plumbing.  Defer.

## Cumulative coverage projection

| State | Tier 5 covered | Total tested |
|---|---|---|
| Now | 9/36 | 9 |
| After Easy B | 22/36 | 22 |
| After Easy A | 31/36 | 31 |
| After server cases | 35/36 | 35 (75 doesn't apply) |
