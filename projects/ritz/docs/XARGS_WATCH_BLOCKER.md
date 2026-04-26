# xargs / watch — pre-existing build blocker

**Status (2026-04-26)**: `examples/tier4_applications/37_xargs` and
`examples/tier4_applications/40_watch` fail to build. They have not built
since the c-string-literal migration in `3ce7ea4` (2026-04-23).

## Symptom

```
$ make build PKG=examples/tier4_applications/37_xargs
🔨 xargs <- src/main.ritz
✗ ritz0 failed for main.ritz: Compiler error:
  Type of #1 arg mismatch: %"struct.ritz_module_1.StrView" != i8*
```

(40_watch fails identically.)

## Pre-condition

Both files originally used the legacy `&x` reference syntax (now hard-rejected
by ritz0).  Replacing `&x` → `@x` mechanically (one-line `sed`) lets the
parser through, at which point the same StrView/i8* type mismatch surfaces in
the LLVM emit step:

```
emitter_llvmlite.py:_emit_call: TypeError: Type of #1 arg mismatch:
  %"struct.ritz_module_1.StrView" != i8*
```

The crash trace points into `_emit_if`, so the bad call is inside an
`if`-body somewhere — likely an `eprints("...")` or `args_init(@parser, ...)`
where a string literal is being passed to a function expecting `*u8`.

## Hypothesis

The c-string migration (`3ce7ea4`) converted some literals to `c"..."` form
and left others as plain `"..."`.  Each form has a different runtime type:

* `"hello"` → `String` (heap-allocated; auto-coerces to `StrView` for I/O)
* `c"hello"` → `*u8` (raw cstr; what `args_init`/`search_path` consume)

The migration likely missed some sites where a plain literal was being
passed where the callee expects `*u8`, but the residual `&x` syntax
prevented those files from compiling so the type mismatch was hidden until
now.

## Repro

```
cd projects/ritz
sed -i 's/&\([a-zA-Z_]\)/@\1/g' examples/tier4_applications/37_xargs/src/main.ritz
RITZ_PATH=$(pwd) python3 build.py build examples/tier4_applications/37_xargs 2>&1 | tail -20
```

## Fix sketch

1. For each remaining bare `"..."` literal in main.ritz that's passed to a
   function with a `*u8` parameter, change it to `c"..."`.
2. The grep query is roughly:

   ```
   grep -nE '"[^"]*"' src/main.ritz | grep -v 'c"' | grep -v 's"'
   ```

3. Cross-reference each hit with the called function's signature in
   `ritzlib/args.ritz`, `ritzlib/io.ritz`, etc.

Estimated effort: 30-60 min per file; both files together ~1-2 h.

## What this blocks

* `[[test]]` test backfill for these two examples (their integration tests
  for tier 4 backfill cannot land until the binaries build).
* Any `make matrix-full` change that incidentally touches the c-string code
  path — these files are not in the matrix today, so changes there are safe.

## Workaround

Tests for the other 8 tier-4 packages (env, which, printenv, kill, nohup,
timeout, tee, time) land independently.  When xargs/watch are fixed, follow
the standard template (see `docs/TESTING.md`) to add their `test/` files
using the same pattern as 36_timeout (process-wrapper) and 37_xargs's
`test.sh` (stdin-driven).
