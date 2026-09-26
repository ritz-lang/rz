# ritzlib survey — examples, ritz0/ritz1 parity, raw-pointer API

AGAST #1449, measured 2026-09-25 on `origin/main` @ `fbd91fa`
(the stage 3 allowlist was re-checked on `d8d79f6`). `args.ritz` is
excluded (owned by #1448). This is a **snapshot**: the tickets it cites are the
living record, and the table goes stale as soon as they land.

## What was measured

1. **Standalone compile.** Every module was compiled on its own (a stub `main`
   importing only that module) by ritz0 and by ritz1, all the way to a `.o`.
   Nothing was compiled with `-o /dev/null` (#1447).
2. **Example parity.** `scripts/regression.sh --quick` ran stage 1 (ritz0 on
   every example), stage 2 (build ritz1) and stage 3 (ritz1 on every example,
   stdout and exit code compared with ritz0).
3. **Example coverage.** For each module, the number of its public functions
   that some `examples/**/*.ritz` calls as a free function.
4. **Raw-pointer API.** Each `pub fn` signature was classified: any `*T` in a
   param or return counts as *raw-ptr*, and `*u8`/`**u8` also counts as a
   *`*u8` param* (C string or byte buffer).

## Headline

- **Parity is clean where both compilers build.** Stage 1 passed 78, skipped 3.
  Stage 3 passed 58, **failed 0**, skipped 23. No example produced different
  output under ritz1. Every gap is a ritz1 *compile* failure, never a
  miscompile, with one exception: #1451 (pointer arithmetic scaled by 8, not
  `sizeof`) is a silent miscompile that no example happens to hit yet.
- **6 of 46 modules do not compile under ritz1 standalone:** `async.task`,
  `async_fs`, `lang.tokens`, `os.env`, `testing`, `testlib`. Every one has a
  root-cause ticket (below).
- **13 modules have no example that calls them:** `async`, `async.task`, `elf`,
  `entry`, `eq`, `hash`, `hashmap`, `json`, `meta`, `option`, `process`,
  `testing`, `timer`. `buf` is exercised by 1 of its 39 functions.
- **The raw-pointer surface is concentrated in `sys`, `fs`, `uring`, `str`,
  `net`, `json`, `buf`, `memory` and `meta`.** `sys` and `uring` are
  syscall-shaped by design. The rest are tracked under #1347 as one ticket per
  module, ordered bottom-up.

## Per-module table

Standalone columns: `ok` means an object file was produced. "Fns exercised"
counts **free-function** calls only, so method-style use is undercounted. For
example, `strview` shows 0 but 14 examples import it and use it through
methods. † `testlib` is capped at its total; the scanner also matched a
same-named non-pub helper.

| module | pub fns | fns exercised by examples | raw-ptr sigs | *u8 params | ritz0 standalone | ritz1 standalone |
|---|---|---|---|---|---|---|
| `args` | 18 | 14 | 12 | 12 | ok | ok |
| `async` | 7 | 0 | 1 | 0 | ok | ok |
| `async.executor` | 10 | 1 | 4 | 2 | ok | ok |
| `async.io` | 10 | 2 | 6 | 4 | ok | ok |
| `async.mod` | 0 | 0 | 0 | 0 | ok | ok |
| `async.server` | 12 | 3 | 0 | 0 | ok | ok |
| `async.task` | 14 | 0 | 9 | 2 | ok | FAIL |
| `async_fs` | 7 | 5 | 6 | 6 | ok | FAIL |
| `async_net` | 20 | 12 | 5 | 4 | ok | ok |
| `async_runtime` | 9 | 7 | 5 | 4 | ok | ok |
| `async_tasks` | 42 | 5 | 16 | 4 | ok | ok |
| `box` | 6 | 1 | 1 | 0 | ok | ok |
| `buf` | 39 | 1 | 14 | 12 | ok | ok |
| `crt0` | 0 | 0 | 0 | 0 | ok | ok |
| `drop` | 0 | 0 | 0 | 0 | ok | ok |
| `elf` | 13 | 0 | 7 | 7 | ok | ok |
| `entry` | 4 | 0 | 4 | 4 | ok | ok |
| `env` | 5 | 2 | 5 | 5 | ok | ok |
| `eq` | 3 | 0 | 0 | 0 | ok | ok |
| `executor` | 12 | 4 | 5 | 5 | ok | ok |
| `fs` | 54 | 26 | 28 | 24 | ok | ok |
| `gvec` | 25 | 13 | 5 | 2 | ok | ok |
| `hash` | 9 | 0 | 1 | 1 | ok | ok |
| `hashmap` | 13 | 0 | 0 | 0 | ok | ok |
| `heap` | 6 | 3 | 1 | 0 | ok | ok |
| `io` | 25 | 15 | 4 | 4 | ok | ok |
| `iovec` | 14 | 8 | 4 | 3 | ok | ok |
| `json` | 27 | 0 | 16 | 8 | ok | ok |
| `lang.lexer` | 20 | 4 | 7 | 2 | ok | ok |
| `lang.tokens` | 6 | 1 | 4 | 4 | ok | FAIL |
| `memory` | 25 | 12 | 13 | 13 | ok | ok |
| `meta` | 21 | 0 | 20 | 12 | ok | ok |
| `net` | 46 | 7 | 17 | 15 | ok | ok |
| `option` | 3 | 0 | 0 | 0 | ok | ok |
| `os.env` | 9 | 1 | 3 | 1 | ok | FAIL |
| `process` | 19 | 0 | 8 | 8 | ok | ok |
| `result` | 5 | 3 | 0 | 0 | ok | ok |
| `span` | 37 | 6 | 11 | 4 | ok | ok |
| `str` | 25 | 12 | 17 | 17 | ok | ok |
| `string` | 39 | 13 | 9 | 9 | ok | ok |
| `strview` | 27 | 0 | 8 | 8 | ok | ok |
| `sys` | 83 | 31 | 52 | 40 | ok | ok |
| `testing` | 8 | 0 | 3 | 3 | ok | FAIL |
| `testlib` | 6 | 6† | 6 | 6 | ok | FAIL |
| `timer` | 20 | 0 | 1 | 0 | ok | ok |
| `uring` | 29 | 15 | 18 | 12 | ok | ok |

## ritz1 standalone failures → tickets

| module | first ritz1 error | ticket |
|---|---|---|
| `async.task` | unannotated `let p = x as *T` loses its type, so member access fails ("unhandled EXPR_MEMBER") | #1453 |
| `async_fs` | `async fn` items unparsed | #1456 (split from #1310) |
| `lang.tokens` | array-repeat of a struct literal `[S { .. }; N]` | #1362 (updated) |
| `os.env` | block-bodied match arm `None =>` plus indented block | #1454 (split from #1310) |
| `testing` | inline `asm x86_64:` block in a fn body | #1455 (split from #1310) |
| `testlib` | trailing comma in a fn parameter list (testlib.ritz:168) — **not** block match arms, which #1310 had blamed | #1452 |

Found while reducing these: #1451, ritz1 scales pointer arithmetic on
`*Struct` locals by 8 rather than `sizeof(Struct)` (`get_ptr_elem_size`,
`emitter_core.ritz:1378`). It is a silent wrong address, so it gets the
highest priority of this batch.

## Examples ritz1 cannot compile (stage 3 allowlist)

Re-measured on `d8d79f6`: each entry in
`scripts/regression-known-failures-ritz1.txt` was built with
`build.py build <example> --compiler ritz1`, and the first error was reduced to
a minimal repro. All 20 still fail, and every one has an open ticket, so no new
tickets were needed. `77_args` arrived with `d8d79f6` and its blockers (#1487,
#1488, #1497, #1498) are recorded in the allowlist entry itself.

| example | first ritz1 error | root cause | ticket |
|---|---|---|---|
| `13_sort` | undefined `Vec$LineBounds_swap` at link | generic method on `@&Vec<T>` not instantiated; `let tmp: T` in generic body | #1513, #1514 |
| `21_ls` | `%.21` is `i64`, expected `%DirEntry` | struct read by value through `*(p + i)` / array element loads `i64` | #1505 |
| `36_timeout` | cannot parse `fn run_timeout` | `if c then a else b` expression | #1524 |
| `39_time` | cannot parse `fn main` | `if c then a else b` expression | #1524 |
| `44_csv` | unhandled `EXPR_MEMBER` | `Vec<T>` of struct / pointer element type | #1487, #1519 |
| `50_http` | cannot determine receiver type | method on a field receiver; imported impl methods; `i32` method args | #1512, #1517, #1518 |
| `51_loadtest` | undefined `String_push_str` | method mangling uses the type name verbatim | #1368 |
| `56_async_runtime` | undefined `open` at link | syscall builtins unknown to ritz1 | #1516 |
| `57_fn_ptr` | unknown identifier `double` | function name used as a value | #1503 |
| `58_closures` | cannot parse `fn test_no_capture` | closures `\|x\| expr` | #1531 |
| `61_true_async` | unhandled `EXPR_MEMBER` | member access on a param named `self` | #1375 |
| `62_async_compiler` | cannot parse `async` | `async fn` items | #1456 |
| `63_executor` | cannot parse `fn simple_poll` | function name used as a value; `self` param | #1503, #1375 |
| `64_async_io` | cannot parse `async` | `async fn` items | #1456 |
| `65_async_main` | cannot parse `async` | `async fn` items | #1456 |
| `66_for_loops` | cannot parse `fn main` | inclusive range `1..=5` | #1530 (item 1) |
| `68_result_error_handling` | cannot parse `fn main` | call with two explicit type args `f<i64, i32>(..)` (one arg is fine) | #1471 |
| `69_result_string` | `%.13` is `i64`, expected `%String` | match arm binding a struct payload gets `alloca i64` | #1515 |
| `72_raii` | unhandled `EXPR_MEMBER` in assignment | `self`-named param; generic impl methods; `{x}` interpolation | #1375, #1520, #1521 |
| `75_async_reference` | cannot parse `async` | `async fn` items | #1456 |
| `76_option` (added by #1460) | struct literal not in var initializer context | `Some(Point {..})`; match arm binding a struct payload gets `i64` (`Some(p) => p.x`) | #1362, #1515 |

The allowlist is dominated by three causes: `async fn` (4 examples, #1456),
`if` expressions (2, #1524) and function values (2, #1503). Those three fixes
would clear a third of it. The next-largest cluster is struct-by-value
lowering (`21_ls`, `69_result_string`, #1505/#1515).

## Tickets filed by this survey

**ritz1 root causes:** #1451 (ptr scaling, P80), #1452 (trailing comma, P72),
#1453 (cast-inferred `let`, P68), #1454 (block match arm, P66), #1455 (inline
asm, P40), #1456 (`async fn`, P45). Updated: #1362.

**Missing examples** (each must be built by both compilers under `test.sh`):
#1457 buf, #1458 hashmap/hash/eq, #1459 json, #1460 option, #1461 process,
#1462 os.env, #1463 heap/timer/elf/meta, #1464 lang, #1465 the async stack.

**Idiomatic API (children of #1347, bottom-up ladder):** #1469 io → #1472 str
→ #1474 string → #1476/#1477 fs → #1478 buf → #1480 env → #1481 process →
#1482 json → #1483 net.

**Closed as stale** (no longer reproduce on main): #1361, #1367.

Deduplicated against the concurrent packages survey (#1450): #1466–#1468,
#1470, #1471, #1473, #1475, #1479 and #1500–#1532 are theirs and are not
re-filed here. The stage 3 allowlist above maps entirely onto those plus
#1368, #1375 and #1456.
