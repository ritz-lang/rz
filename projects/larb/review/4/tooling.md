# LARB v4 Review: build and test tooling

**Reviewed:** 2026-10-25 · **Status:** NEEDS WORK
**Scope:** `./rz`, `rz.toml`, `projects/ritz/{build.py, cache.py, packaging.py}`, `projects/ritz/tools/*.py`,
`projects/ritz/scripts/*.sh`, the Makefiles, `.github/workflows/*.yml` and `run-gate.sh`.
Metrics: `ritz_metrics.py --lang py` over 33 files, 11,867 SLOC, 635 functions.
Performance and caching are reviewed separately in [fast-iteration.md](fast-iteration.md) (epic #1801).

## Summary

The parts of the tooling that run are well guarded:
- strict-xpass allowlists;
- `ci_local.py` reads `main.yml` rather than restating it;
- the harness self-tests source `regression.sh` in library-only mode.

The structure around them has grown only by adding layers:
- five ways to build ritz1;
- three import scanners;
- two dependency walkers;
- four allowlists in three formats, with the outcome logic written three times;
- about 1,000 dead lines in `rz`;
- a 902-line packaging module that only its tests use;
- about 13k lines of dead files, including ELF binaries, in git.

## Findings

### F1. The build cache's import scanner misses 30% of imports [correctness] — Critical → #1832 (fast-iteration epic)
`cache.py:151` uses `IMPORT_PATTERN = ^import\s+NAME\s*$`.

The tree has these import forms:

| Form | Count | Matched? |
|---|---|---|
| `import X` | 2,410 | yes |
| `import X { … }` | 880 | **no** |
| `pub import X { … }` | 73 | **no** |
| `pub import X` | 68 | **no** |
| `import X as Y` | 1 | **no** |

That is 1,022 of 3,432 imports the scanner cannot see. The scanner feeds `needs_rebuild` (`cache.py:600`), which `build.py:1440` uses to decide whether a module's cached `.ll`/`.o` can be reused. So after a struct change in a brace-imported module, its dependents' cached objects can be stale. This is the same class of bug as #1659 and #1674. The regex was checked by the reviewer; the stale-object outcome has not been reproduced.

### F2. Four allowlists, three formats, the outcome logic written three times [architecture] — Major → #1834
- **The allowlists:**
  - `rz.toml [ci.known_failing]`
  - `regression-known-failures{,-ritz1}.txt`
  - `run_regression_matrix.py:49-127 EXPECTED_FAILURES`
  - the xfail and skip markers
- **The outcome logic:** `rz:241`, `run_regression_matrix.py:130` and `regression.sh:292-318`.
- **The "cites an AGAST id" rule** is tested three times.

### F3. `compile_binary` and `compile_freestanding_binary` are diverging copies [architecture] — Major → #1835
- **Sizes:** `build.py:1260` (189 SLOC, CC 64) and `:1615` (243 SLOC, CC 64, depth 8).
- **What the freestanding copy does differently:**
  - it ignores `use_cache`;
  - it writes no provenance file;
  - it calls clang directly (`:1809`) without the timeout and memory cap;
  - it stops at the first failure, which #1286 forbids.

### F4. `build.py` is a god module [architecture] — Major → #1835
- **Size:** 2,914 lines and 1,958 SLOC.
- **What it mixes:** CLI handling, manifest parsing, dependency resolution, planning, compiling, linking, test running and packaging commands.
- **Subprocesses:** of 15 `subprocess.run` calls, 3 have a timeout. `rz` makes 12 more, none of them with a timeout.

### F5. About 1,000 dead lines in `rz` [cleanup] — Major → #1836
- `run_pipeline` (`rz:1055`, the only `shell=True`) has zero callers.
- `compile_with_*`, `link_llvm_ir` and `detect_main_params` (`rz:553-671`) have zero callers.
- `rz ci plan/run/generate`, with templates for three CI systems (`rz:845-1465`), is used by nothing.
- `rz compare` (`:732`) duplicates Stage 3 without the allowlists.

### F6. Two dependency resolvers that disagree [architecture] — Major → #1835
`rz:186` follows dependencies only for packages directly under `projects/`. `rz:850` drops nested packages from impact analysis. `build.py:721/812` resolves on its own. Since #1383, workspace members are `projects/**`.

### F7. `packaging.py` is only used by its tests [cleanup] — Major → #1836
Its 902 lines are reached only from `build.py install/vendor/lock/global` and its own tests. The repo has no lockfiles and no vendor directories. The module name also shadows PyPI's `packaging`.

### F8. Config keys read by nothing; the spec promises unimplemented features [cleanup] — Major → #1837
- **Never read:**
  - `rz.toml [build] cache/parallel/max_jobs` and `[agents]`;
  - manifest `[[test]]`, `[[lib]]`, `[dev-dependencies]`, `[scripts]` and `[features]`.
- **Specified but not implemented:** `RITZ_TOML_SPEC.md:107-123` and `:149-165` describe features no code provides.
- **False comment:** `rz:423`.

### F9. CI [cleanup] — Major → #1838
- **`pr.yml` is dead.** Merges are local fast-forwards, so it never triggers, and its affected-project logic ignores reverse dependencies.
- **The lint jobs exit 0 on every runner.**
- **Setup is copied** into each of 4 jobs.
- **`build-all` and `test-all` only run after merge,** because `run-gate.sh` runs only the bootstrap job. `main.yml` concluded "failure" on each of its 15 most recent runs on main, with `test-all` red in the runs examined (for example 40155556007: nexus, prism and spire, plus tempest-tab).

### F10. Legacy ritz1 build paths [cleanup] — Major → #1268 (existing, evidence appended)
`ritz1/bootstrap_ritzlib/` is 31 files and 11,685 lines, and nothing references it, yet mechanical migrations still touched it on 2026-10-18. `ritz1/compile.sh` is referenced only by a "never use" doc.

### Minor
- **F11:** `regression.sh` Stages 3 and 4 are the same 55 lines with the compiler name changed. Word-splitting and SC2155 bugs; the self-tests don't cover the stage drivers. → #1838
- **F12:** compiler fingerprints are computed in two places. → #1807
- **F14:** `ritz-lint` exists twice (92 lines of diff between the copies). → #1838
- **F16:** `scripts/test_ritz1.sh` prints "All tests passed!" over an empty glob. → #1268
- **F18:** `parser_gen.py.orig` is tracked. → #1822

## Dead files (tracked in git, referenced by nothing; checked with git grep)
- **ELF binaries:** `projects/ritz/{hello_test, ritzgen_test, ritz1_bin, out/test_json}`, `ritz1/ritz1_new`, `ritz0/cat_ll`
- **Profiler and status leftovers:** `callgrind.out.*` (3 files), `BOOTSTRAP_SESSION_SUMMARY.txt`, `FINAL_BOOTSTRAP_STATUS.txt`
- **Old build helpers:** `ritz1/{Makefile.working, verify_integration.sh, bootstrap_env/ritzlib}`, `ritz1/bootstrap_ritzlib/`, `scripts/{build_ritz1, test_ritz1, test_tier1, bootstrap_test}.sh`

All of these are listed on #1268.

## Long-term: `rz` written in Ritz

`projects/rzrz` (353 lines) is a front end that shells out to `python3 ./rz`. Porting the orchestration to Ritz is blocked by five things:
1. ritzlib has no TOML parser.
2. The import closure exists only in Python. ritz1 needs a `--emit-deps` that can replace `mkdeps.py` and the `cache.py` scanner.
3. ritz1 has no `--test` harness.
4. sha256 lives in cryptosec and harland, not ritzlib.
5. ritzlib's `process` has no timeouts or resource limits.

Shrink the Python down to one core of manifest, resolve and pipeline first (#1835, #1837); porting today would carry the duplication across.

## Tickets

| Ticket | Pri | Finding |
|---|---|---|
| #1832 | 85 | F1: cache import scanner (fast-iteration epic #1801; G7 #1808 depends on it) |
| #1834 | 50 | F2: one known-failures schema and outcome module |
| #1835 | 45 | F3, F4, F6, F13: split `build.py`, one pipeline, one resolver, bounded subprocesses |
| #1836 | 45 | F5, F7: dead `rz` code, `packaging.py` |
| #1838 | 45 | F9, F11, F14: CI cleanup, `regression.sh` stage function |
| #1837 | 40 | F8: manifest schema, spec generated from it |
| #1268 | 45 | F10, F16, dead files (existing ticket, evidence appended) |

Epic: **#1833** (tooling consolidation).
