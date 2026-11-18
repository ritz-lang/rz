# ritz1 package parity

M1.1 (#1828) requires that every workspace package that builds under ritz0
builds under `--compiler ritz1` with the same test results. This page records
that measurement package by package, so it can be repeated and compared.
Each difference maps to at least one open AGAST ticket.

Survey ticket: #3965.

## Latest measurement

- **Date:** 2026-11-18
- **main:** `472d77bb` (ritz-task-3768, sema_bool_kind bk-gaps 154 -> 42)
- **Host:** huburght, room cgroup MemoryHigh 10G / MemoryMax 12G. No result
  below is limited by the room's memory cap: the largest peak was 4.0 GB, in
  spire's `test` run under ritz1 (see #3952).

**Summary:** 28 packages. All 28 build and pass their tests under ritz0.
Under ritz1, **20 match ritz0 and 8 differ**: 5 fail to build (angelo, harland,
lexis, prism, tempest), and 3 build but fail tests (nexus, spire, valet).
ritz1_selfhosted fails in exactly the same packages, with the same diagnostics
and test counts as ritz1.

## Table

Build is `./rz build <pkg>`. Test is `./rz test <pkg>`: the files
that compiled and passed out of the total, then the tests that passed. "no tests" means the
package has no test files and the command exits 0. A test that is "FAIL (build)" never
ran because its package didn't build, so its tests are **unmeasured** and further
causes may be hidden behind the build failure.

| package | ritz0 build | ritz0 test | ritz1 build | ritz1 test | ritz1_selfhosted build | ritz1_selfhosted test | blocking tickets |
|---|---|---|---|---|---|---|---|
| angelo | ok | 20/20 files, 106 tests | FAIL | FAIL (build) | FAIL | FAIL (build) | #3972 #3973 #3974 #3979 #3421 #3699 #3982 |
| cryptosec | ok | 34/34, 906 | ok | 34/34, 906 | ok | 34/34, 906 | |
| goliath | ok | 5/5, 46 | ok | 5/5, 46 | ok | 5/5, 46 | |
| harland | ok | 1/1, 8 | FAIL | FAIL (build) | FAIL | FAIL (build) | #3977 (then #1848) |
| http | ok | 23/23, 595 | ok | 23/23, 595 | ok | 23/23, 595 | |
| indium | ok | no tests | ok | no tests | ok | no tests | |
| iris | ok | 3/3, 30 | ok | 3/3, 30 | ok | 3/3, 30 | |
| lexis | ok | 4/4, 31 | FAIL | FAIL (build) | FAIL | FAIL (build) | #3972 |
| mausoleum | ok | 25/25, 477 | ok | 25/25, 477 | ok | 25/25, 477 | |
| nexus | ok | 13/13, 170 | ok | **12/13, 127** | ok | **12/13, 127** | #3980 |
| prism | ok | 13/13, 110 | FAIL | FAIL (build) | FAIL | FAIL (build) | #3973 #3975 |
| ritz | ok | no tests | ok | no tests | ok | no tests | |
| ritz-lsp | ok | no tests | ok | no tests | ok | no tests | |
| ritz-stats | ok | no tests | ok | no tests | ok | no tests | |
| ritzlib-tests | ok | 36/36, 560 | ok | 36/36, 560 | ok | 36/36, 560 | |
| ritzunit | ok | 9/9, 60 | ok | 9/9, 60 | ok | 9/9, 60 | |
| inventory | ok | 1/1, 24 | ok | 1/1, 24 | ok | 1/1, 24 | |
| rzrz | ok | 1/1, 7 | ok | 1/1, 7 | ok | 1/1, 7 | |
| rzsh | ok | 6/6, 43 | ok | 6/6, 43 | ok | 6/6, 43 | |
| s2_module_init | ok | no tests | ok | no tests | ok | no tests | |
| s3_param_shadow | ok | no tests | ok | no tests | ok | no tests | |
| sage | ok | 2/2, 73 | ok | 2/2, 73 | ok | 2/2, 73 | |
| spire | ok | 18/18, 296 | ok | **13/18, 208** | ok | **13/18, 208** | #3952 |
| squeeze | ok | 15/15, 199 | ok | 15/15, 199 | ok | 15/15, 199 | |
| tempest | ok | 2/2, 10 | FAIL | FAIL (build) | FAIL | FAIL (build) | #1295 |
| tome | ok | 10/10, 139 | ok | 10/10, 139 | ok | 10/10, 139 | |
| valet | ok | 15/15, 232 | ok | **14/15, 209** | ok | **14/15, 209** | #3981 |
| zeus | ok | 17/17, 195 | ok | 17/17, 195 | ok | 17/17, 195 | |

## Causes

Each row is one cause with one ticket, with a minimal repro in the ticket.
"ritz0 lenient" means ritz1 is right: the package source has a bug that ritz0
fails to refuse.

| ticket | cause | packages (site) | status at measurement |
|---|---|---|---|
| #3972 | An element reached through a field index (`let e = @t.es[i]` of a `Vec<T>` field, `s.rs[i].k` of a `*T` field) gives an unlocated "unhandled EXPR_MEMBER" or "cannot take address" | lexis (lexis.ritz:144, rule, selector_map, main), angelo (raster/fill.ritz:164) | new |
| #3973 | Sema leaves a `for x in v` binding over a `Vec<T>` untyped, so `x.f` / `x.m()` fails as a bool ("ritz1 cannot tell that it is") | prism (compositor/mod.ritz:287), angelo (loader/ttf.ritz:64) | new |
| #3974 | Sema leaves `let x = f()?` untyped, so `x.m()` fails as a bool | angelo (loader/ttf.ritz:187) | new |
| #3975 | Sema leaves `self.f.m()` untyped inside a `self:&` method, so it fails as a bool | prism (compositor/mod.ritz:298) | new |
| #3977 | Sema leaves a field of a global `[N]S` element (`gs[i].in_use`) untyped, so it fails as a bool | harland (kernel/src/cap/table.ritz:76, :111) | new; #1848 now depends on it |
| #3979 | A generic instance named only in a fn-pointer parameter's type (`fn(u16) -> Option<O>`) is never declared, so clang reports "Cannot allocate unsized type" | angelo (loader/glyf.ritz:310) | new |
| #3980 | A `match` statement arm whose body is an `if`/`else` statement is checked as an expression: "an `if` expression arm does not end in a value" | nexus (test/test_repos.ritz:885) | new |
| #3981 | ritz0 lenient: `sizeof(T)` skips the #3891 import-visibility check | valet (test/test_tls.ritz:393) | new |
| #3982 | ritz0 lenient: a field of an `Option.unwrap()` binding, passed by value into an `@T` parameter, isn't refused | angelo (tests.ritz:593) | new |
| #3952 | A dead first-class `load` of a large sret struct (`let r: Request = request_new()`) drives `clang -O2` past build.py's 4 GiB bound: `LLVM ERROR: out of memory` | spire (5 test files) | existing; root cause added |
| #3421 | An `if`/`else` fn tail with float arms emits `phi i64` over doubles | angelo (cache.ritz:156 `hit_rate`) | existing |
| #3699 | `s.as_bytes()` on a `let` StrView: "no method `as_bytes` on `StrView`" | angelo (shaper/simple.ritz:173) | existing |
| #1295 | Multi-field tuple variants and patterns (`SetViewport(w, h)`) don't parse: "unexpected ','" | tempest (lib/tab_renderer.ritz:119, :196) | existing |

Also found, but blocking no package: #3983. ritz1 accepts a `self:&` method
call on a field of a shared `@T` parameter, which ritz0 refuses.

### Notes

- **harland:** `cap/table.ritz` is the only file ritz1 fails on, and the
  `bootx64` target builds. #1848's older blockers (inline asm #1455, `pub var`
  #1508, `pub import` #1523) no longer fire. indium builds under both ritz1
  compilers. What comes after #3977 (clang, link, the QEMU boot) is unmeasured.
- **spire:** this is not the room's memory cap. ritz1's spire build passes but
  peaks at 3.37 GB, against 78 MB under ritz0, probably from the same loads as
  #3952.
- **lexis:** the ritz1 build peaks at 812 MB, against 29 MB under ritz0. It
  doesn't fail, and the cause hasn't been investigated.
- **Hidden causes:** the five packages that fail to build under ritz1 never
  ran their tests under it. Re-measure them as their build tickets close.

## How to re-measure

Run each package on its own, not as one `--all` run: memory and failures stay
per package, and the logs show which package caused what. Set TMPDIR to disk,
not `/tmp`. Run at most 3–4 packages at a time, and pause when load1 > 25.

```bash
make -C projects/ritz/ritz1 bootstrap          # builds ritz1 and ritz1_selfhosted
export TMPDIR=~/.cache/parity/tmp; mkdir -p "$TMPDIR"
for c in ritz0 ritz1 ritz1_selfhosted; do
  for p in $(./rz list | awk 'NF && $2 ~ /^[0-9]/ {print $1}'); do
    /usr/bin/time -v ./rz build "$p" --compiler "$c" > "logs/$c/$p.build.log" 2>&1
    /usr/bin/time -v ./rz test  "$p" --compiler "$c" > "logs/$c/$p.test.log"  2>&1
  done
done
```

`./rz build <name>` can't find nested packages by name; pass them by path:
`bench/regressions/2026-05-04/s2_module_init`, `.../s3_param_shadow`,
`projects/larb/tools/ritz-stats`, `projects/ritz/ritzlib/tests`
(ritzlib-tests) and `projects/ritzunit/inventory`. Each test log's
`Σ` line gives the counts. To check whether an "out of memory" failure is a ritz1
bug or a memory cap, compare `Maximum resident set size` with ritz0's for the same
package. Also check whether the failure comes from build.py's own `clang -c` bound
(`RITZ_CLANG_OBJ_MEM_MB`, 4096 MiB), which the test log names.
