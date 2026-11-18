# Ticket scrub, 2026-11-18 (AGAST #3967)

Scrub of every open ticket in AGAST project 1, against origin/main
`472d77bb`. Asked for by Aaron. No compiler work: evidence is AGAST,
`git grep`/`git log`, and a few repros with ritz0 (the only compiler built on
the scrub host; ritz1-only claims are marked as unverified).

Method: one read-only reviewer per milestone (#1828, #1829, #1830/#1812/#1816,
#1831/#3787, #1833, #47, #48, #49-#52, Triage #3788) proposed actions with
evidence. Every closing SHA was checked to be an ancestor of origin/main, and
every AGAST change was applied by the scrub room. Closed tickets were claimed as
`ritz-scrub`, and their results hold the evidence. Nothing in `executing` was
touched, nor were the 8 root tickets or the milestones.

## Counts

| | open | pending | ready | executing | failed | blocked |
|---|---|---|---|---|---|---|
| before | 328 | 269 | 39 | 17 | 2 | 1 |
| after | 304 | 126 | 159 | 18 | 0 | 1 |

"Open" = not completed. `executing` includes this scrub (#3967) and rooms that
claimed tickets while the scrub ran. The orphan check
(`parent_task_id=0`, not completed) is 8 before and 8 after.

Summary: **33 closed** (21 already fixed, 6 duplicate,
4 obsolete, 2 folded), **134 pending → ready**, **10 ready →
pending** (blocked, or awaiting a decision), **16 dependency edges added**,
**17 tickets flagged `needs_decision`**, **9 descriptions updated** (fold/dup
targets, narrowed tickets), **16 decisions wanted** (below).

Other rooms kept working during the scrub: project 1 grew from 1,661 to 1,678
tickets (17 filed), and rooms completed 8 tickets besides the 33 closed here.
So 328 → 304 is the net change, not the scrub's alone.

## Closed

| Ticket | Action | Evidence |
|---|---|---|
| #104 | already fixed (was `failed`) | ritz1 has `?` (#134) and aggregate Result payloads (#133); test_issue_try_vec_payload_call passes in the matrix with no EXPECTED_FAILURES entry |
| #191 | already fixed | ritz1_selfhosted phantom `%NFA`: arena truncation removed by #1267 (9aab44f); hard-coded NFA deleted by c3aa4094 (#1440); Stage 5 asserts the fixed point |
| #1298 | already fixed | binaries go to build/<profile>/, root links gitignored; tools/test_bin_links_ignored.py (3baa06e6, #3652) |
| #1339 | obsolete | `[ci.known_failing.build]` is empty (angelo #1321, tempest #3609, lexis #3689); leftovers tracked by #3610 |
| #1342 | already fixed | 71c0458b (#1371): the matrix discovers every ritz0/test/*.ritz, with a floor |
| #1346 | already fixed | ritzlib/tests green and train-gated (bdb10eaa #1686, 1ea90d67, f5b2005d #3909) |
| #1379 | already fixed | fbc49884 (#2018); spire 18/18 files in test-all |
| #1380 | already fixed | 3d8acb8f (#1914): test_hpack 1.4 s; http in test-all |
| #1381 | already fixed | 0879eb0a (#1696): prism tests green |
| #1389 | duplicate of #1823 | generic-param binding landed in 0011dcbe; the re-measure and default flip are #1823's acceptance |
| #1391 | already fixed | 10e7b843 (#2181): harness blanks `main` and keeps the test file's real name |
| #1401 | already fixed | c96dfdb4 (#1382): binary provenance manifest replaces the mtime skip |
| #1402 | already fixed | c9fd4003 (#1485): RITZ1_TESTS deleted, `make ritz1` builds ritz1; tools/test_ritz1_target.py |
| #1404 | obsolete | projects/nexus/wiki deleted in 41cb198c (#1875) |
| #1405 | folded into #3610 | docs/archive excluded (d63c0683); 73_heap/74_autodrop have ritz.toml; only 51_iovec left, moved to #3610 |
| #1407 | already fixed | cde93ec4 (#1869): the diagnostic says `[[test]]` (emitter_llvmlite.py:8728) |
| #1447 | already fixed | 040cd4c2 (#2020) + d90b43e8 (#3086): skip keyed on output path, mode and ritz0's identity |
| #1465 | already fixed (was `ready`) | cc4d6a8e (#1855): one async runtime; the loose async_echo_server.ritz is already in #3610 |
| #1486 | already fixed (was `ready`) | d63c0683 (#1383): members = `projects/**`, `[workspace.exclude]` names each gate |
| #2535 | duplicate of #2534 (was `failed`) | filed by mistake, no work done; #2534 merged as 00703d20 |
| #2760 | already fixed | ritz0 repro on 472d77bb: `p.b` through `*Big` (2 KiB struct) is GEP + `load i32`, no `%Big` alloca/load/memcpy (3d8acb8f, #1914) |
| #3018 | already fixed | 23cae36b (#1876): "a string pattern needs a StrView scrutinee", pinned by test_match_strview.py:89 |
| #3023 | duplicate of #3727 | same async_transform_v2 root cause; its remaining rows copied into #3727 |
| #3240 | obsolete (LARB R66), folded into #3497 | R66: methods come from impl blocks, the UFCS tables go; the strview_* fallback deletion was copied into #3497 |
| #3341 | duplicate of #3617 | same fix (specialize generic impl methods on use); the Cell<T>.wrap repro was copied into #3617 |
| #3422 | obsolete | 4a350d4c (#3450) deleted symbol_table.py / TestStubIREquivalence |
| #3581 | already fixed | 5e2da249 (#1740): place before value; test_assign_place_order.py `index_mut_element` |
| #3603 | already fixed | eadcb5bf (#3397): the `startswith('syscall')` rule is gone from type_checker.py |
| #3611 | already fixed | 672f61f0 (#1904) deleted valet lib/tls/ |
| #3646 | folded into #3615 | same test.sh lines; the pipefail/EXIT_SETUP details were copied into #3615 |
| #3672 | duplicate of #3479 | LARB R60 (confirmed) asks for the §4.3 text; ritz1's accept list was copied into #3479 |
| #3758 | already fixed | 7bb41ee8 (#3759, "covers #3758"): rows in test_match_pass_arm_value.py |
| #3890 | duplicate of #3891 | 09f1b1be: a plain `import` is private on all 3 compilers |

## Updated, folded into, narrowed

| Ticket | Change | Why |
|---|---|---|
| #3727 | description + ready | took #3023's rows (`let y = x*2` before an await; 54_async_fs early return) |
| #3617 | description + ready | took #3341's Cell<T>.wrap repro and the ritz1 receiver-typing note |
| #3479 | description + ready | took #3672's ritz1 accept list and the enum-field question; dep #3448 is complete |
| #3497 | description | took #3240's strview_* fallback item |
| #3615 | description + ready | took #3646's pipefail/EXIT_SETUP details |
| #3610 | description (+ ready) | took #1405's 51_iovec requirement; valet/tls and negated_range rows marked moot |
| #3694 | description + ready | blocker #3685 complete; 3 more gated scripts on fixed ports (test_framing.sh, test_large_echo.sh, test_static_conn.sh) |
| #3428 | narrowed to ritz1 + ready | ritz0 repro on 472d77bb refuses it: `6:24: field `b` of `Outer` is `Box2$u8`, not `Box2$i64`` |
| #1387 | narrowed to defect 2, `needs_decision` | ritz0 repro refuses the String-into-StrView call at 5:22; the pointer bitcast left in `_convert_type` waits on the #3684 ruling |

## Dependencies added

| Ticket | Now depends on | Why |
|---|---|---|
| #73 | #1889, #1817 | its own text: "do it as a step after #1889/#1817"; status ready → pending |
| #1817 | #1889 | its text names "the type-table ticket", now #1889 |
| #3477 | #3592 | #3592's migration must land first or the bootstrap breaks |
| #3496 | #3614, #3617 | named in #3614/#3617's titles ("blocks R66 #3496/#3497") |
| #3497 | #3614, #3617 | same |
| #3630 | #1850 | MSI-X mode follows the polled NVMe driver (#1850: "MSI-X later, sibling ticket") |
| #3673 | #3479 | waits on the §4.3 const-field rule (was #3672) |
| #3801 | #1347 | its text: sweep once the standard is written |
| #3892, #3893 | #3510 | #3510 follow-ups; #3510 hasn't landed (only on its branch) |
| #3943 | #3810 | its text: merge after #3810 |
| #3948 | #3810, #3510 | its text: re-measure after both |

## Status fixes, ready → pending

| Ticket | Why |
|---|---|
| #201, #203, #204 | `ready` but blocked by open #200 / #202, #1347 / #203 |
| #1854 | `ready` but blocked by #2159 (and the Drop epic's children) |
| #73 | now depends on #1889/#1817 (above) |
| #1291, #1626, #3793, #200, #205 | awaiting a decision (below); not workable as written |

## Pending → ready

**M1.1 #1828 (ritz1 parity)**

| Ticket | Still open because |
|---|---|
| #3309 | strict xfail still at ritz0/test_generic_static_method.py:126 |
| #3348 | test_call_arity_and_type.py:125,154 still pins the nameless message |
| #3030 | TUPLE_ALIAS xfail still at test_ownership_free_count.py:261 |
| #3031 | TUPLE_TEMP_GAP xfail still at test_ownership_free_count.py:262 |
| #3033 | still cited as xfail at test_ownership_free_count.py:2646,2668,2677,3059 |
| #3024 | TUPLE_PTR_ELEM xfail still at test_ownership_free_count.py:260 |
| #1295 | test_issue_struct_enum_variants still in _RITZ1_TWINS (run_regression_matrix.py:75); N-ary tuple variants missing from ritz1.grammar |
| #3028 | no landing commit; ritz1 behaviour unverified (see notes) |
| #3042 | no landing commit |
| #3421 | still a blocker of prism tests (d35f8c76, #3620) |
| #3271 | no landing commit |
| #3757 | `untyped_arith` row still refused (test_array_elem_store_drop.py) |
| #3932 | check_doc_examples.py:150-151,183-187 still list rows for it |
| #3933 | check_doc_examples.py:177-178 still lists rows for it |
| #3934 | check_doc_examples.py:180-181 still lists rows for it |
| #3625 | no landing commit (priority 10) |
| #3635 | no landing commit |

**M1.2 #1829 (one language)**

| Ticket | Still open because |
|---|---|
| #3434 | ritz1 ownership.ritz:2864 never checks the field path's moved bit |
| #3399 | let_method_recv_type (let_check.ritz:539-565) still types only IDENT/MEMBER/const INDEX |
| #3019 | no #2940/id(p) rows in ritz0 tests |
| #3800 | no fix, no other ticket |
| #3585 | no `available_externally` in either compiler |
| #3562 | ritz0 `_emit_index` still evaluates index before base |
| #3582 | ritz0 `_emit_lvalue_addr` Index arm still index-first (pair with #3583) |
| #3583 | `_emit_assign_expr_core` has no drop (emitter_llvmlite.py:11430) |
| #3571 | only iris lib/layout/block.ritz:15-17 left |
| #3592 | ritz1 emitter.ritz:3632 and nexus page_cache.ritz:44 still fill field by field; #3477 now depends on it |
| #3614 | ritzlib/tests/test_string_methods.ritz:268-269 still calls `s.drop()`; option (a) needs no ruling |
| #3468 | dep #3448 done (9051cb14); no R55 code on main |
| #3474 | #3448 done; skip citing #2179 still at emitter_llvmlite.py:4785,4817 |
| #3485 | #3448 done; no `+%` in ritz0 |
| #3491 | #3448 and #3490 (da1532c6) done |
| #3493 | #3448 done; no R65 messages on main |
| #3499 | #3448 and #3498 (10e92663) done |
| #3586 | ritz0 `_emit_lvalue_addr` has no Cast arm (:11088) |
| #1445 | `_arith_context_nodes` still walks only BinOp/UnaryOp |
| #3656 | no SIMD-vector row in test_byval_exact_size.py |
| #2847 | ritz1 struct_index.ritz:65,79 still skip `type_params` |
| #2854 | no `tail_temp` row anywhere |
| #3591 | no `strview_span_copied_local` row |
| #3836 | ritz0 emitter_llvmlite.py:9275 still `fcmp_ordered('!=')` |
| #3690 | `_fn_type_byval` adds byval with no size check; dep #3692 done |
| #3699 | ritz0 builtin at emitter_llvmlite.py:13532, no `fn as_bytes` in ritzlib; R66 says impl StrView |
| #3907 | ritz1 import_vis.ritz:20 still records no file for enums/aliases |
| #1444 | `_check_implicit_narrowing` only at let/var; LANGUAGE_SPEC.md:2402-2404 cites #1444 |

**M1.3 #1830 / #1812 / #1816 (structure)**

| Ticket | Still open because |
|---|---|
| #3010 | bool_reg_is_i1 (emitter_core.ritz:6561) still returns 0 |
| #1688 | unannotated-local gap still pinned (test_ritz1_implicit_narrowing.py:131) |
| #1695 | 11 literal allocation sizes left (ast_helpers.ritz, fn_cache.ritz:441) |
| #1819 | dep #1813 done; STMT_*_ASSIGN kinds still live |
| #1826 | dep #1822 done; emitter_llvmlite.py still one file |
| #1889 | dep #1814 done; ladders still at emitter_core.ritz:2360-2380 |
| #3522 | monomorph.py 2,566 lines, type_checker.py 2,334 (after #3553/#3554) |
| #3523 | emitter_llvmlite.py:17674 still calls monomorphize |
| #3561 | guard still at emitter.ritz:53-54 |
| #3621 | 18 `eprints_cstr(c"error: ")` sites; emit_ir_error takes no span |
| #3887 | deps #3886/#3888 done; lexer_nfa.ritz still present (needs a quiet window) |
| #3903 | allowlist still has no module separators (kept separate from #3904) |
| #3904 | sema_walk.ritz:20-49 still one unsorted import block |
| #3915 | holds #3905/#3901/#3898 done (needs a quiet window) |
| #3553 | move_checker.py:209-315 `_type_of_*` still present |
| #3554 | monomorph.py `_infer_value_type`/`_infer_method_call_type` still present |
| #3555 | emitter_llvmlite.py `_infer_*` still present |
| #3593 | #1823 child; no checker commit since 9051cb14 |
| #3594 | same |
| #3595 | same |
| #3596 | same |
| #3597 | same |
| #3598 | same |
| #3599 | same |
| #3600 | same |
| #3601 | same |
| #3602 | type_checker.py:499 still uses the flat variant_to_enum map |
| #3604 | 8727ef22 (#3607) covers binary-op literals, not argument slots |
| #3605 | type_checker.py:1397 IdentPattern still binds `None` as a local |
| #3608 | harland blk.ritz/shm.ritz still call `kfree(dev)` uncast |

**M1.4 #1831 / #3787 (ritz1 default; ritz0-only bucket)**

| Ticket | Still open because |
|---|---|
| #1390 | 147 `raise ValueError(` left in emitter_llvmlite.py (side question in Decisions) |
| #3051 | `_emit_global_var` lowers only StringLit.as_ptr; test_ritz1_global_var_init.py:312 still ritz1-only |
| #3146 | `_unsliceable` still calls every NamedType "a struct" |
| #3588 | precondition #3386 landed (2226f3db); closure wording still at emitter_llvmlite.py:3935,3940,4277 |
| #3404 | emitter_llvmlite.py:12241 still raises "Cannot access field on non-struct type" |
| #3424 | no fix commit |
| #3022 | still in run_regression_matrix.py:89 EXPECTED_FAILURES |
| #3128 | ritz0 still raises UnknownFunction("Unknown function: Full") |
| #3066 | workaround space still at test_bare_place_borrow.py:162,166 |
| #3727 | took #3023's rows (see Updated) |
| #3435 | ritz0 repro on 472d77bb: `-x` folded into the `let`, "Unknown identifier: x" |
| #3433 | ritz0 repro on 472d77bb: `var g: [2][1]S = [ [S{x:1}; 1]; 2]` with Drop S compiles |

**1833 (tooling)**

| Ticket | Still open because |
|---|---|
| #1386 | step 1 done (34eb00a9); step 2 (stray tests/*.ritz is an error) left |
| #1341 | regression.sh:1522 skip and :1753 no-denominator still there |
| #3797 | 3 skipifs still at the cited lines |
| #3632 | build.py 3,477 lines, no pipeline/testrun/cli split |
| #3807 | test_cas_harness_and_inprocess_units.py:335 still @unit |
| #2842 | build.py:668 and :803 both parse the entry file |
| #2210 | no orphan/uncompiled-module report |
| #3831 | cmd_clean still leaves ROOT/build/linked |
| #3832 | deps #3816 (0aee87a1), #1873 done; prism test_damage.ritz still `t.regions[0]` |
| #3610 | still present (see Updated) |
| #3624 | ci_local.py:438 still treats any rc 3 as setup error |
| #3894 | dep #1837 done; manifest.py still lists `sources` three times |
| #2113 | ritz1 main.ritz:819 still cites it (caching; see notes) |
| #2252 | cmd_run still writes the shared ROOT/build/<stem> |
| #2300 | still no lock file (lock file or drift step: ticket allows either) |
| #3566 | test_row_table.py and test_table_rows.py both exist |
| #3623 | likely_tests.py:48 MAX_FILES = 60 |

**#47 (ritzlib)**

| Ticket | Still open because |
|---|---|
| #1490 | deps #1487/#1488/#1497/#1498 done; tier2 still imports ritzlib.args |
| #1491 | same; 21_ls..30_find |
| #1492 | same; 31_env..40_watch |
| #1493 | same; 41_calc..49_ritzgen |
| #1494 | same; ritzunit runner.ritz |
| #1495 | same; valet main.ritz |
| #3881 | dep #3880 done; mausoleum client.ritz:144,235 still `host: *u8` |
| #3916 | ritzlib/heap.ritz still on main |
| #3917 | six response_*_iov builders have only test callers |
| #1957 | `% 10` loops still in rzsh, zeus, mausoleum, prism, harland, boot |
| #1958 | ritz-lsp transport.ritz:77 parses Content-Length by hand |
| #3590 | spire test_lib_all.ritz:9-10 still leaves the module out (check after 09f1b1be first) |
| #3940 | rzsh main.ritz:120-304 still over threshold |

**#48 (harland)**

| Ticket | Still open because |
|---|---|
| #2755 | dep #2754 done (5f2316c8); no user-mode kill path yet |
| #2762 | process.ritz:132 sets g_child_pid = 2, failure paths don't reset it |
| #2786 | fd_dup still re-exported, no syscall calls it |
| #2761 | workaround comment still in process.ritz |
| #1443 | code fix on main (d190c98b); the boot test is left |
| #3529 | rzsh common.ritz:19 MAX_ARGS = 32 |
| #3552 | two TODOs still in sys_mmap_impl |
| #3282 | harland ritz.toml:62 still `sources = ["tests"]` |
| #3577 | still as described |
| #3576 | still as described |
| #3615 | took #3646 (see Updated) |
| #1919 | ritz1 parse_attr still single-name only |
| #3633 | fn_copy_instance_attrs still leaves out ATTR_NAKED |

**Parked #49-#52**

| Ticket | Still open because |
|---|---|
| #3694 | blocker #3685 done; see Updated |

**Other (dup/fold targets)**

| Ticket | Still open because |
|---|---|
| #3617 | took #3341 (see Updated) |
| #3479 | took #3672 (see Updated) |
| #3428 | narrowed to ritz1 (see Updated) |

Skipped while readying: #3953 and #3949 (rooms claimed them mid-scrub), #1848 (now blocked by the new #3977).

## Not changed, with notes

- **Executing, untouched:** every ticket a room owns. #1455 (ritz1 inline asm
  in ritzlib/testing.ritz, proposed as already fixed by 0568dff7/bb6af962) was
  claimed by room ritz-task-1455 while the scrub ran, so it was left alone.
- **#1844** (harland main.ritz split) is `ready` but is only a tracker now:
  #2747-#2754, #2756 and #2757 landed, and only #2755 is open. Nine tickets are
  blocked on #1844 only so their line numbers get re-checked after the split,
  and the split has landed: #1877, #1878, #1882, #1883, #1884, #1886, #1887,
  #1888, and #1881 (which also waits on #1857). Recommend removing those #1844
  edges (rz's call) or closing #1844 once #2755 lands.
- **#3556** (remove `--check-types`) repeats #1823's type half. Give it deps on
  #3593-#3608, or fold one into the other.
- **#3926** is `ready` while blocked by #3506 (executing; already on main as
  27a3bf6e). It clears when rz completes #3506; #3507 becomes ready then too.
- **Stale descriptions to trim** (left as is, still valid):
  - #1859: dead modules, prose and the liveness gate were done by #3913.
  - #1858: step 4 landed (#3439/#3466); trait bounds were ruled by R55.
  - #2223: tempest and lexis build now; the docs half is still live.
  - #3572: only prism src/api/mod.ritz:21 is left.
  - #3612: tls.ritz lines moved to 1097/1099/1308/1309.
  - #1867: spire/tome logs and valet lib/tls/ are gone.
  - #1386: only step 2 (stray `tests/*.ritz` is an error) is left.
  - #1326: the ritz1 shims are gone (eadcb5bf).
  - #1688: the check runs on Sema now (24a81274).
  - #1819: generator.py and ritz.grammar are gone.
  - #3399: let_method_recv_type moved to let_check.ritz:539-565.
  - #3571: only iris lib/layout/block.ritz is left.
  - #1919: the stale LANGUAGE_SPEC.md:5739 "ritz1 does not implement [[naked]]".
- **Overlaps to keep in one place:**
  - The tome server_blocking deletion is in both #1867 and #3070.
  - harland/user and the USER_DIR step are in both #1871 and #1886; leave them
    to #1871 (#1886's arch/x86_64/syscall.ritz is already gone).
  - #3629 overlaps #1882 (per-process table) and #1883 (timer).
  - #3031 and #3033 (ritz1 tuple-element drops, ownership.ritz) suit one room.
  - #1490-#1495 (args → argspec) suit one room.
- **Parent mismatches:**
  - #73 is still under #46; its text says #1812.
  - #3309, #3042 and #3421 say "Parent: #1829" but sit under #1828.
  - #2113 (caching) sits under #1833; #1801 owns caching.
  - #202 has project_id null.
- **#1853**: dependency #3405 is complete (dd76c65d), but the inventory went to
  projects/harland/docs/hardware/thinkpad-p16-gen2/, not the
  `docs/targets/<machine>.md` path its acceptance names.
- **#1834**: add check_doc_examples' KNOWN_FAILURES (#3963) to its allowlist
  migration.
- **Unverified (needs a built ritz1):**
  - #3028 (`match` arm `t` on a Drop ref, ritz1 "cannot move out of a
    reference") may already be fixed by #2046's take_match_wants_value. It was
    readied anyway; check it first.
  - #3836 ritz1 half.
  - #1848 is the harland/indium `--compiler ritz1` integration run.

## Decisions wanted

Each of these is flagged `needs_decision` in AGAST. None was decided here.

| Ticket | Question | For |
|---|---|---|
| #1756 | lexical scope vs rejecting shadowing | already decided by Aaron 2026-11-18 ("no shadowing"); executing, listed for completeness |
| #3924 | which column a `let` `@&` borrow error reports: the `@` (ritz1) or its operand (ritz0, 2 columns on) | LARB |
| #3968 | is the trailing value of an `if`/`while`/`for` statement body discarded (whole-array, `[[must_use]]`)? | LARB |
| #3796 | is a `[[must_use]]` call as a statement-`match`/`if` arm value discarded? Rule together with #3968 | LARB |
| #3802 | is f64 → f32 without `as` an error (literals exempt)? §7.5 covers integers only; #3607's text assumes it is | LARB |
| #3684 | is a `*[4]i32` value into a `*[3]i32` slot (or another pointee type) an error? Spec §734-735 says pointers "aren't judged"; #1387's remaining bitcast defect hangs on the same answer | LARB |
| #3012 | struct-to-struct `as`: refuse on all 3 compilers, or a layout-checked copy? | LARB |
| #3584 | `_` digit separators (`1_000`, `0xFFFF_FFFF`): spec them (and add to the ritz1 lexer) or remove from ritz0? | LARB |
| #3959 | is `*mut T` vs `*T` part of a generic argument's identity (`Vec<*mut i32>` ≠ `Vec<*i32>`)? | LARB |
| #3673 / #3479 | may a const struct field be a unit enum variant? (R60 allows array/struct literals; enums are unnamed) | LARB |
| #1291 | nested variant patterns: spec §8 says a variant pattern is a binding or `_`. Close as out of spec, or make it a spec + both-compilers feature under M1.2? | LARB / Aaron |
| #1626 | `[[cfg(...)]]` (LARB-0013 draft): implement it (with `not(...)`), or rewrite test_level42 to `[[target_os]]` and drop test_cfg_not? | LARB |
| #3728 | async poll contract: `Poll<T>` enum, a ready flag in the future, or an out-param (today i32 with -1 = Pending) | LARB |
| #3793 | how a program keeps a future and hands it to an executor without naming `f_Future`/`f_poll` (blocks #3606) | LARB, then Aaron if it adds syntax |
| #3251 | runtime polymorphism (fat pointer / fn-pointer struct / bounds only); R55 is confirmed, so it can be ruled now | LARB, then Aaron |
| #198 (#200, #205) | the v1 main ABI + Display chain: 8bfa9dd6 (#3913) deleted entry.ritz and the start shims it was built on. Redo it, or close the chain? | Aaron |
| #1390 (side question) | is a free `T` in an `impl Box<T>` written without `<T>` an error on both compilers (LARB review/5 ritz0.md:75)? The ValueError conversion itself was readied | LARB |
