# Stack matrix — bootstrap layering

## The three compiler stages

| Stage | Binary | Built by | Tool that drives it |
|---|---|---|---|
| **ritz0** | Python source (`projects/ritz/ritz0/`) | (interpreted) | `rz` |
| **ritz1** | `projects/ritz/ritz1/build/ritz1` | ritz0 | `rz --compiler ritz1` |
| **ritz1_selfhosted** | `projects/ritz/ritz1/build/ritz1_selfhosted` | ritz1 | `rzrz` |

## The two orchestrators

- **`rz`** — Python script. Part of the initial bootstrap. Drives `build.py`. Used to build ritz0, ritz1, and `rzrz` itself.
- **`rzrz`** — Ritz program at `projects/rzrz/`. The Ritz-native port of `rz`. Compiled by ritz1. Drives ritz1_selfhosted.

## How to run the stack matrix

```bash
# Column 1 — ritz0 (Python)
./rz build <project>                    # default compiler is ritz0

# Column 2 — ritz1 (Ritz, compiled by ritz0)
./rz build <project> --compiler ritz1

# Column 3 — ritz1_selfhosted (Ritz, compiled by ritz1)
./rz build rzrz --compiler ritz1        # one-time: build rzrz with ritz1
./projects/rzrz/build/debug/rzrz build <project>
```

For each project in `{valet, zeus, nexus, mausoleum, tome, spire}`, all three columns must build cleanly before the bootstrap is considered complete.

## Language matrix (separate, runs per-test)

```bash
make -C projects/ritz matrix-full       # 33 tests × 3 compilers
```

This runs `tools/run_regression_matrix.py` which exercises ritz0, ritz1, and ritz1_selfhosted on the language regression suite. It does NOT exercise the application stack (valet, zeus, etc.).

## Current state (refresh as columns turn green)

| Project | ritz0 | ritz1 | ritz1_selfhosted |
|---|---|---|---|
| zeus | ✅ | ✅ | (blocked: rzrz needs Span$u8→i64 fix to build with ritz1) |
| valet | ✅ | ❌ MONOMORPH | (gated on ritz1) |
| nexus | ✅ | ❌ codegen | (gated on ritz1) |
| mausoleum | ✅ | ❌ codegen | (gated on ritz1) |
| tome | ✅ | ❌ codegen | (gated on ritz1) |
| spire | ✅ (lib only) | (lib only) | (lib only) |

## Why three columns matter

Each column proves a different invariant:

- **ritz0 column** — sanity baseline. The reference Python compiler must work; everything downstream depends on it.
- **ritz1 column** — proves the self-hosted compiler is functionally correct. ritz1 ≡ ritz0 on the application stack.
- **ritz1_selfhosted column** — proves the bootstrap is closed. If ritz1 can recompile itself and that binary in turn compiles the stack identically, we have a fixed point. This is the canonical "you can throw the Python away" milestone.

When a future task spec says "build the stack matrix", it means **all three columns** for **all stack projects**, not just the language regression matrix.
