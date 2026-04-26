# Stale `.ritz-cache/objects/*.ll` for orphan modules

**Status (2026-04-26)**: known trap, easy workaround (`rm -rf .ritz-cache`).
The previously-filed "ritz0 bug" turned out to be cache hygiene; the
compiler's per-source emission is correct.

## Symptom

```
$ RITZ_PATH=$(pwd) python3 build.py build examples/tier3_coreutils/24_cp
…
/usr/bin/ld: undefined reference to `string_push_strview'
clang: error: linker command failed with exit code 1
```

A function that exists, is `pub`, is in the source file's import chain,
and is even fully cached in `<src>.ritz.sig` — fails to link because the
whole-file `.ll` cache was generated before the function existed and is
being reused unchanged.

## Why both caches matter

We have two layers:

| Layer | Path | Owner | Role |
|---|---|---|---|
| Per-source `.ll` | `.ritz-cache/objects/<src>.ll` | `build.py` (cache.py) | Skip ritz0 invocation entirely when source + transitive deps unchanged |
| Per-function IR | `<src>.ritz.sig` | `ritz0` internal | Within a ritz0 run, skip emitting unchanged functions and splice cached IR back |

`build.py` consults the .ll cache *first*; if it hits, ritz0 never runs.
That means a stale .ll *masks* the .sig (which would have caught this
correctly via per-function token hashing).

## Why it gets stale

The .ll cache is correctly invalidated when its **own source file or any
transitive dep changes** (cache.py:`needs_rebuild`).  But it stays warm
forever otherwise.  If a module is "orphaned" — nobody in the regularly-
built dep graph imports it — its cache entry never gets re-evaluated.

In our case:
- April 24, `fb5f04b` added `string_push_strview` to `ritzlib/string.ritz`.
- **The only consumers of `ritzlib.string`** at that moment were:
  - `ritz1/src/main.ritz` — but ritz1 builds via `make`, not `build.py`,
    so it never touches `.ritz-cache/`.
  - Four `tier5_async` examples — not in `make matrix`.
- Nothing in tier 1-4 matrix triggered `cache.needs_rebuild(string.ritz)`.
- The April 23 `.ll` cache for `string.ritz` (predating
  `string_push_strview`) sat unrefreshed.
- My tier-3 cp refactor on April 26 was the first matrix-path import of
  `ritzlib.string` since the function was added — and tripped the trap.

## Workarounds (immediate)

```
rm -rf .ritz-cache              # nuke the whole-file cache
make matrix                     # rebuilds correctly
```

Or selectively:
```
rm .ritz-cache/objects/ritzlib_string.ritz.ll
```

## Real fix candidates

1. **Tie `.ll` cache validity to the current commit hash.**  Cheapest:
   `git rev-parse HEAD` becomes part of the compiler-hash blob.  Trade-
   off: invalidates on every commit (harsh, slow).
2. **Validate cache on use, not just on lookup.**  When `build.py` is
   about to consume a cached `.ll`, do a fresh hash of the source file
   *and* its transitive deps, ignoring stored deps.  More work per build
   but catches orphan-module rot.
3. **Drop the per-source .ll cache, lean on .sig.**  The .sig cache is
   correct (function-token-hash keyed) and already does most of the work.
   The per-source .ll cache mostly saves the AST/parse cost; profile
   first to see if that's worth the foot-gun.

Option (1) is the smallest hygiene fix.  Option (3) is the architectural
simplification.  Both worth considering — neither is urgent because the
workaround (`rm -rf .ritz-cache`) is one line and the trap only fires for
orphan modules.

## Reproduction (the symptom is gone now; for posterity)

The trap fired specifically because `ritzlib/string.ritz` was orphaned
from the build.py-tracked dep graph between commit `fb5f04b` and our cp
refactor.  After `rm -rf .ritz-cache && make matrix && build cp`, the
cache is correct and stays correct as long as cp keeps importing
ritzlib.string in matrix-tracked builds.

## Impact

Mostly resolved: `rm -rf .ritz-cache` lets cp refactor use the ritzy
StrView form.  Once verified end-to-end, the `cp_err2`-style helper can
be migrated to take `StrView` parameters and `c"..."` literals can
become `"..."` (StrView) literals across all 17 other example binaries.

## Lessons

* The two-layer cache works — but the layering means the per-function
  .sig cache (which is correct) is shadowed by a coarser per-file .ll
  cache that has fewer correctness invariants.
* "Orphan module" rot is a real problem in monorepos with multiple build
  systems (here: build.py + Make for ritz1).  Hash-based invalidation
  only works when builds actually re-evaluate the hash regularly.
