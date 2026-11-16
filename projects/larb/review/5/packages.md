# LARB v5 Review: all other packages (remaining packages + infrastructure)

**Reviewed:** 2026-11-16 · **Baseline:** review/4 (2026-10-25) · **Status:** Part 1 (remaining packages) NEEDS WORK · Part 2 (infrastructure) NEEDS WORK (was CRITICAL)
**Metrics:** [metrics-packages.md](metrics-packages.md). Same tool, same paths and `--top 15` as review/4. The "then" column was produced by the same script over `git archive 887d91ad` (the review/4 commit), so both sides are measured the same way.
**Method:** `INSTRUCTIONS_v4.md`, read-only, on main @ 6f245b93. Nothing was built or run. Statuses come from reading the code, not from ticket state; AGAST was not consulted, so whether a ticket is open or closed is not checked here.
**SLOC note:** the review/4 infra table gives total line counts (for example "cryptosec 27k"). This file uses metric SLOC throughout.

---

# Part 1: remaining packages (ritzunit, ritz-lsp, rzrz, ritzutils, rzsh, indium, spectree, nexus, lexis, prism, angelo, angelo-simple, sage, iris, tempest)

**Status: NEEDS WORK**

## Summary

Both Criticals are fixed:
- **C1:** ritzunit is now the `main` of every test binary on ritz0 and ritz1. The compiler emits a test table, and ritzunit has `-j N`, memfd capture, a wrap-safe exit code and valid JSON.
- **C2:** nexus builds its responses in `String`, and slugs are validated against `[a-z0-9-]`.

The developer-tool false successes (M8) and the assertion-library sprawl (M4) are also resolved.

What hasn't moved:
- **The harland userland** is still in two copies, with four `sys_open` definitions (M7).
- **The parked browser-stack complexity** is unchanged, line for line (M9).
- **The cleanup sweep** has done one thing: the dev key is no longer tracked. Transcripts, assets and broken manifests are all still there (M10).

nexus's dead second architecture has **regressed**. It was made to compile, and it gained about 1.5k SLOC of tests, but production still never imports it. That is dead code with green tests (M11).

New code repeats v4 anti-patterns: rzsh's new shell parser uses fixed global tables, i32 kind codes and numeric character codes (F1).

The status stays NEEDS WORK because of M11, M7 and F1.

## Against review/4

| id | title | v4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| C1 | Four test harnesses; the gate uses no Ritz one | Critical | **FIXED** | `ritz0/test_runner.py:686-700`: ritzunit `bin_main.ritz` is the test binary's `main`. `ritzunit/src/runner.ritz:47` reads `__ritz_test_table`. `build.py:522-534` handles `--test-table` for ritz1 (c5e31714). `-j N` is at `runner.ritz:182` (d2686833). `ritzlib/testing.ritz` is deleted. `git grep 'run_batch_tests\|emit_test_main\|__init_tests\|run_tests_array'` is empty. | #1868 |
| C2 | nexus stack overflow escaping page content | Critical | **FIXED** | `nexus/src/html_writer.ritz` writes into `String`. No `[16384]u8` body buffers remain. `slug.ritz:48-62` validates `[a-z0-9-]{1,128}`. Content reads are capped at `MAX_CONTENT_LEN` (`store.ritz:359`). Fixed by a038bc34. | #1870 |
| M1 | ritzunit discovers tests by `test_` prefix | Major | **FIXED** | `is_test_name` is gone; discovery uses the compiler table (`runner.ritz:460`). Spec §17.1 now defines a test by `[[test]]` and specifies its result and signature (`LANGUAGE_SPEC.md:5183-5196`). | #1868 |
| M2 | ritzunit runner defects | Major | **PARTLY** | Fixed: exit wrap (`runner.ritz:129-132`); the 1024 cap (now a gvec); output isolation (memfd, `:137`); the JSON escaper handles every byte < 0x20 (`json_reporter.ritz:114`); polling replaced by `rt_sigtimedwait` (`:185`). Still there: 13 `g_*` option globals (`:68-80`); the deprecated `ritzlib.args` (`:31`); `g_color` written but never read (`:611`, `:614`); dead `struct TestResult`, `summary_merge` and `TEST_SKIP` (`types.ritz:15,24,73`); wait-status macros in ritzunit (`wait_status.ritz:12`) rather than `ritzlib.process`. | #1868 |
| M3 | Tests that test a copy, cannot fail, or never run | Major | **PARTLY** | Fixed: `test_assertions.ritz:11` imports `ritzunit.assertions`; rzrz `test_args.ritz:10` calls `parse_args` (a7625437); angelo's 106 in-`src` tests run through `[test] sources` (97b9b75a). Open: prism `src/damage.ritz` still exists and `test_damage.ritz:7` tests it, not `compositor/damage`; `test_core.ritz:12-27` still redefines its types; `inventory/test/test_inventory.ritz:35` redefines `Inventory`; ritzunit runner, filter and the reporters have no tests. nexus is covered in M11. | #1873 |
| M4 | Five assertion libraries; `assert` test-only and value-blind | Major | **FIXED** | `[[test_helper]]` and assert diagnostics that print operands are in the spec (`LANGUAGE_SPEC.md:5198-5230`, with an `expect-runtime-error` example). zeus `test/support` and spire `lib/test` are deleted (9621b472, 6a350efd), as is `testing.ritz`. `git grep 'fn assert_eq_i(32\|64)('` hits only `larb/review/3`. spire `test_utils.ritz` keeps HTTP-specific helpers, which are fine. | #1869 |
| M5 | No `\xNN` / `\e` escapes | Major | **OPEN** | The spec escape list is unchanged (`LANGUAGE_SPEC.md:334`). `ritzunit/src/reporter.ritz:71-75` still writes `buf[0] = 27   # ESC`. | #1872 |
| M6 | Hand-rolled formatting and C string idioms | Major | **PARTLY** | Fixed: rzsh and indium `print_int` and angelo's writer use `ritzlib.fmt` (`rzsh/src/common.ritz:39`, `indium/user/libharland.ritz:67`, `angelo/src/hello_world.ritz:69`; cb35e7c4); nexus `write_cstr`/`write_bytes` are gone; lexis char literals (78d0b72f). Open: ritz-lsp still reads one byte per syscall (`transport.ritz:37-39`), parses `Content-Length` by hand (`:77`) and uses `itoa` (`protocol.ritz:134,147,153`); 15 numeric char compares remain in lexis (`git grep -c 'c == NN'`). | #1856 |
| M7 | Harland userland written four times | Major | **OPEN** | `sys_open` is still defined at `harland/user/libharland.ritz:38`, `indium/user/libharland.ritz:41`, `ritzutils/src/cat.ritz:25` and `rzsh/src/main_harland.ritz:36`. ritzlib still has it for linux only (`sys.ritz:554-556`). `harland/user` is alive and edited twice over: 5597ffa3 migrated both copies, and 7 files are still byte-identical. rzsh `main_linux.ritz`/`main_harland.ritz` are still present and unimported, and they share 84 duplicate-window lines. `indium/Makefile:51,58` and `tools/mkiso.sh:61,66,72,78` still use `cp … 2>/dev/null \|\| true`. | #1871 |
| M8 | Developer tools report success while doing nothing | Major | **PARTLY** | Fixed: rzrz `test`/`clean`/`run`/`compare` delegate to `./rz` (`rzrz/src/main.ritz:170-198`; a7625437). `build` goes through fork/exec with no pipes, so the deadlock is gone. ritz-lsp advertises only `textDocumentSync` (`server.ritz:50`), pinned by `ritz-lsp/test.sh` (d5b1deb9). Open: `build --all` and `list` still walk only `projects/*` (`main.ritz:54`, `:206`), while the workspace is `projects/**` (`rz.toml:17`); `build --all` could delegate `--all` the way `test` does. | #1874 |
| M9 | Complexity hot spots (browser stack, parked) | Major | **OPEN** | The metrics are unchanged. lexis `tokenizer_next` is 510 SLOC, CC 173; `tag_from_name` is CC 105. sage `lexer_next` is CC 64. angelo `execute_instruction` is 164 SLOC, CC 125 (was 129). rzsh `main` is 138 SLOC, CC 42, depth 7 (was 134/41). Spec §8.2 literal patterns are still integer-only (`LANGUAGE_SPEC.md:2977-2988`). | #1876 |
| M10 | Checked-in secrets, transcripts, binaries, rotted manifests | Major | **PARTLY** | Fixed: `nexus/deploy/certs/key.pem` is untracked (only `.gitignore` remains); the angelo render test with the pre-monorepo path is gone (it is now an angelo `[[bin]]`, 7993be7b). Open: 21 `logs/claude_transcript_*` files are tracked; `angelo/aadhunik.ttf` and `prism/hello.ppm` are tracked; `ritzunit/patches` and `ritzunit/known_issues` exist; `nexus/wiki` has 38 files, and `wiki/projects/ritzunit.md:24-26` still claims squeeze, cryptosec and mausoleum depend on ritzunit; `tempest/ritz.toml:36` still points at `../ritz/ritzunit`; `lexis/ritz.toml:17` still declares ritzunit; `ritzunit/inventory/ritz.toml` still uses `[deps]` with a path that doesn't resolve. | #1875 |
| M11 | nexus has two architectures; only one is live | Major | **REGRESSED** | Production still imports only `store`, `slug`, `pages`, `html_writer` and `log` (`nexus/src/main.ritz:43-48`). `errors/`, `models/`, `presenters/`, `repos/` and `services/` (862 SLOC) are imported only by each other and by 7 test files (1,532 test SLOC). e233575e made them compile against a live Mausoleum instead of deleting them. By INSTRUCTIONS §1 that is dead code with green tests. `repos/page_cache.ritz` keeps a per-worker cache that eb5415ea removed from the live path. | #1870 (the acceptance there says "dead layer deleted") |
| Mi-a | ritzunit README and filter claims | Minor | **PARTLY** | The README is fixed: no "Used by" line, `./rz test ritzunit` (`:123`), and `ritz.toml:10-12` is accurate. `let s: *u8 = "hello"` (`:58`) is now valid since 507d4d5c. Still stale: `filter.ritz:10` claims `*` stops at `::`; `:19-23` treats tags as name substrings. | #1875 |
| Mi-b | angelo file loading (raw stat buffer, unchecked NUL) | Minor | **OPEN** | `angelo/src/loader/file.ritz:14-28`: it calls `sys_open(strview_as_ptr(path))` assuming a NUL, and reads the size from `var statbuf: [144]u8` at offset 48. | #1875 |
| Mi-c | Missing from ritzlib: UUID, hex, float parse | Minor | **PARTLY** | Hex output now exists (`ritzlib/fmt.ritz:44` `fmt_u64_hex_into`, `string.ritz:543`). UUID is still written twice (`spectree/lib/uuid.ritz`, `spire/lib/model/uuid.ritz`). Float parsing is still only in `sage/src/lexer.ritz`. | — |
| Mi-d | Packages with no purpose (spectree, angelo-simple, ritzutils) | Minor | **OPEN** | spectree is unchanged (1,705 SLOC, same metrics). angelo-simple is unchanged apart from two repo-wide sweeps. ritzutils is the same 71-SLOC `cat`. | #1875 |

**Ticket vs code:** #1870's acceptance (a) requires "the dead layer from M11 is deleted". C2 is fixed in code, but the dead layer was revived (e233575e, 2026-11-04), not deleted. If #1870 is closed, the code does not support closing it.

## Metrics delta

| Package | SLOC | fns | longest fn (SLOC) | max CC | fns >150 SLOC | CC >30 | depth ≥6 | smells | dup clusters ≥3 |
|---|---|---|---|---|---|---|---|---|---|
| ritzunit | 2,156 → 2,151 | 218 → 200 | run_tests 101 → 80 | 30 → 23 | 0 | 0 | 0 | 146 → 174 | 5 |
| ritz-lsp | 455 → 445 | 35 → 33 | parse_message 37 | 12 → 11 | 0 | 0 | 0 | 90 → 84 | 0 |
| rzrz | 320 → 379 | 18 → 27 | parse_args 45 → 49 | 18 → 19 | 0 | 0 | 0 | 46 → 92 | 0 → 1 |
| ritzutils | 71 | 9 | cat_file 20 | 7 | 0 | 0 | 0 | 12 | 0 |
| rzsh | 1,700 → 2,705 | 114 → 199 | main 134 → 138 | 41 → 42 | 0 | 2 → 3 | 4 → 5 | 340 → 559 | 3 → 2 |
| indium | 571 → 528 | 49 → 40 | main 61 | 10 | 0 | 0 | 0 | 187 → 188 | 1 |
| spectree | 1,705 | 186 | uuid_parse 51 | 16 | 0 | 0 | 0 | 45 | 4 |
| nexus | 2,207 → 4,256 | 163 → 384 | handle_wiki_view 63 → main 61 | 18 | 0 | 0 | 7 → 0 | 307 → 449 | 11 → 1 |
| lexis | 5,791 → 5,800 | 433 | tokenizer_next 510 | 173 | 2 | 7 | 4 | 81 | 15 |
| prism | 5,307 → 5,336 | 582 → 579 | get_char_row 132 | 66 | 0 | 2 | 2 | 49 → 46 | 2 |
| angelo | 4,499 → 4,693 | 363 → 370 | execute_instruction 164 | 129 → 125 | 1 | 2 | 3 | 33 → 46 | 7 → 8 |
| sage | 2,916 → 2,945 | 186 → 187 | lexer_next 131 | 64 | 0 | 2 | 1 | 57 → 72 | 18 |
| iris | 2,177 | 180 | resolve_box_model 52 | 15 | 0 | 0 | 2 | 38 | 0 |
| tempest | 1,209 | 134 | handle_browser_message 30 | 17 | 0 | 0 | 0 | 3 | 0 |

What changed:
- **Build status:** lexis and tempest still do not build (`rz.toml:43-44`, #2162 and #1302).
- **nexus doubled,** because of the rewrite in C2 and the tests on the dead layer in M11. Its nesting hot spots are gone.
- **rzsh grew by 1,005 SLOC** (the 448c80df shell features). Its smells went from 340 to 559 (F1).

## New findings

### F1. rzsh's new shell parser is C in Ritz clothing [cleanup] — Major
- **Evidence:** `rzsh/src/parse.ritz`, added by 448c80df, 326 SLOC.
  - **Fixed global tables:** `MAX_TOKENS = 64` with the parallel arrays `g_tok_kind`/`g_tok_word` (`:30-38`), `g_word_buf: [2048]u8` (`:41`), `MAX_VARS = 32` with `g_var_names: [1024]u8`, `g_var_values: [8192]u8` and the parallel `g_var_used`/`g_var_exported` (`:237-244`), and `g_envp_buf: [8192]u8` (`:403`).
  - **Integer kind codes** where an enum belongs: `TOK_*` (`:24-28`).
  - **Numeric character codes:** 24 compares in `parse.ritz`, for example `c == 63  # $?` (`:98`) and `123`/`125` for `{`/`}`. Char literals exist and lexis was migrated to them in 78d0b72f.
  - **Hand copy loops** with a repeated magic `8192` in `vars_build_envp` (`:408-428`).
  - **Results passed back through globals:** `g_overflow`, `g_tok_next` and `g_tok_count`.
- **Impact:**
  - The package's smells rose from 340 to 559, and `tokenize` has CC 32 at depth 6.
  - The shell has hard limits: 64 tokens, 32 variables, 2 KB of words and 8 KB of environment. Past them, `push_token` sets `g_overflow` (`:83-85`) and `var_set` returns -1 (`:316-317`); exported variables that don't fit in 8 KB are left out of a child's envp (`:418`).
  - rzsh is on the M2.3 "boots to rzsh" path.
- **Fix direction:**
  - Tokens become `Vec<Token>` with `enum TokKind` and StrView words.
  - The variable table is `Vec` of `{name: String, value: String, exported: bool}`.
  - envp is built in a `String`.
  - Use char literals.
- **Ticket:** #3459.

### F2. nexus's rewritten modules reintroduce `(*u8, len)` pairs and i32 booleans [cleanup] — Minor
- **Evidence:**
  - **`slug.ritz`:** `path_starts_with`, `extract_slug`, `validate_slug` and `slug_from_path` (`:14,27,48,67`) take `(*u8, i32)` and return `1`/`0` as `i32`. `bool` has been its own type since c8893b5a.
  - **`pages.ritz`** (`:52-204`) and `html_writer.ritz` (`html_bytes(out, src, len)`) take the same pairs.
  - **ptr/len pairs** in nexus went from 34 to 48 (metrics).
  - **`wiki_store_get(slug, len, content_out, content_len_out)`** (`store.ritz:542`) takes no capacity. Every caller must know to pass a buffer of at least `MAX_CONTENT_LEN` (`main.ritz:281,326,365,389`).
- **Fix direction:** take StrView parameters and return `bool`. `wiki_store_get` returns a `String`, or takes a capacity.
- **Ticket:** #3461.

## Not findings
- **rzsh `print_int` uses `[20]u8`:** `i64::MIN` is 20 characters, and `fmt_i64_into` writes no NUL, so it fits.
- **nexus content buffers `[8192]u8`** (`main.ritz:281` and others) are filled only through `db_extract_field(…, MAX_CONTENT_LEN)` (`store.ritz:359`) or the `fallback_get` copy of a stored page. Both are bounded.

---

# Part 2: infrastructure (spire, cryptosec, http, valet, zeus, squeeze, mausoleum, tome)

**Status: NEEDS WORK** (was CRITICAL)

## Summary

The two TLS Criticals are fixed in code:
- **C1:** wire lengths are bounded before use.
- **C2:** the client authenticates the server and fails closed. Record framing passes the whole record, and `valet/test/test_tls_e2e.ritz` exercises cryptosec client ↔ valet.

cryptosec's February H-items H-1, H-2, H-4, H-7 and H-10 are fixed. spire's 7.3k-line httplib fork is deleted (74580387), and the infra integer formatters mostly go through `ritzlib.fmt`.

What remains:
- **Security:**
  - mausoleum generates X25519 ephemeral keys from `getrandom` without checking its result (3 sites, missed by #1863).
  - valet still ignores `Transfer-Encoding` and reads a non-numeric `Content-Length` as 0.
- **Structure:**
  - The duplicate subsystems other than spire's are all still there: valet `lib/tls/`, tome's three servers, mausoleum's test-only `server.ritz`, squeeze's encoder copies.
  - The language gaps (element-list literals, the flat namespace, a generic `HashMap`) are unchanged.
- **Size:** valet's two connection handlers grew past the thresholds.

The status is NEEDS WORK rather than CRITICAL because no remaining item is a reachable memory-safety bug.

## Against review/4

| id | title | v4 sev | now | evidence | ticket |
|---|---|---|---|---|---|
| C1 | TLS: wire-supplied lengths overflow fixed buffers | Critical | **FIXED** | `tls13_record_decrypt` checks the header length against `record_len` (`cryptosec/lib/tls13_record.ritz:192`) and caps it at `TLS_MAX_CIPHERTEXT_LEN` before touching `inner` (`:198`). `inner` is sized to that cap (`:222`), and `out_cap` is checked before the copy (`:240`). `handshake_header_parse` refuses `length > len - 4` (`tls13_handshake.ritz:1184`). Fixed by 12114377. | #1861 |
| C2 | TLS client fails open; record framing wrong at every caller | Critical | **FIXED** | `certificate_verify_verify` verifies ECDSA P-256/P-384, Ed25519 and RSA-PSS, and refuses everything else (`tls13_handshake.ritz:1056-1120`). The client checks the pin or CA chain and the hostname (`tls13_client.ritz:690-710`). Every caller passes the full record (`valet/lib/tls.ritz:1222`, `:1360`; `tls13_client.ritz:609`). The e2e test is `valet/test/test_tls_e2e.ritz` (8baaa0e6, 731a16ad). | #1862 |
| S1 | cryptosec `REVIEW.md` H-1/2/4/7/10 open and unticketed | (in summary) | **FIXED** | H-1 and H-2 are fixed by C1 and C2. H-4: secret wipes use `sizeof` (cca1f597). H-7: `u128_mul` takes the full product (`u128.ritz:67-74`). H-10: `sc_is_canonical` is checked in verify (`ed25519.ritz:783`). | #1862 |
| M1 | Secrets and randomness | Major | **PARTLY** | Fixed: `random_u64` aborts on RNG failure (`random.ritz:131-135`); secret wipes are sized with `sizeof`; tome AUTH uses `ct_bytes_eq` (`tome/lib/commands.ritz:992`, `ritzlib/ct.ritz:20`; cca1f597); `mem_zero` has an asm barrier (`mem.ritz:30-34`, 5e6db0de). Open: mausoleum ignores `getrandom`'s result when it generates X25519 private keys (`mausoleum/lib/encrypted_channel.ritz:104`, `:129`; `server_async.ritz:223`), all three present at 887d91ad. **Impact:** if the call fails (`ENOSYS` under seccomp, `EFAULT`), the key is whatever was in the struct. **Fix direction:** check the return and fail closed, or call `random_bytes`, and mark `getrandom` `[[must_use]]`. The secure-zero language intrinsic (#1864) does not exist; the asm barrier stands in for it. | #1863, #1864 |
| M2 | HTTP/1 framing | Major | **PARTLY** | Fixed: a body that spans several `recv()` calls is collected up to `headers_end + Content-Length` (`valet/lib/valet.ritz:1205-1221`, `request.ritz:266-273`; 0599a969); an overflowing CL is refused with 413; the open-ended `Range` can no longer go negative (`static.ritz:213-235`); pipelining is in (`valet.ritz:917`). Open: valet's request parser never reads `Transfer-Encoding` (only `http/lib/h1_response.ritz:168` does, for responses); a non-numeric `Content-Length` parses as 0, so the request has "no body" (`request.ritz:172-184`); with duplicate CLs, the last one wins. **Impact:** request desync or smuggling when valet proxies. **Fix direction:** refuse TE+CL, a non-digit CL and conflicting CLs with 400, or implement chunked decoding. | #1865 |
| M3 | 22 integer formatters, 19 parsers | Major | **PARTLY** | Fixed: `json_write_i64` (`valet/lib/json_builder.ritz:81`) and `resp_write_i64` (`tome/lib/resp.ritz:422`) use `fmt_i64_into` (d02a0ad2). Open: `zeus/lib/main_helpers.ritz:262` `i64_to_str` writes an empty string for any negative value (`while v > 0`); `spire/lib/middleware/mod.ritz:430` is another hand-rolled formatter; 28 hand-written `* 10 +` parse loops remain in non-test infra code (30 at v4), including valet's CL parser. | #1856, #1824 |
| M4 | Duplicate and dead subsystems | Major | **PARTLY** | Fixed: spire/httplib is deleted (74580387, #1680; spire went from 16,852 to 5,380 SLOC); ritzlib has one async runtime (cc4d6a8e, #1855). Open: valet `lib/tls/{conn,handshake,keyschedule,record}.ritz` are imported only by each other; tome still has `server`, `blocking_server` and `server_blocking`, with `bin/tome_server_blocking.ritz` not declared in `ritz.toml:14-20`; mausoleum `lib/server.ritz` is imported only by `test/test_server.ritz`; squeeze is unchanged (same metrics, 25 clusters of ≥3). | #1867, #1680, #1855 |
| M5 | Static tables as if-ladders | Major | **OPEN** | `http/lib/qpack_static.ritz:29` `qpack_static_get` is still 383 SLOC, CC 101. `cryptosec/lib/sha512.ritz:121` `get_k512` (162 SLOC, CC 81) and `sha256.ritz:94` `get_k` (CC 65) are unchanged. | #1866 |
| M6 | Private names leak through imports | Major | **OPEN** | The spec now says outright that privacy gives no namespace, and makes a duplicate fn name across an import closure an error (`LANGUAGE_SPEC.md:5074-5092`; 42fb3e42). Calling another file's private fn is also an error (§15.2, ad97d689). So the clash is now loud instead of silent, but the gap is the same: lexis is blocked on exactly these clashes (`rz.toml:43`), and packages still prefix-rename. | #1858 |
| M7 | tome's hand-rolled string-keyed map | Major | **OPEN** | ritzlib still has only `HashMapI64` (`ritzlib/hashmap.ritz:31`). `tome/lib/tome.ritz` is unchanged (2,448 SLOC, 123 hash/probe lines). | #1858 |
| M8 | Functions over the v4 thresholds | Major | **REGRESSED** | Fixed: `x509_parse_extensions` is no longer over the depth threshold. Grew: `valet_handle_connection` went from 141 SLOC/CC 31 to 201/53 (`valet/lib/valet.ritz:1150`); `valet_handle_tls_connection` from 197/34 to 213/39, depth 6 (`:1478`); `handle_task_event_encrypted` from 169/37 to 174/41 (`mausoleum/lib/server_async.ritz:1187`); tome `cmd_dispatch` from 118/38 to 130/42. Unchanged: `qpack_static_get`, `get_k512`, `deflate_dynamic` (164/37, depth 6). | #1867 |
| Mi | Debug prints, transcripts, broken symlink, `bcmp.s`, no-importer modules, argument parsing | Minor | **OPEN** | 86 `prints("[…")` debug lines are still in `valet/lib/tls.ritz` (also 86 at v4), for example `:1217-1231`. `spire/logs` and `tome/logs` transcripts are tracked. `valet/lib_squeeze` is still a tracked broken symlink. `mausoleum/runtime/bcmp.s`, `squeeze/lib/bytes.ritz` and `http/lib/json_stub.ritz` have no importers. The four zeus test-only modules (`hotreload`, `runtime`, `streaming`, `worksteal`) are still imported only by their tests. | #1867, #1875, #1495 |

## Metrics delta

| Package | SLOC | fns | longest fn (SLOC) | max CC | fns >150 SLOC | CC >30 | depth ≥6 | smells | dup clusters ≥3 |
|---|---|---|---|---|---|---|---|---|---|
| spire | 16,852 → 5,380 | 1,523 → 650 | qpack_static_get 383 → present_error 55 | 101 → 15 | 2 → 0 | 3 → 0 | 1 | 967 → 208 | 52 → 13 |
| cryptosec | 17,753 → 25,808 | 1,008 → 1,711 | test_chacha20_poly1305_rfc8439 222 → 224 | 81 | 5 | 2 | 4 → 3 | 1,768 → 2,735 | 140 → 158 |
| http | 11,312 → 11,338 | 847 → 848 | qpack_static_get 383 | 101 | 2 | 3 | 0 | 893 | 37 |
| valet | 7,137 → 9,249 | 457 → 644 | valet_handle_tls_connection 197 → 213 | 40 → 53 | 1 → 2 | 4 | 14 → 15 | 840 → 1,122 | 5 → 14 |
| zeus | 6,967 → 6,790 | 478 → 490 | main (examples/test_client) 131 → 138 | 20 → 23 | 0 | 0 | 0 | 284 → 335 | 18 |
| squeeze | 6,976 → 6,975 | 347 | deflate_dynamic 164 | 37 | 1 | 1 | 8 | 534 | 25 |
| mausoleum | 14,007 → 15,341 | 907 → 990 | handle_task_event_encrypted 169 → 174 | 37 → 41 | 1 | 1 | 2 → 3 | 666 → 783 | 84 → 88 |
| tome | 6,789 → 7,270 | 450 → 486 | client_print_response 122 → cmd_dispatch 130 | 38 → 42 | 0 | 1 | 19 | 909 → 1,007 | 54 → 55 |

What changed:
- **cryptosec** grew by 8k SLOC, mostly tests: `test_ed25519` (2,064), `test_tls13_handshake` (1,571), `test_tls13_client` (1,130), `test_x509_verify` (1,055) and `test_p256` (1,059).
- **valet** grew by 2.1k SLOC, including `test_tls_e2e.ritz` (1,042) and `proxy.ritz`.

## New findings

### F3. TLS client silently truncates a configured hostname longer than 255 bytes [security] — Minor
- **Location:** `tls_config_set_hostname` (`cryptosec/lib/tls13_client.ritz:109-116`) clamps `len` to 255 and keeps going.
- **Impact:** both SNI and certificate hostname verification (`:701`) then check a prefix of the name the caller asked for. A server holding a certificate for the truncated name passes. Exploiting this requires a caller-supplied hostname over 253 bytes, which is already invalid DNS.
- **Fix direction:** refuse a hostname over 253 bytes (return an error, as the rest of the client now fails closed), and pin the behaviour with a test.
- **Ticket:** #3460.

### F4. cryptosec test files over the file-size threshold [cleanup] — Minor
- **Evidence:**
  - `cryptosec/test/test_ed25519.ritz` is 2,064 SLOC; it was 1,721 at v4, already over and not flagged then.
  - `test_tls13_handshake.ritz` (1,571 SLOC) crossed the 1,500 Major threshold after review/4.
  - Both are hand-written vector tables and cases.
- **Fix direction:** split them by concern (RFC 8032 vectors, small-order/canonical checks, Wycheproof-style cases; handshake parse vs CertificateVerify). This becomes element-list data once #1866 lands.
- **Ticket:** #3461.

## Not findings
- **valet's heap receive buffer:** `bigbuf_acquire` (`valet/lib/valet.ritz:993-995`) refuses any size over `VALET_MAX_BUFFERED`, even when `max_request_size == 0` (unlimited, `:133`). A client-claimed huge `Content-Length` cannot force an unbounded mmap.
- **`[16624]u8` in `tls13_record_decrypt`** (`tls13_record.ritz:222`) is a stack buffer sized to the cap that `:198` enforces, and the comment says so. The size is still a hand-computed literal rather than one derived from those constants.
- **AES-GCM `mem_zero(@block[0], 16)`** calls (`aes_gcm.ritz:274` and others) clear 16-byte blocks; they are not hand-counted secret sizes.

## Not verified
- AGAST ticket states (no AGAST access in this review).
- Whether `ritz-lsp/test.sh` and the prism and nexus suites are green: nothing was run. The spire and http module-liveness checks of review/4 were not redone file by file; only the deletions named above were confirmed.
