# LARB 2026-10 — Fast iteration: smoke tier, faster gate, once-only builds

Status: design, measured 2026-10-25 without running a build (read-only room).
Owner ticket: AGAST #1800 (deliverable C). Implementation tickets: epic #1801, children #1802–#1811 (§7).

Every ritz room's merge gate (`.claude/skills/rz-iterate/run-gate.sh` →
`make -C projects/ritz ci-local`) currently takes **39–54 min**. A room that
breaks the compiler outright finds out after ~26 min. This document measures
where the time goes, explains why almost nothing is reused, and specifies a
smoke tier, a faster full gate, and a content-addressed artifact cache.

---

## 1. Baselines (measured)

Sources: 30 gate logs in `~/dev/ritz-lang/gate-logs/` (Oct 14–25), GitHub
Actions REST step timings and job logs for `main.yml` run 40155556007
(commit 28ff8b0, the base of this branch).

### 1.1 Local gate (`ci-local`, bootstrap job), log `1520-28ff8b03e30e.log`

| Step | Local (contended) | CI runner (4 vCPU) |
|---|---|---|
| Documentation examples compile | ~15 s | 11 s |
| `tools-unit` (276 pure-Python tests) | 75 s | 31 s |
| Regression harness self-tests | ~10 s | 11 s |
| **ritz0 pytest** (2646 tests, serial) | **24 m 20 s** | **6 m 35 s** |
| `matrix-full` (bootstrap + 588 units × 3) | ~17 m together | 40 s |
| `regression.sh` (stages 1–5) | | 4 m 30 s (S1 90 s, S3 58 s, S4 123 s) |
| **Total** | **44 m 45 s** | **13 m 10 s** |

### 1.2 Trend — the gate doubled in a week

| Gate log | Date | Wall | pytest | tests | tools-unit (same 274–276 tests) |
|---|---|---|---|---|---|
| 1745-33fb3b65 | Oct 18 | 21 m | 692 s | 2363 | 45 s |
| 1754-fdf56c87 | Oct 19 | 28 m | 914 s | 2530 | 61 s |
| 1789-e2e067ef | Oct 24 | 36 m | 1165 s | 2536 | 77 s |
| 1791-e4e33263 | Oct 24 | 54 m | 1955 s | 2618 | 107 s |
| 1520-28ff8b03 | Oct 25 | 44 m | 1460 s | 2646 | 75 s |

The suite grew 12 %. pytest time grew 110–180 %. `tools-unit` — identical,
pure-Python, compiles nothing — slowed 1.7–2.8×. **Most of the growth is host
contention**: the gate holds the only gate slot (`RZ_GATE_SLOTS=1`) but task
rooms keep building on the same 12-core / 15 GB WSL VM (load avg ≈ 8 at
measurement). The gate slot protects gates from gates, not from builds.

### 1.3 Workspace sweep (`main.yml` `test-all`, `rz test --all`)

23 m 31 s; 196 `.ritz` test files run serially; median **5.3 s per file**, p90
9.0 s, regardless of how many tests the file holds. That flat floor is the cost
of recompiling the file's whole ritzlib closure every time (§3).

### 1.4 What nobody measures

`tools/ci_local.py` prints step banners without timestamps, and neither gate
log nor `regression.sh` records per-stage time. Every number above was
reconstructed. Step timing is the first thing to add (ticket G1).

---

## 2. Redundant work in one gate

| Work | Times per gate | Where |
|---|---|---|
| ritz1 built by ritz0 (23 ritz1 + 16 ritzlib modules, link) | **2 full** + 2 no-op checks | pytest fixtures (gate wiped `ritz1/build`); `regression.sh` Stage 4 |
| ritz1_selfhosted (23 self-compiles + link) | **2** | `matrix-full --rebuild`; Stage 4 |
| ritzlib compiled by ritz0 | 4 independent stores | `ritz1/build`, matrix tmpdir, `.regression/`, `.ritz-cache` |
| Each of 88 examples compiled + run | 3, all serial | Stages 1, 3, 4 |
| `list_deps.py` full-closure parse | 375 (125 needed) | `run_regression_matrix.py:581` |
| ritz0 "oracle" subprocess runs in pytest | ~600 | 69 `test_*oracle` fns in 60 files |
| `make -C ritz1 ritz1` from pytest fixtures | ~80 modules | 42 copy-pasted `_build_ritz1()` + 32 importers |
| Fixed 5 s kill timeouts on never-exiting servers | ~13 | Stages 1/3/4 |

**The single worst line: `scripts/regression.sh:1050`**

```bash
if make -s bootstrap BUILD_DIR="$BUILD_DIR" 2>/dev/null; then
```

A command-line `BUILD_DIR` overrides `ritz1/Makefile:56` (`BUILD_DIR = build`)
for objects and `.d` files (only `RITZ1`/`RITZ1_SELFHOSTED` are hard-coded to
`build/`, lines 16–17). Stage 4 therefore rebuilds ritz1 **and** ritz1_selfhosted
from nothing into an empty `.regression/`, relinks `build/ritz1` mid-run, and
sends the build's stderr to `/dev/null`. The comment at :1052 ("The bootstrap
target ignores BUILD_DIR") is false. Cost: 55 s on CI, ~3–4 min locally.

---

## 3. Why nothing is reused — the five cache layers

| Layer | What / key | Why it gives no cross-run reuse |
|---|---|---|
| `<src>.ritz.sig` (ritz0) — `ritz0/emitter/fn_cache.py:244-291` | per-fn IR + source/import hashes, next to the source | File-level skip needs the output `.ll` to already exist at the requested path (`ritz0.py:107-116`); build.py and test_runner always compile into a fresh `mkdtemp` (`build.py:1387`, `test_runner.py:727`), so it never fires. Per-fn reuse only skips body emission — lex/parse/resolve/check/monomorph still run. |
| `<src>.ritz.sig` (ritz1) — `ritz1/src/fn_cache.ritz:827-880` | whole-module IR, FNV source hash + compiler fingerprint | Works across output paths (splice path b) — the only reuse that exists. But **the same file is rewritten by ritz0, ritz1 and ritz1_selfhosted** with incompatible schemas, so it is invalidated at every compiler boundary (≥4×/gate; #1280). Per-fn `lookup_fn_ir`/`cache_fn_ir` (`:886`, `:901`) have **no callers**. **Correctness:** the fast path never checks import hashes — `fn_cache.ritz` contains no `import_hash` at all — so a module whose imported struct changed can be served stale IR (same class as #1659/#1674). |
| `cache.py` `BuildCache` — `.ritz-cache[-ritz1[_selfhosted]]` | per-module `.ll/.bc/.o`; key = SHA-256 of source + transitive import sources; compiler fingerprint checked **wholesale** | Only `build.py compile_binary` uses it. Any ritz0/build.py edit or ritz1 relink **wipes the whole store** (`cache.py:446-486`). `build.py clean` wipes it; `rz compare` calls clean before each of 89 examples (`rz:686-691`). Per worktree only; no CI cache. `deps.json` is last-writer-wins (`cache.py:651-683`) — unsafe under parallelism. Flags/target not in key (`.o` is always `-O2`). |
| ritz0 import resolution — `ritz0.py:153` | — | `ImportResolver(..., use_cache=False)` hard-coded ("the cache creates stub functions without bodies, incompatible with our merged-module architecture"). Every ritz0 invocation lexes, parses and checks its **entire** transitive closure. `MetadataCache`/`.ritz-meta` has no production caller; `import_resolver.py:830-853`'s "eliminates re-parsing all 34+ ritzlib modules" comment is dead. |
| Test paths — `ritz0/test_runner.py:705-815`, `run_regression_matrix.py:447-468`, `ritz1/Makefile` | in-memory `ll_cache` per test file; matrix tmpdir per run; make mtime | `build.py test` builds the package through BuildCache, then each test file launches `ritz0 --test`, which re-compiles **every dependency `.ll` again** (one ritz0 subprocess per dep, `:428`) and hands clang `.ll` text (`:498`), so ritzlib is re-lowered per test file. BuildCache is never consulted. `rz.toml [build] cache/parallel/max_jobs` are read by nothing. `ritz1/bootstrap_ritzlib/` is unreferenced. |

Net: in a `rz test --all` sweep, ritzlib modules are compiled on the order of
**2,400–4,700 times** (237 test files × closure of 10–20 modules), and
`ritzlib/sys.ritz` is parsed several thousand times.

---

## 4. Design (a) — smoke tier: "fully broken" in ≤ 2 min

`make -C projects/ritz smoke`, run **first** by `run-gate.sh` and as the first
step of `main.yml`'s bootstrap job; the gate stops if it fails.

| # | Check | Catches | Budget (uncontended) |
|---|---|---|---|
| 1 | `check-no-s-strings`, `regen-check` | generator drift, banned syntax | 5 s |
| 2 | ritz0 in-process pytest subset (`-m smoke`, ~750 tests: parser, lexer, const_eval, symbol_table, type_checker, move_checker, monomorph, metadata, export_map, attrs, packaging, struct_layout, fn_cache, non-integration `test_build`) | broken ritz0 front end | 45 s |
| 3 | `make -j -C ritz1 ritz1` (incremental; cold ≤ 30 s at `-j`) | ritz1 does not build | 30 s |
| 4 | Canary matrix: `run_regression_matrix.py --compiler ritz0,ritz1 --tests '<~8 canary files>'` (hello/print, ritzlib strview+gvec, generics, structs, match, async-free) | ritz1 builds but compiles nothing / miscompiles basics | 20 s |
| 5 | ritz1 self-compiles one module (`tokens_gen.ritz`) and `clang -c` accepts it | self-hosting totally broken | 10 s |

Budget ≤ 120 s cold, ≤ 60 s warm. The canary list is a checked-in file, and
a self-test asserts each canary is still discovered (same "discovered, not
listed, with a floor" rule as #1371).

---

## 5. Design (b) — a faster full gate

**Order by cost and failure likelihood, and stop at the first failure.** Today
`ci_local.py:178-186` and `regression.sh:1287-1297` record failures and carry
on, so a broken compiler still costs ~44 min.

```
smoke (≤2 min)  ──fail──▶ stop
  │
build ritz1 + ritz1_selfhosted ONCE, make -j      (cold ≤1.5 min)
  │
matrix-full (no --rebuild; reuses the binaries)   (≤1 min)
  │
ritz0 pytest -n 8 --dist loadgroup                (≤5 min)
  │
regression.sh, examples in parallel, S4 reuses ritz1_selfhosted (≤2 min)
```

Specific changes:

1. **Stage 4** — drop `BUILD_DIR="$BUILD_DIR"` at `regression.sh:1050`, stop
   discarding stderr, and use the already-built `ritz1_selfhosted` when make
   says it is up to date. Fix the false comment.
2. **Build once, in parallel** — `$(MAKE) -j` in `_matrix_ritz1_built` and
   `--rebuild`; the `.d` files from #1659 make it safe. Build before pytest so
   pytest fixtures become no-ops.
3. **pytest parallel** — add `pytest-xdist`; `conftest.py` builds ritz1 and the
   runtime object once in `pytest_configure` on the controller only; replace 42
   copies of `_build_ritz1()` with one conftest fixture (#1334); put
   shared-tree tests (`test_ritz1_bin_staleness`, `test_build_compiler_switch`,
   `test_ritzlib_output_goldens`, and other build.py-cache users) in
   `xdist_group("tree")`; cap at `-n 8` for memory (`clang -O2` tests take up to 2 GB).
4. **Drop duplicate coverage** — run the ritz0 oracle in-process via
   `ritz0.compile_file` (`ritz0.py:70`, already used by `test_slice_types.py:40`)
   or delete oracle fns whose programs the matrix already runs under ritz0;
   delete `test_slice_types.py:139-168` (runs matrix files verbatim). Fix the
   markers: 36 subprocess-spawning files carry no `integration` mark.
5. **regression.sh parallel** — per-example sandbox and port (today all builds
   share `$BUILD_DIR/sandbox`, `:514`), `xargs -P`; cache the Stage 1 ritz0
   baseline keyed on (ritz0 fingerprint, example content); 1–2 s cap for
   declared non-terminating servers instead of the 5 s kill.
6. **Host budget** — gate wall time doubled from contention alone. Heavy room
   builds and gates should draw from one machine-wide budget (shared flock
   semaphore, or systemd `CPUWeight`/`MemoryMax` on room builds so the gate is
   never starved). Policy (how many slots) is rz's call.

Targets: **full local gate ≤ 12 min uncontended** (baseline 21 min on Oct 18,
44 min contended today); stretch ≤ 8 min.

---

## 6. Design (c) — once-only builds: a content-addressed artifact store

### 6.1 Store

- Location `$RITZ_CACHE_DIR`, default `~/.cache/ritz/cas/` — **shared across
  worktrees**, so ten task rooms compile `ritzlib/io.ritz` once, not ten times.
- Layout `objects/<k[0:2]>/<k>.{ll,o}` + `meta/<k>.json` (inputs, compiler,
  creation time). Writes are tmp-file + `rename` (atomic); readers never see a
  partial entry. No index file to clobber (replaces `deps.json`).
- Never wiped wholesale. Size-capped LRU eviction (`ritz cache gc`).
  `build.py clean` / `rz clean` clean the project's `build/`, not the store.

### 6.2 Key

```
key = sha256(
    compiler_fingerprint,          # ritz0: hash of ritz0/**/*.py + build.py
                                   # ritz1: content hash of the binary (as #1279)
    target_os, target_triple,
    flags,                         # opt level, freestanding, RITZ_VERIFY_IR, debug
    module_source_bytes,
    sorted(import_interface_hash for each direct import))
```

Phase 1 uses the import's **full source hash, transitively** (always correct,
cascades too much). Phase 2 introduces an **interface hash**: the hash of a
module's exported declarations (types, signatures, consts, generic bodies),
so a body-only edit to `ritzlib/io.ritz` does not invalidate every dependent.
The compiler fingerprint is part of the key, so a compiler change simply
misses instead of wiping the store; old entries age out.

### 6.3 Consumers (phase 1, no compiler changes)

| Consumer | Today | With the store |
|---|---|---|
| `build.py compile_binary` | BuildCache, wiped on compiler change | per-entry keyed lookup |
| `test_runner.run_test_file` | one ritz0 subprocess per dependency per test file; links `.ll` text | dependencies fetched as `.o` from the store; only the test file is compiled |
| `run_regression_matrix.py` | ritzlib objects in a tmpdir per run; `list_deps` per cell | store lookup; `deps.closure` memoised per file |
| `regression.sh` stages | via build.py | via build.py (inherits) |
| `ritz1/Makefile` ritzlib objects | private `ritz1/build/ritzlib_*.o` | optional: fetch through a `ritz-cas get-or-build` shim |

ritz0 already emits per-dependency `.ll` (test_runner compiles each dependency
separately), and ritz1 emits per-module (#194), so per-module objects need no
compiler change in phase 1.

### 6.4 Phase 2 — stop re-parsing the closure (compiler work)

`ritz0.py:153` has `use_cache=False` because import stubs lack bodies under the
merged-module architecture. Separate compilation against **interface files**
(the exported declarations above, serialised) removes the full-closure re-parse
from every ritz0 and ritz1 invocation. This is a language-tooling feature and
may surface **language gaps** (what exactly a module exports, how generic
bodies cross module boundaries). Treat those as language tickets under the No
Concessions doctrine, not as cache hacks.

### 6.5 Prerequisite — correctness of the existing fast path

Before anything relies on cached IR: ritz1's `check_source_unchanged` must
include import hashes in its key, and the sig files must leave the source tree
(namespaced per compiler, or moved into the store, which closes #1280). A
cache that can serve stale IR makes every speedup above a liability.

### 6.6 Targets

- `rz test --all` (CI `test-all`): 23.5 min → **≤ 10 min cold**, **≤ 3 min**
  re-run with no change.
- Per gate, each (module, compiler fingerprint, flags) is compiled **at most
  once**, verified by `RITZ_CAS_STATS=1` hit/miss output in the gate log.
- Second worktree on the same commit: ritzlib misses = 0.

---

## 7. Tickets (all priority 90, children of epic #1801)

Order is smallest/safest first. AGAST dependencies: G2→G1, G3→G1, G4→G3, G7→G6, G8→G7, G9→G7; #1280 → G6. Ready now: G1, G5, G6, G10.

| Ticket | Scope | Target |
|---|---|---|
| G1 #1802 | Gate quick wins: Stage 4 rebuild, `-j` builds, build once before pytest, `ci_local --fail-fast`, per-step timestamps | −4 min/gate local; step times in every log |
| G2 #1803 | Smoke tier `make smoke`, first in run-gate and CI | ≤ 2 min cold, ≤ 1 min warm |
| G3 #1804 | pytest parallel (xdist, session build, groups, single `ritz1_bin` fixture) | pytest ≤ 5 min local uncontended |
| G4 #1805 | pytest duplicate-coverage cut (in-process oracle, matrix duplicates, markers) | ≥ 50 % fewer ritz0 subprocesses |
| G5 #1806 | regression.sh parallel + Stage 1 baseline cache + server timeouts | regression.sh ≤ 2 min local |
| G6 #1807 | ritz1 fast path checks import hashes; sig files out of the source tree (#1280) | stale-import test red→green |
| G7 #1808 | Content-addressed artifact store, phase 1 (build.py, test_runner, matrix) | §6.6 |
| G8 #1809 | `rz build/test --all` parallel across packages and files (after G7) | `test-all` ≤ 6 min CI |
| G9 #1810 | Interface files / separate compilation (phase 2) | ritz0 per-invocation parse ≤ own module + interfaces |
| G10 #1811 | Host build budget shared by room builds and gates | gate wall time within 1.3× of uncontended |
