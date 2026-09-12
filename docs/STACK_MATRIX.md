# Stack matrix — bootstrap layering

## The three compiler stages

| Stage | Binary | Built by | How to build it |
|---|---|---|---|
| **ritz0** | Python source (`projects/ritz/ritz0/`) | (interpreted — nothing to build) | n/a |
| **ritz1** | `projects/ritz/ritz1/build/ritz1` | ritz0 | `make -C projects/ritz/ritz1 ritz1` |
| **ritz1_selfhosted** | `projects/ritz/ritz1/build/ritz1_selfhosted` | ritz1 | `make -C projects/ritz/ritz1 bootstrap` |

`make -C projects/ritz/ritz1 verify` checks that both Ritz-built binaries
compile a program. Verified exit 0 on 2026-09-12.

## The two orchestrators

- **`rz`** — Python script at the workspace root. Part of the initial bootstrap.
  Drives `projects/ritz/build.py`. Selects the compiler with
  `--compiler {ritz0,ritz1,ritz1_selfhosted}` (default `ritz0`).
- **`rzrz`** — Ritz program at `projects/rzrz/`, the Ritz-native port of `rz`.

### `rzrz` is not yet an independent orchestrator

Read `projects/rzrz/src/main.ritz:225-248` before treating `rzrz` as a third
column. `rzrz build <project>` does not compile anything itself — it spawns:

```
python3 ./rz build <project> --compiler ritz1
```

Two consequences, both measured:

1. It still requires Python and the `rz` script. It is a wrapper, not a
   replacement.
2. The compiler it selects is **ritz1**, not ritz1_selfhosted. Running
   `rzrz build <project>` therefore measures column 2 a second time. Use
   `./rz build <project> --compiler ritz1_selfhosted` for column 3.

## How to run the stack matrix

The `./rz clean` is **required** in columns 2 and 3 — see "The `--compiler`
cache defect" below. Without it the build is a no-op that still prints success.

```bash
# Column 1 — ritz0 (Python). Default compiler.
./rz build <project>

# Column 2 — ritz1 (Ritz, compiled by ritz0).
./rz clean <project> && ./rz build <project> --compiler ritz1

# Column 3 — ritz1_selfhosted (ritz1 compiled by itself).
./rz clean <project> && ./rz build <project> --compiler ritz1_selfhosted
```

Confirm which compiler actually ran by checking that the matching per-compiler
dependency cache gained entries — this is the only reliable signal:

```bash
python3 - <<'EOF'
import json
for c in ('.ritz-cache', '.ritz-cache-ritz1', '.ritz-cache-ritz1_selfhosted'):
    d = json.load(open('projects/ritz/' + c + '/deps.json'))
    print(c, len([k for k in d if 'zeus' in k]))
EOF
```

`rzrz` is **not** the column-3 tool, despite earlier revisions of this document
saying so:

```bash
# This builds rzrz itself with ritz1 — fine, and it works (exit 0):
./rz clean rzrz && ./rz build rzrz --compiler ritz1

# But this does NOT give you a ritz1_selfhosted column; it re-runs ritz1:
./projects/rzrz/build/debug/rzrz build <project>
```

## The `--compiler` cache defect (AGAST #1360)

**`./rz build <project> --compiler ritz1` silently does nothing if the project
was last built with ritz0.** It exits 0 and prints the success tick for every
binary, but nothing is recompiled.

Reproduced 2026-09-12 on both `rzrz` and `zeus`. To see it, start from a
ritz0-built state — that is the precondition, and it is the state you are in
after any ordinary `./rz build`:

```bash
./rz clean rzrz && ./rz build rzrz             # ritz0 build, exit 0
stat -c %Y projects/rzrz/build/debug/rzrz      # note the mtime

./rz build rzrz --compiler ritz1               # exit 0, prints "✓ .../rzrz"
stat -c %Y projects/rzrz/build/debug/rzrz      # UNCHANGED — nothing recompiled
python3 -c "import json; d=json.load(open('projects/ritz/.ritz-cache-ritz1/deps.json')); \
            print(len([k for k in d if 'rzrz' in k]))"   # 0
```

The per-compiler dependency cache (`.ritz-cache-ritz1/deps.json`) gains no
entries, proving ritz1 never ran. The ritz0 cache (`.ritz-cache/deps.json`) has
the entries instead. The binary on disk is a ritz0 build wearing a ritz1 label.

**Workaround:** `./rz clean <project>` first. With a clean, the compile really
happens and the cache fills in:

```bash
./rz clean zeus && ./rz build zeus --compiler ritz1     # exit 0
# .ritz-cache-ritz1 zeus keys: 0 → 10
```

Until #1360 is fixed, **treat any `--compiler ritz1` or
`--compiler ritz1_selfhosted` result that was not preceded by `rz clean` as
meaningless**, including results recorded in this file's history.

## Language matrix (separate, runs per-test)

```bash
make -C projects/ritz matrix-full       # 53 tests × 3 compilers, ~35s
```

This runs `tools/run_regression_matrix.py`, which exercises ritz0, ritz1 and
ritz1_selfhosted on the language regression suite. It does **not** exercise the
application stack (valet, zeus, etc.).

Measured 2026-09-12, exit 0:

| Compiler | Result |
|---|---|
| ritz0 | 53/53 |
| ritz1 | 52/53 |
| ritz1_selfhosted | 52/53 |

The one failure is `test_issue_float_coercion` — ritz1 has no float method
dispatch (**AGAST #1370**) — and it is explicitly excused for both ritz1 and
ritz1_selfhosted, which is why the gate prints green. Exit 0 here does not mean
53/53 on every stage.

## Current state

Every cell below was measured on 2026-09-12 by running
`./rz clean <project>` immediately followed by
`./rz build <project> --compiler <stage>`, and the exit status of the build
command itself was checked. Without the `clean` these numbers are worthless —
see #1360 above.

`rz build --compiler ritz1_selfhosted` **does work**; it is the tool for column
three. `rzrz` is not (it delegates to ritz1 — see above).

| Project | ritz0 | ritz1 | ritz1_selfhosted |
|---|---|---|---|
| zeus | ✅ exit 0 | ✅ exit 0 (10 cache entries written) | ✅ exit 0 (10 cache entries written) |
| rzrz | ✅ exit 0 | ✅ exit 0 | ✅ exit 0 |
| spire | ✅ exit 0 | ✅ exit 0 | ✅ exit 0 |
| valet | ✅ exit 0 | ❌ exit 1 | ❌ exit 1 |
| nexus | ✅ exit 0 | ❌ exit 1 | ❌ exit 1 |
| mausoleum | ✅ exit 0 | ❌ exit 1 | ❌ exit 1 |
| tome | ✅ exit 0 | ❌ exit 1 | ❌ exit 1 |

`spire` is `test_only = true` with no `[[bin]]`, so all three of its cells are
"nothing to build" — green, but not evidence of anything.

Failure causes, ritz1 and ritz1_selfhosted identically (the self-compiled
binary reproduces its parent's gaps, which is expected):

| Project | Failure |
|---|---|
| valet | ritz1's parser rejects 3 top-level `const` array items in `projects/cryptosec/lib/aes.ritz` (`cannot parse item starting at 'const SBOX'`), then refuses to emit a partial module. 7 source files fail. |
| nexus | `ritz1 cannot emit: cannot determine receiver type for method call` ×4, plus `unknown identifier 'scan_rebuild_callback'` (function pointer taken by name). |
| mausoleum | Same two classes: 4 unresolved method receivers, plus `unknown identifier 'handle_task_event'`. |
| tome | `unknown identifier 'handle_connection'` — function-pointer-by-name again. |

So the remaining blockers are three ritz1 gaps, not four project bugs:
top-level `const` array parsing, method-receiver type inference, and taking a
function's address by bare identifier.

An earlier revision of this table recorded `zeus: blocked — rzrz needs
Span$u8→i64 fix to build with ritz1` in the selfhosted column. That is
superseded: rzrz builds with ritz1 *and* with ritz1_selfhosted today (exit 0
each, after `rz clean`), and zeus is green in all three columns. The entry was
also mis-framed — zeus's selfhosted column never depended on rzrz, because
`rz build --compiler ritz1_selfhosted` drives it directly.

## Why three columns matter

Each column proves a different invariant:

- **ritz0 column** — sanity baseline. The reference Python compiler must work;
  everything downstream depends on it.
- **ritz1 column** — proves the self-hosted compiler is functionally correct.
  ritz1 ≡ ritz0 on the application stack.
- **ritz1_selfhosted column** — proves the bootstrap is closed. If ritz1 can
  recompile itself and that binary in turn compiles the stack identically, we
  have a fixed point. This is the canonical "you can throw the Python away"
  milestone. Note that "throw the Python away" is still some distance off for a
  different reason: `rz` itself is Python, and `rzrz` currently re-enters it.

When a future task spec says "build the stack matrix", it means **all three
columns** for **all stack projects**, not just the language regression matrix.
Three things stand between here and there:

1. **AGAST #1360** — `--compiler` must invalidate the cache so results are
   trustworthy without a manual `rz clean`.
2. **Three ritz1 gaps** — top-level `const` array parsing, method-receiver type
   inference, and function-address-by-bare-identifier. These are what block
   valet, nexus, mausoleum and tome in columns 2 and 3.
3. **`rzrz` compiling directly** instead of spawning `python3 ./rz`, if the goal
   is a Python-free orchestrator rather than just a Ritz-language one.
