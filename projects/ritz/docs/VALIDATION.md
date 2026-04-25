# Validation Workflow

**How to verify a change without burning 5 minutes on every iteration.**

This document defines the canonical commands for validating Ritz changes at four
escalating levels of thoroughness, what each one actually checks, and which one
you should be running for any given task. It exists because previous debugging
sessions have spent **50+ minutes per iteration cycle** running redundant
full-bootstrap rebuilds when an incremental rebuild would have taken 30 seconds.

If you find yourself reaching for `make clean` to "make sure it works": stop.
Read the rules below first.

---

## The four validation levels

Pick the **lowest** level that actually exercises the surface you changed. Going
higher just wastes time.

| Level | Command (run from `projects/ritz/`) | Time | Use when |
|---|---|---|---|
| **1. Quick** | `make -C ritz1 ritz1 && python3 tools/run_regression_matrix.py --compiler ritz1 --tests <pattern>` | 5–15 s | Inner-loop iteration on a single failing test |
| **2. ritz1 full** | `make matrix` | 30–60 s | Pre-commit, no self-hosting concerns |
| **3. Full matrix** | `make matrix-full` | 4–5 min | Pre-push, OR after touching anything that affects ritz1's own codegen |
| **4. Pristine** | `make -C ritz1 clean && make -C ritz1 bootstrap && python3 tools/run_regression_matrix.py` | ~5 min | Debugging "is this real or stale build?" — last resort |

**Default cadence**: stay at level 1 until your change passes for the test you're
working on. Run level 2 once before committing. Run level 3 once before pushing
(or whenever you touch anything that shows up in `ritz1`'s own compiled output).
Level 4 is for genuine "I don't trust the build state" moments and should be
rare.

### What each level checks

- **Quick (level 1)** — Builds `ritz1` incrementally (only files whose source
  changed), then runs a regex-filtered subset of the regression matrix against
  `ritz1` only. Catches almost all regressions you'd care about during inner-loop
  work.
- **ritz1 full (level 2)** — Same incremental `ritz1` build, then runs the full
  33-test matrix against `ritz1`. Skips selfhost. Catches anything the filtered
  level 1 would miss.
- **Full matrix (level 3)** — Incremental `ritz1` rebuild **and** incremental
  `ritz1_selfhosted` rebuild, then runs all 33 tests against all three compilers
  (ritz0, ritz1, ritz1_selfhosted). Catches "ritz1 itself miscompiles its own
  source" bugs.
- **Pristine (level 4)** — `make clean` + full bootstrap + matrix. Only useful
  when the build itself is the suspect.

---

## Hard rules

These are not suggestions:

1. **Never `make clean` to "make sure it works."** Make's dependency tracking
   is correct. If incremental gives different results from clean, that is a
   Makefile bug to file and fix, not paper over.
2. **Never use `ritz1/compile.sh` for iteration.** It has no dependency
   tracking and recompiles all 27 source files every time, taking ~40 s for a
   one-character edit. Use `make -C ritz1 ritz1` instead — same result, ~10 s
   after a single-file edit.
3. **Don't combine `compile.sh` and `make`.** They both build `ritz1`. Running
   one then the other is redundant work.
4. **Don't bootstrap selfhost unless you actually need to.** Self-hosting takes
   3+ minutes (ritz1 compiling itself is ~5× slower per file than ritz0). If
   your change can't possibly affect `ritz1`'s own compiled output (for
   example, you're only adding a grammar rule that ritz1's source doesn't use),
   skip it.
5. **Never hand-edit `ritz1/src/parser_gen.ritz`.** The grammar (in
   `grammars/ritz1.grammar`) is the source of truth. Edit the grammar, then
   regenerate via `tools/ritzgen_py/ritz_generator.py grammars/ritz1.grammar
   --monolithic --output-dir <tmp>` and copy the output. `make matrix` and
   `make matrix-full` run `make regen-check` automatically and refuse to run
   the matrix if drift is detected — but you can also run `make regen-check`
   directly any time to verify.

---

## Real measured timings (for reference)

Numbers taken on the project as of the green-matrix push. Update if the build
shape changes meaningfully.

| Operation | Time |
|---|---|
| `make -C ritz1 ritz1` from clean | 42 s |
| `make -C ritz1 bootstrap` (ritz1 already built) | 3 m 6 s |
| One ritz1 source file via ritz0 (`emitter.ritz`, 1700 lines) | 2.4 s |
| One ritz1 source file via **ritz1** (same file) | 12.4 s |
| Full matrix (no rebuild) | 1 m 1 s |
| Matrix ritz0 only | 14 s |
| Matrix ritz1 only | 24 s |
| Matrix selfhost only | 33 s |
| `--rebuild --tests <pattern>` (nothing changed) | 6.4 s |

The 5× ritz1-vs-ritz0 per-file gap is the underlying bottleneck. Until that's
addressed the workflow optimisations above are the difference between "5 min
per cycle" and "30 s per cycle."

---

## Common pitfalls

### "I added debug `eprint` statements and the matrix takes 50 minutes"

Don't `make clean`. After editing one source file (typically
`ast_helpers.ritz`), Make's incremental rebuild will only:

1. Recompile that file via ritz0 (~2 s)
2. Recompile via ritz1 for selfhost (~12 s)
3. Re-link both `ritz1` and `ritz1_selfhosted`

Total: ~30 s. The matrix run then adds ~1 minute. Five-minute total per
iteration, not fifty.

### "I edited a grammar rule. Do I need to regenerate the parser?"

If you edited `grammars/ritz1.grammar`, **yes**:

```
python3 tools/ritzgen_py/ritz_generator.py grammars/ritz1.grammar \
    --monolithic --output-dir /tmp/regen_test
cp /tmp/regen_test/parser.ritz ritz1/src/parser_gen.ritz
```

Make doesn't yet track `.grammar` → `parser_gen.ritz` as a dependency. (TODO:
add a `make regen-parser` target and a Makefile rule that triggers it
automatically when the `.grammar` is newer.)

### "I changed `ast_helpers.ritz` but selfhost still has old behavior"

You're running an old `ritz1_selfhosted` binary. Either:

- Run level 3 (`make matrix-full`) — rebuilds selfhost incrementally, or
- Manually: `make -C ritz1 bootstrap`

The selfhost binary doesn't auto-rebuild from `make -C ritz1 ritz1` (which only
rebuilds `ritz1`).

### "ritz0 fails on a file the rest of the build needs"

Almost always a regression in `tools/ritz_lint`, or a missing import in the
file. Run `python3 ritz0/ritz0.py <file>.ritz -o /tmp/x.ll --no-runtime` in
isolation and read the error. Don't escalate to level 3 or 4.

### "The matrix passes locally but fails in CI"

Check that your local `ritz1/build/ritz1` is from the **current** source tree
and not a stale copy. `ls -la ritz1/build/ritz1` and compare its mtime against
`ritz1/src/`. If `ritz1` is older than any source, your level 1/2/3 was lying
to you. Fix: `make -C ritz1 ritz1` again, then re-run.

---

## Integration with `tools/run_regression_matrix.py`

The matrix runner has flags for every level above:

| Flag | What it does |
|---|---|
| (no flags) | Run all 33 tests against all 3 compilers (~1 min) |
| `--compiler ritz1` | Skip ritz0 and selfhost (~24 s) |
| `--compiler ritz1_selfhosted` | Just selfhost (~33 s) |
| `--tests <regex>` | Filter test names |
| `--rebuild` | `make -C ritz1 bootstrap` first (incremental — fast unless source changed) |
| `--verbose / -v` | Per-test output |

The `make matrix` and `make matrix-full` targets in the project Makefile wrap
the most common combinations.

---

## When to escalate

Decision tree:

1. **Did your change touch a `ritz1/src/*.ritz` file?**
   → Run level 1 first. Pass? Run level 2 before commit.
2. **Did your change touch the grammar, the parser, or anything `ritz1`'s own
   source uses (parser_gen, ast_helpers, monomorph)?**
   → Run level 3 before pushing.
3. **Did you only touch a `ritzlib/*.ritz` file or a test file?**
   → Level 1 + level 2 are sufficient. Selfhost compiles ritzlib too, but the
   `--rebuild` path picks that up automatically.
4. **Did you only touch ritz0 (Python)?**
   → `cd ritz0 && pytest` plus level 2.
