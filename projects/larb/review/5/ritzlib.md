# LARB v5 Review: ritzlib (standard library)

**Reviewed:** 2026-11-16 · **Baseline:** review/4 (2026-10-25) · **Status:** NEEDS WORK

**Metrics:** [metrics-ritzlib.md](metrics-ritzlib.md). Same command as review/4: `ritz_metrics.py projects/ritz/ritzlib --top 25`. Rerunning the current tool on a `git archive 30815afa` tree reproduces review/4's numbers exactly (81 / 14,089 / 1,546), so the two runs compare like for like. Code at main 6f245b93. HEAD 1f18c488 differs from it only in `projects/larb/review/4/rulings-2026-11.md`.

## Summary

Review/4's two Critical findings are resolved or largely resolved:
- **Async (C2):** the five async runtimes are now one family under `async/` (cc4d6a8e).
- **Drop (C1):** the language now defines Drop (spec §13.6), and all three compilers implement it, gated by `ritz0/test_ownership_free_count.py`.
- **Formatting (M1):** integer formatting is now a single routine, `fmt.ritz`, and it is correct for `i64::MIN`.
- **Byte views (M2):** there is now one byte-view type.

What remains:
- **Vec and String still have no Drop.** Their `impl Drop` blocks are still commented out, and the reason given is still the false "ritz1 doesn't support impl blocks". So ritzlib's two most-used containers leak, while GrowBuf, HashMapI64 and Box free themselves.
- **The kernel still can't use the allocator.** ritz0 refuses `memory.ritz` for harland with "`sys_mmap` called with 6 argument(s) but defined with 4" (`memory.ritz:42`).
- **No movement on generic HashMap, argspec migration or docs.** Generic HashMap and the args → argspec migration have not moved. That is despite argspec's stated ritz1 blocker no longer holding: ritz1 now compiles `argspec.ritz`. README and STDLIB_REFERENCE still carry most of review/4's false claims.

No function or file crosses a v4 size threshold. Status stays NEEDS WORK because of the open Major findings: M3, M4 and M6, plus C1's container gap.

## Against review/4

| id | title | r4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| C1 | Ownership/Drop undefined in practice | Critical | PARTLY | Language side fixed. Spec §13.6 (`docs/LANGUAGE_SPEC.md:4610`) defines scope-end, `return`, `break`/`continue` and assignment drops. `drop.ritz:1-27` and `STDLIB_REFERENCE.md:174-188` now agree with it. ritz0, ritz1 and ritz1_selfhosted are gated by `ritz0/test_ownership_free_count.py` (f2096693, #2157/#2158). Still open: `impl Drop` for `Vec<T>` and `String` is commented out (`gvec.ritz:36-46`, `string.ritz:36-46`), and both keep the false "ritz1 doesn't support impl blocks" note. Live Drop impls: Box, Heap, GrowBuf and HashMapI64 only. The STDLIB_REFERENCE cites #2159 for the gap. | #1854 |
| C2 | Five async runtimes, one live | Critical | FIXED | `async.ritz`, `executor.ritz`, `async_runtime.ritz`, `async_tasks.ritz`, `async_fs.ritz` and the `async/{executor,io,mod,server,task}` fork are deleted (cc4d6a8e). What remains is three modules with distinct roles, each stated in its header: `async/runtime.ritz:1-10` (one future), `async/tasks.ritz:1-21` (task pool) and `async/blocking_fs.ritz:1-6` (blocking calls behind `async fn`). `struct Task`/`TaskPool` are now defined once. No importer of a deleted module remains anywhere in `projects/`. Residual: `async_net.ritz` stays at top level and repeats runtime's submit/peek sequence (4× cluster, `async/runtime.ritz:99,126` vs `async_net.ritz:244,270`). | #1855 |
| M1 | Integer formatting ×7; `i64::MIN` prints `-` | Major | FIXED | `fmt.ritz:14-44` holds `fmt_u64_into`, `fmt_i64_into` (negates in u64, `:35`) and `fmt_u64_hex_into`. io, str, string, iovec and testlib all call it (`io.ritz:65,70,79`, `str.ritz:165`, `iovec.ritz:164,182`, `string.ritz:539,547`, `testlib.ritz:93`). No `0 - n` formatting remains. `i64::MIN` is tested in `tests/test_string_io.ritz` and `test_strview.ritz`. `format_into` has shipped (spec `:415`, aa407393, #1824). An eighth copy has appeared since: see F2. | #1856, #1824 |
| M2 | Duplicated string/byte types | Major | FIXED | The second `struct StrView` is gone; the only one is `strview.ritz:29`. Span<u8> delegates to strview (`span.ritz:142-209`, 90433b4a). `string_push_strview` is deleted. Appends reserve once and `memcpy` (`string.ritz:260-285`, 1cbcdcc3). GrowBuf stays a separate struct, and its docs now say so (`buf.ritz:7-9`, 8f1d24f2). One read-all loop remains: `vec_read_all_fd` (`gvec.ritz:357`). | #1856 |
| M3 | Platform layering promised, not built | Major | PARTLY | Fixed: an mmap failure is now detected as −4095..−1 (`memory.ritz:26-32`, 1fd8c00d), and harland's syscall table is diffed against the kernel enum (c532e019). Open: `memory.ritz:42,128,285,360` still call the 6-argument `sys_mmap`, but the harland one takes 4 (`sys.ritz:178` vs `:667`), and `ritz0 --target-os harland ritzlib/memory.ritz` fails at `:42:14`. Syscall numbers are still redeclared without an OS gate (`net.ritz:37-53`, `async_net.ritz:46-55`). `calloc` still multiplies without an overflow check (`memory.ritz:442`). There is no `target_arch` in ritzlib. `README.md:13` still makes the kernel claim. | #1857 |
| M4 | Generic HashMap: stale blocker; real one is trait bounds | Major | OPEN | The stale note is still at `hashmap.ritz:15`. Spec `:3826` says "no trait bound on a generic parameter". `tempest/lib/network.ritz:16,66,68` still imports the non-existent `HashMap`. Selective import still does not filter (spec §15.1, `:5027`). | #1858, #1621 |
| M5 | Errors as sentinels; C idioms | Major | PARTLY | Same grep, run on both trees (non-test `pub fn`s): `-> Result/Option` 23 → 23 of 755 → 747; `return -1` 95 → 86; `return null` 81 → 82; i32 predicates 49 → 24; bool predicates 10 → 33 (a7c13ad8 #1943 covers String/StrView/Span); `*Struct` receivers 272 → 238. Production `i32_as_bool` smell 112 → 90. Still open: `json_parse2` always reports `UNEXPECTED_CHAR` (`json.ritz:487`); `vec_valid` returns 1 (`gvec.ritz:158-160`); the stale `option_map` comment (`option.ritz:41`); 24 i32 predicates (fs `mode_is_*` `:128-152`, `hashmap_i64_contains` `:319`, `socket_valid` `net.ritz:275`). | #1859 |
| M6 | args → argspec migration stalled | Major | OPEN | `args` has 35 production importers and `argspec` has 1, against 36 and 1 in review/4. The stated blocker is now false: `ritz1/build/ritz1 ritzlib/argspec.ritz` and `examples/tier2_stdlib/77_args/src/main.ritz` both compile with rc 0, yet `argspec.ritz:32-35` still says "ritz1 cannot compile this module yet". | #1859 |
| m1 | HTTP constants in span.ritz | Minor | OPEN | `span.ritz:235-` | #1859 |
| m2 | heap.ritz duplicates box.ritz, 0 importers | Minor | OPEN | The file still exists with 0 importers. `README.md:68` calls it "Heap allocator internals", which is wrong: it is `Heap<T>`, a box. | #1859 |
| m3 | testlib re-implements str with `(*u8, len)` | Minor | OPEN | `testlib.ritz:35` `buf_eq`, `:46` `buf_contains` (both `-> i32`) | #1859 |
| m4 | 7 output tests copy fork harness | Minor | OPEN | Unchanged 7× clusters (`tests/test_*_output.ritz:20-72`) | #1859 |
| m5 | uring SQE prep ladder ×7 | Minor | OPEN | Unchanged 7×/6×/4× clusters (`uring.ritz:349…718`) | #1859 |
| m6 | Stale comments | Minor | PARTLY | `drop.ritz` is rewritten (fixed). Two are still stale, checked by a ritz1 compile of `/tmp/r5chk/t.ritz` (rc 0): `span.ritz:24` (ritz1 now accepts `{ StrView }` selective imports) and `memory.ritz:201` (ritz1 now accepts a `const [3]i64 = [...]`). | #1859 |
| m7 | Vec lacks insert/remove/extend/contains | Minor | OPEN | The `gvec.ritz` `pub fn vec_*` list has none of them. | #1859 |
| D1 | Dead: `async.ritz`, `async/*` fork, `testing.ritz` | — | FIXED | Deleted (cc4d6a8e; f1ead76c #1868). | #1855, #1868 |
| D2 | Dead: `heap`, `crt0`, `entry`, `meta`, `lang/lexer`, `lang/tokens` | — | OPEN | 0 production importers each; `lang/tokens`' only importer is `lang/lexer`. | #1859 |
| D3 | Dead: `timer` | — | OBSOLETE | It now has a production importer: `spire/lib/model/timestamp.ritz`. | — |
| Doc1 | README false claims | — | OPEN | `README.md:45-52` still shows `GVec`/`gvec_init`, and `let s: *u8 = "hello"`. `:13` still has the kernel claim. The module table lists the deleted `testing.ritz` (`:89`) and omits 8 modules: argspec, async_net, ct, fmt, lang/lexer, lang/tokens, ptr, testlib. | #1859 |
| Doc2 | STDLIB_REFERENCE false claims | — | PARTLY | Fixed: `:174-188` (Drop), the "ritz1 does not parse trait" line (gone), and `testing` (`:2243-2245` now says removed). Open: `:27` still names `HashMap`, and `:1108` still says "the actual entry point is generated by the compiler". | #1859 |

**Totals (20 rows):**
- FIXED 4: C2, M1, M2, D1.
- PARTLY 5: C1, M3, M5, m6, Doc2.
- OPEN 10: M4, M6, m1-m5, m7, D2, Doc1.
- REGRESSED 0.
- OBSOLETE 1: D3.

**Commit claims vs code:** none contradicted. 4bb7e105 ("one integer digit routine") was true when it landed, and 0ab9b1b8 added another copy later (F2). c532e019 ("harland: one syscall ABI") is scoped to syscall numbers, so it does not claim the allocator builds, and it doesn't. AGAST ticket states were not consulted: no AGAST access this pass.

## Metrics delta

| metric | review/4 | now |
|---|---|---|
| files / SLOC / functions | 81 / 14,089 / 1,546 | 76 / 13,744 / 1,520 |
| non-test files / SLOC / functions | 46 / 8,543 / 960 | 40 / 7,856 / 903 |
| fn SLOC > 150 / > 300 | 0 / 0 | 0 / 0 |
| CC > 30 / > 80 | 1 / 0 (meta_free 55) | 1 / 0 (meta_free 55) |
| nesting ≥ 6 / ≥ 9 | 6 / 0 | 3 / 0 (async fork gone) |
| file SLOC > 1500 | 0 | 0 |
| top fn SLOC / top CC | meta_free 110 / 55 | meta_free 110 / 55 (unchanged) |
| largest file | sys.ritz 835 | sys.ritz 821 |
| duplicate clusters (all / ≥ 3 copies / ≥ 8) | 95 / 33 / 0 | 63 / 28 / 0 |
| smell total (all / non-test) | 820 / 348 | 824 / 329 |
| `i32_as_bool` (all / non-test) | 137 / 112 | 117 / 90 |
| `ptr_len_param_pair` (all / non-test) | 60 / 51 | 62 / 53 |
| `cstr_literal` (all / non-test) | 347 / 89 | 362 / 91 |
| `malloc_magic_size` | 28 | 32 (test_memory only) |

Test code grew: `test_async_server.ritz` (354 SLOC) and `test_memory.ritz` (424 → 482).

## New findings

### F1. HashMapI64's probe loop is written four times, with integer state codes [cleanup] — Major
- **Evidence:** the probe is copied in `hashmap_i64_get` (`hashmap.ritz:224`), `hashmap_i64_value_ptr` (`:247`, added by 0ab9b1b8 for R15 indexing), `hashmap_i64_contains` (`:320`) and `hashmap_i64_remove` (`:342`). The metrics show it as clusters of 4× (`hash_i64(key)`) and 3× (`idx & mask`, `var i`). Dup-window lines went from 36 to 60. Slot state is the magic `0/1/2`, as in `entry.state == 0  # EMPTY` and `entry.state = 2  # TOMBSTONE` (`:215-237`, `:327-352`), rather than an enum. `contains` returns `i32` (`:319`). The `is_empty` method returns `i32` (`:97`, added 2026-11-15 in 913687523, after the #1943 bool sweep).
- **Fix direction:**
  - One `hashmap_i64_find(m, key) -> i64` slot search; get, value_ptr, contains and remove become thin wrappers over it.
  - Add `enum Slot { Empty, Full, Tomb }`.
  - Return `bool` from `contains` and `is_empty`.
  - This removes three of the four probe loops and is the template generic `HashMap<K,V>` (M4) will copy.
- **Ticket:** #3451.

### F2. An eighth integer formatter appeared after the fmt consolidation [cleanup] — Minor
- **Evidence:** `hashmap_i64_missing_key` (`hashmap.ritz:270-291`, 0ab9b1b8) hand-rolls a `% 10` digit loop. It is correct for `i64::MIN`, but `fmt.ritz:6` says new code must call fmt. It also passes `c"HashMapI64: key not found: "` with a hand-counted length of `27` (`:272`).
- **Fix direction:** `fmt_i64_into` plus a StrView literal, or `eprint` interpolation. A grep for `% 10` outside `fmt.ritz` that must come back empty would stop the next copy.
- **Ticket:** #3452.

### F3. `ptr.ritz` is a spec-cited module with no ritzlib or production user [cleanup] — Minor
- **Evidence:** the spec names `ptr_read<T>` as the escape hatch (`LANGUAGE_SPEC.md:4048`, `STDLIB_REFERENCE.md:224`). The module header says "Container code … reads them with ptr_read" (`ptr.ritz:3-5`), but no `.ritz` file imports `ritzlib.ptr`. Its only user is `ritz0/test_ref_into_value.py:341`. It also copies byte by byte (`:13-16`) instead of using `memcpy`.
- **Fix direction:** have `gvec`/`hashmap` element reads go through it once Vec gets Drop (C1), or drop the "container code" claim. Use `memcpy`.
- **Ticket:** #3452.

### F4. New public API repeats the `(*u8, len)` pattern [cleanup] — Minor
- **Evidence:** `ct_bytes_eq(a: *u8, a_len: i64, b: *u8, b_len: i64)` (`ct.ritz:20`, cca1f597, new since review/4) takes two pointer/length pairs where StrView (`strview.ritz:29`) fits.
- **Fix direction:** `ct_eq(a: StrView, b: StrView) -> bool`. Its only caller is tome (`tome/lib/commands.ritz`).
- **Ticket:** #3452.

## Not findings

- **`meta_free` (CC 55, depth 8, `meta.ritz:135`):** it crosses the Major thresholds, but `meta.ritz` has no production importers (D2). Delete the module rather than split the function.
- **`args_parse` (depth 7, `args.ritz:158`):** it is in the deprecated module, and the fix is M6.
- **`task_server_run_multishot` (depth 6, `async/tasks.ritz:786`):** this is at the threshold, in the live tome/valet event loop. Its shape is unchanged from review/4, which didn't raise it. It's a candidate if C2's follow-up touches tasks.
- **`(*u8, len)` in `async/tasks.ritz:303-411` (`task_send_buf` etc., smell 2 → 6):** these are mutable I/O buffers handed to io_uring. StrView is read-only, and Ritz has no mutable byte slice to use instead.
- **`json.ritz:313` and `strview.ritz:413` `0 - val`:** these are parse-side negations of an accumulated positive value, not formatting. Overflow on `-9223372036854775808` input is a separate parse-range issue, not M1.
