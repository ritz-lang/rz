# LARB v4 Review: ritzlib (standard library)

**Reviewed:** 2026-10-25 · **Metrics:** [metrics-ritzlib.md](metrics-ritzlib.md) (81 files, 14,089 SLOC, 1,546 functions) · **Status:** NEEDS WORK
**Method:** `INSTRUCTIONS_v4.md`, read-only. The two claims everything else rests on were checked by the
reviewer before filing:
- `print_int`'s `n = 0 - n` (`io.ritz:63`);
- the spec and the stdlib reference contradicting each other on Drop (`LANGUAGE_SPEC.md:1362` vs `STDLIB_REFERENCE.md:177-180`).

## Summary

No ritzlib function crosses the v4 size or complexity thresholds. The worst is `meta_free`, CC 55, and it sits in a dead module.

The problems are structural:
- **Drop:** it means four different things across the spec, the stdlib reference, ritz0 and ritz1.
- **Async:** there are five runtimes, and one is live.
- **Duplicate types:** string views, byte buffers and read-all helpers each exist two or three times.
- **Integer formatting:** written seven times, and three of those print only `-` for `i64::MIN`.
- **Kernel support:** the README promises it, but harland cannot use the allocator.
- **Stale limits:** several "ritz1 can't do X" comments describe limits that are no longer true.

## Findings

### C1. Ownership/Drop is undefined in practice [language-gap] — Critical → #1854
- **What each authority says:**
  - Spec §13.1 (`LANGUAGE_SPEC.md:1362`): "no destructor insertion today".
  - `STDLIB_REFERENCE.md:177-180` and `drop.ritz:15-20`: drops are inserted at block end, before `return`, and on `break`.
  - ritz0: inserts drops at function scope only (`emitter_llvmlite.py:3776`, `:3884-3903`, `:4294-4304`).
  - ritz1: inserts none.
- **Effect on types:** `impl Drop` exists for HashMapI64, GrowBuf, Box and Heap. These are auto-freed under ritz0 and leak under ritz1. Struct assignment copies (§13.2), so under ritz0 a copied value can be freed twice.
- **Stale reason for the gap:** the `Vec` and `String` Drop impls are commented out (`gvec.ritz:36-46`, `string.ritz:39-46`) because "ritz1 doesn't support impl blocks". It does now.
- **Related:** #1292 (Span use-after-free once Vec's Drop is enabled).

### C2. Five async runtimes, one live [architecture] — Critical → #1855
`async.ritz` (a placeholder with no importers), `executor.ritz`, `async_runtime.ritz`, `async_tasks.ritz` (the live one: tome, valet, mausoleum), and the `async/*` fork, about 2,000 lines in total. `struct Executor`, `Task`, `TaskPool`, `spawn_task` and `run_tasks` are each defined twice.

### M1. Integer formatting written seven times; three break on `i64::MIN` [cleanup] — Major → #1856 (+ #1824)
- **The bug:** `io.ritz:63`, `:88`, `str.ritz:166` and `iovec.ritz:154` negate with `0 - n`. For `i64::MIN` that overflows, the value stays negative, the digit loop never runs, and only `-` is printed. `print_hex` of any negative number prints just `0x`.
- **The seven sites:** `io.ritz:61/86/111`, `str.ritz:162`, `string.ritz:556/585`, `iovec.ritz:154/201`, `testlib.ritz:93-102`. Only `string_push_i64` is correct.
- **Language gap:** interpolation only formats inside `print`/`eprint`, so nothing can format into a buffer (#1824).

### M2. Duplicated string and byte types [cleanup] — Major → #1856
- `string.ritz:22` declares a second `struct StrView`.
- `span.ritz:133-275` re-implements `strview.ritz:107-314`.
- `GrowBuf` is documented as an alias of `Vec<u8>` (`buf.ritz:7`) but is a separate struct (`:404`).
- `string_push_strview` is just another name for `string_push_str`.
- Appends copy one byte at a time (`string.ritz:265-287`).

### M3. Platform layering promised, not built [architecture] — Major → #1857 (feeds EPIC 2)
- **The kernel can't use the allocator:** `memory.ritz:120/274/345` call the 6-argument linux `sys_mmap`, but harland's takes 4 (`sys.ritz:199` vs `:688`). So memory, and with it gvec, string and hashmap, cannot build for harland.
- **Syscall numbers are duplicated:** they are redeclared without the OS gate in `net.ritz:37-52` and `async_net.ritz:46-59`.
- **x86_64 only:** there is no `target_arch`.
- **mmap failures go undetected:** the result is checked with `== -1`, but the kernel returns any value from −4095 to −1 (`:275`, `:346`).
- **`calloc` can overflow:** it multiplies without an overflow check (`:424`).
- **The README is wrong:** `README.md:13` says the same library serves the kernel and Linux.

### M4. Generic HashMap: the stated blocker is stale, the real one is trait bounds [language-gap] — Major → #1858 (+ #1621)
- **Stale blocker:** the note at `hashmap.ritz:13` no longer holds. Multi-parameter generics work (#1574; `Pair<i64, Vec<i64>>` runs on all three compilers). The real missing piece is a `K: Hash + Eq` bound: spec §12.2 says there are none, while ritz0 tests them.
- **Tempest builds against a map API that doesn't exist:** `tempest/lib/network.ritz:16,66,68` imports `HashMap` names that are defined nowhere. It still builds because a selective import does not filter names (§15.1).

### M5. Errors as sentinels; C idioms [cleanup] — Major → #1859
- **Error returns:** 28 of 757 `pub fn`s return `Result` or `Option`. Non-test code has 101 `return -1` and 81 `return null`. `Err` carries a raw errno.
- **JSON:** `json_parse2` has no callers outside ritzlib, and it always reports `UNEXPECTED_CHAR` (`json.ritz:487`).
- **Booleans:** 59 predicates return `i32`; 14 return `bool`.
- **Receivers:** 272 `pub fn`s take a `*Struct`; 169 take `@`/`@&`.
- **Placeholder:** `vec_valid` always returns 1 (`gvec.ritz:157`).
- **Stale comment:** `option_map` is commented out "for lack of higher-order functions", but `buf.ritz:195` already takes a `fn(u8) -> bool`.

### M6. args → argspec migration stalled [language-gap: ritz1] — Major → #1859
`args` is deprecated but has 36 importers; `argspec` has 1. ritz1 compiles every function of an imported module and cannot compile argspec (`argspec.ritz:26-30`, #1440).

### Minor → #1859
- HTTP constants live in `span.ritz:295-333` (they belong in valet).
- `heap.ritz` duplicates `box.ritz` and has no importers.
- `testlib` re-implements `str` with `(*u8, len)` pairs.
- Seven output tests copy the same fork harness.
- The `uring.ritz` SQE prep ladder is repeated 7 times.
- Stale comments: `drop.ritz:23`, `span.ritz:21`, `memory.ritz:190`.
- `Vec` lacks insert, remove, extend and contains.

## Dead modules (no production importers in `projects/*`)
- **No importers at all:** `async.ritz`, `heap.ritz`, `crt0.ritz` (whose own comment at `:73` says it contains no code), `entry.ritz` (`build.py:55-57` links `ritz_start*.o` instead).
- **Test-only, with green tests:** `async/*`, `meta.ritz`, `lang/lexer`, `lang/tokens`, `timer`.
- **Not dead, even though nothing imports it:** `testing.ritz`, which ritz0 injects (`emitter_llvmlite.py:12406`).

## Documentation claims that are false (prose, outside the compile gate)
- **README:**
  - `:50-53`: `GVec` and `gvec_init` do not exist.
  - `:47`: `let s: *u8 = "hello"` is wrong, because `"hello"` is a StrView.
  - `:13`: the kernel claim is false (M3).
  - The module table lists 31 of the 45 modules.
- **STDLIB_REFERENCE:**
  - `:177-180`: the drop-insertion claim (C1).
  - `:173`: "ritz1 does not parse trait" is stale.
  - `:27`: names a "HashMap" type that does not exist.
  - `:2196`: says `testing` provides `_start`; it defines `main`.
  - `:1012`: says the compiler generates the entry point; it comes from the runtime `.o` files.
- **Accurate:** the hashmap and gvec API tables.

## Tickets

Epic **EPIC 3 #47** (re-scoped; its original scope, "consolidate dual async, merge Box/Heap, fix syscall ABIs", is preserved in the ticket).

| Ticket | Pri | Finding |
|---|---|---|
| #1854 | 70 | C1: language decision on ownership/Drop, with ritz0 and ritz1 parity |
| #1856 | 60 | M1+M2: formatting (`i64::MIN` red test first), one byte view, bulk append |
| #1855 | 55 | C2: one async runtime |
| #1857 | 55 | M3: syscall table, freestanding core vs hosted layer, allocator interface |
| #1858 | 55 | M4: trait bounds → `HashMap<K,V>`, selective import must filter |
| #1859 | 45 | M5, M6, minors, dead modules, docs, liveness gate |
