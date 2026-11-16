# LARB review/5: overall code assessment (2026-11-16)

**Baseline:** review/4 (2026-10-25, `projects/larb/review/4/`) · **Measured on:** `main` @ 6f245b93
**Method:** `INSTRUCTIONS_v4.md`, unchanged, so the numbers compare. Every area reran `ritz-metrics`
over review/4's paths. Where a tree moved, the script was also rerun on the review/4 commit, and it
reproduced review/4's tables. Each review/4 finding was rechecked against the code, not against its
ticket's status. Repros were single files; no full builds or boots. Area write-ups:

| Area | File | review/4 | review/5 | Against review/4: fixed / partly / open / regressed / obsolete | New: C / M / m |
|---|---|---|---|---|---|
| ritz1 | [ritz1.md](ritz1.md) | CRITICAL | **CRITICAL** | 4 / 3 / 2 / **4** / 0 | 2 / 4 / 2 |
| ritz0 | [ritz0.md](ritz0.md) | NEEDS WORK | NEEDS WORK | 1 / 3 / 0 / **1** / 0 | 0 / 2 / 4 |
| ritzlib | [ritzlib.md](ritzlib.md) | NEEDS WORK | NEEDS WORK | 4 / 5 / 10 / 0 / 1 | 0 / 1 / 3 |
| tooling + fast iteration | [tooling.md](tooling.md) | NEEDS WORK | NEEDS WORK | 11 / 9 / 5 / **2** / 0 | 0 / 3 / 1 |
| harland + goliath | [harland.md](harland.md) | CRITICAL | **CRITICAL** | 1 / 6 / 20 / 0 / 0 | 0 / 2 / 5 |
| packages | [packages.md](packages.md) part 1 | NEEDS WORK | NEEDS WORK | 4 / 7 / 5 / **1** / 0 | 1 / 3 (both parts) |
| infra | [packages.md](packages.md) part 2 | CRITICAL | NEEDS WORK | 3 / 4 / 4 / **1** / 0 | (above) |
| **Total** | | | | **28 / 37 / 46 / 9 / 1** (121 rows) | **2 / 13 / 18** |

## What improved

- **Correctness bugs review/4 named are fixed, and the repros confirm it.** ritz1's silent
  capacity drops, the `[N]u16` layout bug, tab indentation hanging and the `sizeof` mismatch are
  all fixed. In infra, the TLS length bounds and the fail-closed client are in (with a
  client-to-valet test), and the nexus response overflow is gone. ritzunit is now the test runner
  on both compilers.
- **Fast iteration is the clear success.** All of epic #1801 (#1802–#1811) is in the code:
  - the local gate's median fell from **45.5 min to 12.3 min**, and the smoke tier answers
    "fully broken" in **58 s** (it used to take about 26 min);
  - CI `test-all` fell from 23.5 min to 2 min 13 s;
  - `main.yml` passed its last 14 of 14 completed runs (review/4: 15 of 15 failed).
- **Dead code is gone and guarded.** ritz0 dropped about 11,900 unreachable lines, and a reachability
  check now runs in `tools-unit`. ritz0's duplicate clusters fell from 884 to 126; ritzlib's async
  runtimes are one family, and its integer formatting is one routine.
- **The kernel's interface layer is real:** a table-driven syscall dispatcher on `enum Syscall`, one
  `Errno`, an ABI diffed against ritzlib by a test, and `kernel/src/main.ritz` down from 2,677 lines
  to 556.
- **Language gaps review/4 named are closed in the spec:** Drop (§13.6), `asm` (§18.6),
  `format_into`, and the kernel features (atomics, `fence`, volatile MMIO).

## What got worse: both compilers are absorbing language rules faster than their structure can

This is the main finding of review/5. In three weeks the rulings (R1–R52) were implemented on
both compilers, with no checking phase for them to live in:

- **ritz1 doubled**, from 25.8k to 56.6k SLOC and from 763 to 2,515 functions. Six hand-written files
  are now over 3,000 SLOC (there were none). The import cycle grew from 7 to 25 modules.
  - **Why:** the new ownership, ref, let, bool, call and must-use checks (about 8.1k SLOC with
    their helpers) were built on `EmitterState` and run during IR emission. Ownership inserts drops
    by re-scanning IR text it already wrote.
  - **Result:** all four of review/4's design findings for ritz1 are REGRESSED: no semantic phase,
    IR built as strings, decomposition, and C idioms. For example, `i32`-as-bool went from 389 to
    1,185, and there are still 0 `enum`, `match` or `impl` in ritz1.
- **ritz0's emitter grew** from 12.4k to 17.4k lines, and its function count doubled to 518. Its
  `raise EmitError` went from 13 to 134: language rules are landing in the emitter, because the
  type checker is still off by default (only its reference-slot rules run). Ritz types are now
  inferred in four separate places. The emitter split, #1826, hasn't started.
- **The gate is climbing back.** The ritz0 suite went from 2,898 to 39,054 tests, mostly
  parametrised matrices, and the gate is rising about 50 s a day. The CI bootstrap job is slower
  than at review/4 (20 min vs 13 min).
- **New code repeats the anti-patterns review/4 named:** rzsh's new parser (fixed global tables,
  integer kind codes), nexus's rewritten modules (`(*u8, len)` pairs, `i32` booleans), and a
  fourth copy of HashMapI64's probe loop.

## Still open and Critical

- **harland C1:** one 4 KB syscall stack holds a 21 KB `readdir` frame. A test now pins the
  workaround. **C2:** the mmap region is inside the shared identity map.
- **The kernel is never booted in CI.** About 12 harland commits since review/4 were verified by
  greps over the source. `origin/harland-main` is still unmerged (21 commits) and still holds fixes
  `main` lacks.
- **ritzlib:** `Vec` and `String` still have no `impl Drop` (it's commented out, citing a ritz1
  limit that no longer exists), so the two most-used containers leak. That is #2159. LARB R57–R59
  set up its prerequisites.
- **Security (infra):** mausoleum makes X25519 private keys without checking `getrandom`. valet
  ignores `Transfer-Encoding` and reads a non-numeric `Content-Length` as 0.

## Recommendations, in order

1. **Give each compiler a checking phase before more rulings are implemented in it.** ritz0 turns
   its type checker on by default and moves the emitter's 134 rule errors into it. ritz1 moves
   ownership/ref/let/bool/call/must_use off `EmitterState` into a pass over the AST that runs before
   emission (ritz1 N1 → #1816, ritz0 N1 → #3448). Every new ruling then has one home on each compiler. Until then,
   each R-number adds a branch to `emit_*`.
2. **Hold the gate at 12 min:** budget the parametrised matrices, and split ritz0's pytest by tier
   (tooling F1 → #3453).
3. **Boot harland in CI** (one QEMU smoke run that must reach the shell, #1845), then fix C1 and C2 behind it.
4. **Land #2159** (Vec/String Drop) after R57–R59's checks, since the containers leak today.
5. **Fix the two infra security gaps** (existing tickets, still open in code).

Tickets for every new finding are named in each area file's "New findings" section.
