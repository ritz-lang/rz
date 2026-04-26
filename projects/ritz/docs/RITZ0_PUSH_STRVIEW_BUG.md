# ritz0 drops `string_push_strview` body under build.py separate compilation

**Status (2026-04-26)**: latent.  Not blocking matrix; exposed when refactoring
example binaries to use bare-string (StrView) error literals via String
building.

## Symptom

```
$ RITZ_PATH=$(pwd) python3 build.py build examples/tier3_coreutils/24_cp
…
/usr/bin/ld: undefined reference to `string_push_strview'
clang: error: linker command failed with exit code 1
```

`string_push_strview` is `pub`, defined in `ritzlib/string.ritz:280`, and used
across the codebase (e.g. `ritz1/src/main.ritz:134`) — yet *some* compilations
of `string.ritz` produce an .o that lacks both the function body and even a
`declare` line for it.

## Conditions

Reproduces only via the **build.py separate-compilation pipeline**.  Standalone
ritz0 produces the symbol correctly:

```
# Works — symbol present:
$ RITZ_PATH=$(pwd) python3 ritz0/ritz0.py ritzlib/string.ritz -o /tmp/a.ll \
    --no-runtime --target-os linux --deps '{}' --sources '[]'
$ grep -c string_push_strview /tmp/a.ll
2

# Same args via build.py — symbol absent:
$ RITZ_PATH=$(pwd) RITZ_KEEP_TEMP=1 python3 build.py build \
    examples/tier3_coreutils/24_cp 2>&1 | grep "Keeping"
  [DEBUG] Keeping temp dir: /tmp/tmpXXXXXX
$ grep -c string_push_strview /tmp/tmpXXXXXX/string_*.ll
0
```

The two invocations pass the same flags (`--no-runtime --target-os linux
--deps {} --sources []`) and the same source file.  Something else in the
build.py environment — likely a quirk in how the `.sig` file's per-fn cache
or splice interacts with separate-compilation visibility — drops the
function entirely, including its `declare`.

## Why other `string_push_*` functions are unaffected

`string_push`, `string_push_str`, `string_push_string`, `string_push_bytes`,
`string_push_i64` all emit correctly under build.py.  The single missing one
is `string_push_strview` — the only push helper whose second parameter is
`StrView` by-value.  This points at StrView-by-value parameter handling
specifically, perhaps interacting with cache invalidation.

## Likely culprit

`emitter_llvmlite.py:_should_emit_function_body` returns False when a
function name is in `self._cached_fn_names`.  After emission,
`_splice_cached_ir` (line 9636) is supposed to splice the cached IR back
in by regex-matching the corresponding `declare` line.

The splice pattern:

```python
pattern = rf'^declare\s+[^@]+@"?{escaped_name}"?\([^)]*\)\s*$'
```

For `string_push_strview`, the declare would be:

```
declare i32 @"string_push_strview"(%"struct.ritz_module_1.String"* %"s.arg", %"struct.ritz_module_1.StrView" %"sv.arg")
```

The `[^)]*` only allows non-paren chars between `(` and `)`.  Both args are
single-paren-free chunks — so the regex *should* match.  But the symptom
suggests the `declare` line itself isn't being emitted — splicing has
nothing to replace.

## Workaround (temporary)

Use cstr-based String building instead of StrView:

```ritz
# WORKS — string_push_str takes *u8
fn err2(prefix: *u8, path: *u8, suffix: *u8) -> i32
    var s: String = string_from_cstr(prefix)
    string_push_str(@s, path)
    string_push_str(@s, suffix)
    eprintln_string(@s)
    string_drop(@s)
    return 1

# DOES NOT BUILD under build.py — string_push_strview body absent
fn err2(prefix: StrView, path: *u8, suffix: StrView) -> i32
    var s: String = string_from_strview(@prefix)
    string_push_str(@s, path)
    string_push_strview(@s, suffix)  # ← undefined reference at link time
    eprintln_string(@s)
    string_drop(@s)
    return 1
```

The cstr workaround captures most of the win — collapses 3-line write triplets
into a single helper call, preserves the same error message — but at the cost
of cstr literals (`c"..."`) instead of bare strings.

`24_cp` was refactored using the workaround; see commit (TBD).

## Fix sketch

1. Reproduce with the smallest possible test case.  A `*.ritz` that imports
   only `ritzlib.string` and uses `string_push_strview` once should be enough.
2. Print the IR text right before splicing to see whether the `declare` is
   present.  If absent, the bug is in body-skip logic — it's filtering more
   than it should.
3. Compare the standalone vs build.py invocations under a debugger or with
   per-step logging.

Effort: 1-2 h to root-cause, less than that to fix once root cause is clear.

## Impact

* Blocks the "ritzy pass on example binaries" (#6 from the recent code-review
  TODO).  Specifically, blocks bare-string error literals in the cp/rm/mv/
  stat refactors.
* Once fixed, the err helpers in `examples/tier3_coreutils/24_cp/src/main.ritz`
  (and the ones we'll write for the other binaries) should be migrated to
  StrView signatures + bare-string literals.
