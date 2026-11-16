# LARB v5 Review: build and test tooling, and fast iteration

**Reviewed:** 2026-11-16 · **Baseline:** review/4 (2026-10-25) · **Status:** NEEDS WORK

**Scope:** the same files as review/4 [tooling.md](../4/tooling.md) and [fast-iteration.md](../4/fast-iteration.md): `./rz`, `rz.toml`, `projects/ritz/{build,cache,packaging,cas}.py`, `projects/ritz/tools/`, `scripts/regression.sh`, the Makefiles, `.github/workflows/`, `.claude/skills/rz-iterate/run-gate.sh`.

**Metrics:** [metrics-tooling.md](metrics-tooling.md), produced with `ritz_metrics.py rz projects/ritz/{build,cache,packaging}.py projects/ritz/tools --lang py`. Run on a `git archive 587fab06` tree, the same command reproduces review/4's 33 files / 11,867 SLOC / 635 fns exactly, so the before and after numbers are comparable. `cas.py` is new and outside the review/4 path set; it adds 597 lines.

**Gate times:** taken from the 1,303 logs in `~/dev/ritz-lang/gate-logs/`. Wall time runs from `SLOT=n START` to the log's mtime, for passing runs (`EXIT=0`) only. CI times come from the GitHub Actions step timings of `main.yml` run 43768702453, which tested 6f245b93.

## Summary

Epic #1801 landed almost in full: all ten tickets, #1802 through #1811, are in the code, in commits dated Oct 25–27.
- **Gate time:** the local gate's median fell from 45 min (Oct 19–25) to 9 min (Oct 27–28).
- **CI:** `test-all` takes 2 m 13 s on CI, down from 23 m 31 s, and `main.yml` passed all 14 of its last completed runs (review/4: 15 of 15 failed).
- **Gate time is climbing again:** the ritz0 suite grew from 2,898 to 39,054 tests (13×) in three weeks. The gate median is 737 s on Nov 15, over the 12-minute target, and the CI bootstrap job is slower than at review/4 (20 m vs 13 m).
- **Consolidation (epic #1833) has barely started:** the four allowlists, the dead code in `rz`, the duplicate dependency resolvers, `packaging.py` and the two `ritz-lint` copies are all unchanged.
- **Growth:** `build.py` grew 31% and `compile_freestanding_binary` grew. The ritz0 fingerprint now exists twice.

Status is NEEDS WORK because the fast-iteration work is a success but the structural findings are untouched.

## Against review/4

### tooling.md

| id | title | r4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| F1 | Cache import scanner misses 30% of imports | Critical | FIXED | `cache.py:151`'s regex is gone. `BuildCache._scan_direct_imports` (`cache.py:514-533`) now asks ritz0's `ImportResolver` (`:535`) for imports (a8aa1052). The closure feeds the CAS key (`build.py:389,551`); covered by `tools/test_cache_import_closure.py`. The fixed scanner's old consumer, `needs_rebuild`, has since lost every caller: see new F2. | #1832 |
| F2 | Four allowlists, three formats, outcome logic ×3 | Major | OPEN | All four allowlists are still there: `rz.toml:64 [ci.known_failing.build]`, `scripts/regression-known-failures{,-ritz1}.txt`, `run_regression_matrix.py:49-97 EXPECTED_FAILURES`, and the markers. The outcome logic is still written three times: `rz:241 gate_outcome`, `run_regression_matrix.py:129`, and `regression.sh:358-395 is_known_failure/report_xpass`. | #1834 |
| F3 | `compile_binary` / `compile_freestanding_binary` diverging copies | Major | PARTLY | `compile_binary` shrank from 189 to 124 SLOC (CC 64→41) after `compile_modules` was extracted (`build.py:1594`). The freestanding copy grew from 243 to 279 SLOC (CC 64→74, depth 8→9; `build.py:2060`). Two of the four differences are closed: it now uses the CAS (bff76a1c) and reports every failure (`:2305`, #1286). It still writes no provenance, and its `clang -c` at `build.py:2265` still runs without the timeout and memory cap that `compile_ll_to_obj` (`:277`) applies. | #1835 |
| F4 | `build.py` god module; unbounded subprocesses | Major | REGRESSED | `build.py` grew from 2,914 lines / 1,958 SLOC / 64 fns to 3,714 / 2,568 / 105. Subprocess calls: 3 of 18 are bounded (`:290` via `communicate(timeout=)`, `:580`, `:2895`); review/4 counted 3 of 15. In `rz`, 0 of 13 have a timeout (review/4: 0 of 12). | #1835 |
| F5 | ~1,000 dead lines in `rz` | Major | OPEN | Each of these still appears once in `rz`, at its own definition, so nothing calls it: `run_pipeline` (`rz:1412`, still the only `shell=True`), `compile_with_ritz1/ritz0` (`:896,922`), `link_llvm_ir` (`:979`). `cmd_ci_plan/run/generate` (`:1557,1603,1790`) are still in place, and no script or workflow calls `rz ci`. `cmd_compare` is still there (`:1089`). `rz` itself grew from 1,567 to 1,957 lines. | #1836 |
| F6 | Two dependency resolvers that disagree | Major | OPEN | `rz:186 collect_dependency_paths` and `rz:1207 get_project_dependencies` both still recurse only when `dep_path.parent == PROJECTS_DIR` (`:207,:1220`), so nested packages are still missed. `build.py:1116 get_transitive_dependencies` is a third resolver. | #1835 |
| F7 | `packaging.py` used only by its tests | Major | OPEN | Unchanged byte for byte: 902 lines, no commits since 587fab06. It is reached only from `build.py:3520-3552` (install/uninstall/list/cache/lock) and `ritz0/test_packaging.py`. The repo still has no lockfile or vendor directory, and the module name still shadows PyPI's `packaging`. | #1836 |
| F8 | Config keys read by nothing; spec ahead of code | Major | PARTLY | Now read: `[build] parallel/max_jobs` (`rz:436-439`, cc4df840), `[[lib]]` (24b68f29), `[[test]]` (3dce8591, 97b9b75a). Still read by nothing: `[build] cache`, `[agents]` (`rz.toml:41`), `[dev-dependencies]` (spec `RITZ_TOML_SPEC.md:138`), `[scripts]`, `[features]`. Searching `rz` and `build.py` for these keys finds no reader. | #1837 |
| F9 | CI | Major | PARTLY | Fixed: the gate now runs `--job build-all --job bootstrap` (`run-gate.sh:133`, 475ba311), and the train gate also tests the workspace packages it touches (935a415f). `main.yml` passed its last 14 completed runs. Still open: `pr.yml` is still present and last ran on 2026-09-04. `lint-all` is `continue-on-error` and exits 0 when `claude` is missing (`main.yml:293,306`); it is now documented as advisory. Setup steps are still repeated in each job (`main.yml:61,122,166,298`). | #1838 |
| F10 | Legacy ritz1 build paths | Major | PARTLY | `ritz1/bootstrap_ritzlib/` went from 31 files / 11,685 lines to 28 files / 9,792 lines, and mechanical commits still edit it (cc4d6a8e, 87a64c11). `ritz1/compile.sh`, `Makefile.working`, `verify_integration.sh` and `bootstrap_env` are still tracked. | #1268 |
| F11 | `regression.sh` Stages 3/4 copy-paste; shell bugs | Minor | PARTLY | Stages 3 and 4 now share `differential_worker` (`regression.sh:1492`) and `run_differential` (`:1551`). The script grew from 1,330 to 1,863 lines. The SC2155 and word-splitting part is unverified: shellcheck is not installed here. | #1838 |
| F12 | Compiler fingerprints computed in two places | Minor | REGRESSED | There are now two whole-tree ritz0 walks, each with its own exclude constants: `cache.py:87-88,310-336` and `ritz0/emitter/fn_cache.py:337-356` (d90b43e8, whose comment says it "covers the same files"). The third, `module_interface.py:103-123`, is a narrower parser-only hash and is justified (see Not findings). | #1807 |
| F14 | `ritz-lint` exists twice | Minor | OPEN | `projects/ritz/tools/ritz-lint/ritz_lint.py` and `projects/larb/tools/ritz-lint/ritz_lint.py` still differ by 92 diff lines, the same count as review/4. | #1838 |
| F16 | `scripts/test_ritz1.sh` passes over an empty glob | Minor | FIXED | The file is deleted. | #1268 |
| F18 | `parser_gen.py.orig` tracked | Minor | FIXED | Gone; `git ls-files '*.orig'` returns nothing. | #1822 |
| — | Dead files (ELF binaries, callgrind, status txt) | — | PARTLY | Removed: `hello_test`, `ritzgen_test`, `ritz1_bin`, `ritz0/cat_ll`, the `callgrind.out.*` files and `scripts/test_tier1.sh` / `bootstrap_test.sh` (7b14feb3 and others). Still tracked: `ritz1/ritz1_new` (a static ELF), `out/test_json`, `BOOTSTRAP_SESSION_SUMMARY.txt`, `FINAL_BOOTSTRAP_STATUS.txt`, `scripts/build_ritz1.sh`. | #1268 |

Review/4's ticket table also cites F13; review/4 never describes it, so there is no row for it. There are no F15 or F17.

### fast-iteration.md (epic #1801)

| id | title | r4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| G1 | Gate quick wins: Stage 4 rebuild, `-j`, fail-fast, step timings | Design (p90) | FIXED | Stage 4 builds with `make -C ritz1 -j… bootstrap` and no `BUILD_DIR` override or `2>/dev/null` (`regression.sh:1628-1644`). `--fail-fast` is in the gate command (`run-gate.sh:133`). Every step logs `[step] START/END … Ns rc=` (c474befd). | #1802 |
| G2 | Smoke tier ≤ 2 min, first in gate and CI | Design | FIXED | `make smoke` (`tools/smoke.py`, c139c06c) runs first in `run-gate.sh:133` and in `main.yml` bootstrap. Over 290 gates (Nov 12–15) it takes 44.9 s min, 57.7 s p50, 65.5 s p90, 97.5 s max. On CI it takes 89 s. Its `pytest -m smoke` step selects 1,021 of 39,126 tests and took 40.6 s of its 45 s budget on 6f245b93. | #1803 |
| G3 | pytest parallel, one ritz1 build | Design | PARTLY | xdist with `--dist loadgroup` is in place (`Makefile:149`), conftest builds ritz1 once, and there are no `_build_ritz1` copies left (review/4 counted 42). But pytest takes 372 s p50 on Nov 15, over the ≤ 300 s target, and is growing (new F1). | #1804 |
| G4 | Cut duplicate coverage; ≥ 50 % fewer ritz0 subprocesses | Design | PARTLY | Tests now compile in-process (a0b284bb), and `spawn_guard` (`ritz0/conftest.py:107`) fails any test that spawns a process without the `integration` mark. Only 1 of 241 spawning files lacks the string "integration" (review/4: 36 unmarked). However, the number of test files that spawn grew from 106 to 241. The ≥ 50 % reduction is not measured anywhere. | #1805 |
| G5 | regression.sh parallel, Stage 1 cache, server budget | Design | FIXED | `REGRESSION_JOBS` defaults to 8 (`regression.sh:112`), there is a Stage 1 baseline cache (`:114`, `stage1_cacheable` `:1203`), and a watchdog (`:622`). On the 6f245b93 gate, the bootstrap chain took 19.5 s and the differential 47.9 s, inside the ≤ 2 min target. | #1806 |
| G6 | ritz1 fast path checks import hashes; sigs out of tree | Design (correctness) | FIXED | The sig carries `import_hashes` (`ritz1/src/fn_cache.ritz:14,49,400`). Sigs live under `$RITZ_CACHE_DIR/<compiler>/` (`:35,285`; `ritz0/emitter/fn_cache.py:307-319`). No `*.ritz.sig` file is tracked. The dead `lookup_fn_ir`/`cache_fn_ir` are deleted (`:53`). This also closes #1280. | #1807 |
| G7 | Content-addressed artifact store | Design | FIXED | `cas.py`: default store `~/.cache/ritz/cas` (`:7`), writes with `os.replace` (`:297,314`), `gc` (`:451`), single-flight (99948037), gate-level stats. Gate 6f245b93 reported `processes=2598 hits=8200 misses=1050 failed=30; interfaces hits=26121 misses=925`. The §6.6 targets "≤ 3 min re-run" and "second worktree misses = 0" are not measured in any log. | #1808 |
| G8 | `rz build/test --all` parallel | Design | FIXED | One bounded `-j`/`max_jobs` pool (`rz:426`, `test_projects_parallel` `rz:591`, cc4df840). CI `test-all` takes 2 m 13 s, against 23 m 31 s at review/4 and a ≤ 6 min target. | #1809 |
| G9 | Interface files / separate compilation | Design | FIXED | `ritz0/module_interface.py` (495 lines) stores interfaces (bodies stripped except generic and async ones) in the CAS (e98e5a2c, 7b565f56). In gate 6f245b93, 26,121 interface loads hit and 925 missed. `ImportResolver(use_cache=False)` remains (`ritz0.py:216`) for the separate `.ritz-meta` path, which has no production caller. | #1810 |
| G10 | Host build budget shared by rooms and gates | Design | FIXED | `ritz-gate.slice` runs at CPUWeight 100 and `ritz-rooms.slice` at 20 under a memory cap (`run-gate.sh:31-36`, f9263a53). Per-host `host.env` sets the gate slots (62c9082a), with a FIFO slot queue (5c2b935b). The 1.3× target is not directly measurable: the Nov 15 p50 (737 s) is 1.40× the fastest pass in the sample (525 s). | #1811 |
| §5 | Full local gate ≤ 12 min uncontended | Target | PARTLY | Met from Oct 27 to Nov 5 (p50 540–739 s). Missed on Nov 6–12 (1,019–2,489 s) while the test count grew. Back under target after 86a44567 (628 s on Nov 13). Now 737 s, over target and rising. | #1801 |

## Metrics delta

| metric | review/4 | now |
|---|---|---|
| files / SLOC / fns (same paths) | 33 / 11,867 / 635 | 67 / 19,755 / 1,428 |
| non-test SLOC / test SLOC | 8,829 / 3,038 | 10,692 / 9,063 |
| `build.py` lines / SLOC / fns | 2,914 / 1,958 / 64 | 3,714 / 2,568 / 105 |
| `rz` lines / SLOC | 1,567 / 1,190 | 1,957 / 1,482 |
| `cache.py` lines | 855 | 1,063 (plus `cas.py` 597) |
| `regression.sh` lines | 1,330 | 1,863 |
| fns > 100 SLOC / > 300 SLOC | 9 / 1 | 11 / 1 |
| CC > 20 / CC > 50 | 14 / 2 | 21 / 2 |
| depth ≥ 6 | 28 | 108 (mostly nested `with`/`patch` in the new `tools/test_*`) |
| worst fn | `_emit_lexer` 375 SLOC (deleted with `ritzgen_py/generator.py`) | `smoke_stack.py:913 suite_stack` 359 SLOC, CC 110, depth 11 |
| worst duplicate cluster | 25× (`generator.py`) | 23× `self._emit('')` (`ritz_generator.py`) |
| **local gate wall, p50 of passing runs** | **45.5 min** (2,730 s, Oct 19–25); 46 min Oct 24–26 | **12.3 min** (737 s, Nov 15); 11.8 min Nov 13–15 (n=271, p90 13.1 min, min 8.75 min) |
| local ritz0 pytest step / tests | 1,460 s / 2,646 (log 1520-28ff8b03) | 389 s / 39,054 (train-6f245b933a13) |
| local tools-unit / tests | 75 s / 276 | 63 s / 837 (xdist, 62464551) |
| smoke tier | did not exist | 57.7 s p50 local; 89 s CI |
| earliest "fully broken" signal | ~26 min | ≤ 98 s (smoke max) |
| CI bootstrap job | 13 m 10 s | **20 m 02 s** (ritz0 unit tests 6 m 35 s → 12 m 42 s) |
| CI `test-all` | 23 m 31 s | 2 m 13 s |
| `main.yml` on main | 15 of 15 failed | 14 of 14 completed passed |

## New findings

### F1. Gate time is climbing back, driven by test count [architecture] — Major
- **Evidence:** daily gate p50 by date (gate-logs):
  - Oct 28: 540 s
  - Nov 4: 724 s
  - Nov 8: 2,489 s
  - Nov 13: 628 s (after 86a44567, "70% less test time")
  - Nov 14: 686 s
  - Nov 15: 737 s
- **Where the time goes:** ritz0 pytest went from 2,898 tests / 134 s (Oct 28) to 39,054 tests / 372 s (Nov 15). That is 53 % of a 737 s gate.
- **Test count by file:** eight parametrised-matrix files hold 9,246 tests. The largest are `test_array_store_rule.py` (1,679), `test_ritz1_array_pointer_index.py` (1,669) and `test_member_through_levels.py` (1,206).
- **CI:** the CI bootstrap job is now 52 % slower than at review/4.
- **Impact:** the ≤ 12 min target is missed again. The trend is about +50 s/day over Nov 13–15, and nothing would stop a repeat of Nov 6–8, when the gate passed 40 min.
- **Fix direction:**
  - a time budget per test file, checked in `tools-unit` (fail when a file exceeds N s or the suite exceeds a cap);
  - collapse combinatorial matrices into one table-driven test per compiler that compiles one program holding all cases;
  - publish pytest `--durations` in every gate log.
- **Ticket:** #3453.

### F2. Most of `BuildCache`'s artifact cache is dead code with green tests [cleanup] — Major
- **Evidence:** `cache.py:710-977` (`_get_safe_cache_name`, `get_cached_{ll,bc,obj}{,_path}`, `needs_rebuild`, `update_cache`, `has_valid_bc`, `update_{bc,obj}_cache`) has no caller outside `cache.py` and tests: `ritz0/test_build.py`, `tools/test_cache_import_closure.py`, `tools/test_cache_concurrent_writes.py`.
- **Impact:** all compiled artifacts now go through `cas.ArtifactStore` (`build.py:340` comment). Production uses only the import-closure half of `BuildCache` (`set_import_context`, `get_transitive_dependencies`, the compiler hash).
- **Fix direction:** reduce `cache.py` to an `ImportClosure` (closure plus imports DB) and the fingerprint. Delete about 270 lines and the tests that assert the dead path.
- **Ticket:** #3454.

### F3. `smoke_stack.py` is one 1,599-line file with a 359-SLOC suite [architecture] — Major
- **Evidence:** `tools/smoke_stack.py:913 suite_stack` measures 359 SLOC, CC 110, depth 11; `:639 suite_mausoleum` measures 180 SLOC, CC 43. The file is 1,599 lines / 1,263 SLOC, over the 1,500-line Major threshold.
- **Why Major, not Critical:** the function numbers count about 25 nested closures (`health`, `create`, `edit_4x`, `wrk_index`, `respawns_killed_worker` …). Each closure is short, but they share `up`/`down`/port state through captured locals.
- **Fix direction:** one module per suite under `tools/smoke_stack/`, with a `StackCtx` dataclass holding the processes and ports, and each check as a module-level fn taking the ctx.
- **Ticket:** #3455.

### F4. Partial breakage surfaces only 9–11 minutes into the gate [architecture] — Minor
- **Evidence:** smoke passed in every one of the last 290 gates (Nov 12–15) but caught none of the 18 failures among them. 10 of the 18 failed in `ritz0 unit tests`, between 550 and 674 s of gate wall time. The other 8 failed in build-all, tools-unit or the harness tests, at 105–281 s.
- **Fix direction:** order the pytest step so the most likely failures run first, for example by running the tests the diff touches first (`pytest --lf`-style, or the train's touched-file set), with `--maxfail`.
- **Ticket:** #3456.

## Not findings
- **`module_interface.py:103` hashes a hand-picked file list** (`tokens.py`, `lexer.py`, `parser.py`, `ritz_ast.py`, itself). An interface is parser output, so the narrow list is correct. It is not a third copy of the codegen fingerprint.
- **The gate wipes `ritz1/build` and `.regression` on every run** (`run-gate.sh:133`). This is deliberate cold-build coverage. The ritzlib objects come from the CAS, so the cost is the 19.7 s smoke ritz1 build.
- **`lint-all` exits 0** because it needs an authenticated `claude` CLI. It is documented as advisory (`main.yml:285-290`). It still belongs to F9 above, as a job that can never fail.
- **`rzrz` shells out to `./rz`** (a7625437). This matches review/4's long-term note: port the orchestration only after the Python has been consolidated.
