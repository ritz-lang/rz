# LARB v4 Review: remaining packages (ritzunit, developer tools, harland userland, browser stack, parked apps)

**Reviewed:** 2026-10-25 · **Metrics:** [metrics-packages.md](metrics-packages.md), the ritzunit … ritzutils sections (angelo-simple is not in the metrics; it is 55 SLOC) · **Status:** NEEDS WORK
**Scope:** ritzunit, ritz-lsp, rzrz, ritzutils, rzsh, indium, spectree, nexus, lexis, prism, angelo, angelo-simple, sage, iris, tempest.
**Method:** `INSTRUCTIONS_v4.md`, read-only. Nothing was built or run. SLOC means non-blank, non-comment lines of tracked `.ritz` files. The claims everything else rests on were checked by reading the code:
- **The gate never runs ritzunit.** `build.py:2338` runs `ritz0 --test` once per file. `ritz0.py:390` dispatches to `test_runner.run_test_file` (`test_runner.py:705-815`). No tooling file mentions ritzunit except `test_runner.py:880-1042` (`--batch`), and nothing calls `--batch` (`git grep -- --batch`).
- **The nexus overflow is real.** `MAX_CONTENT_LEN = 8192` (`store.ritz:37`). Content is written through `write_escaped`, which expands up to 6×, into `var body: [16384]u8` (`main.ritz:509`, `:743`). `write_cstr` and `write_escaped` (`main.ritz:63`, `:114`) never check a bound.

## Summary

The package that matters most here, **ritzunit, is not used by anything that gates**:
- **What runs instead:** the live harness is Python (`ritz0/test_runner.py`). It works through a file's tests one at a time, one subprocess each, with a hard-coded 10 s timeout.
- **What ritzunit offers that nobody uses:** ELF discovery, fork isolation, filters, JSON/JUnit output, shuffle.
- **ritzunit's own tests test copies of its code.**
- **There are four test runners and five assertion libraries.** The assertion libraries exist because the language's `assert` is test-only and does not show the values it compared. Under No Concessions that is a language ticket.

Below ritzunit:
- **Harland userland is written in four places.**
- **The developer tools report success for commands that do nothing:** rzrz `test`/`run`/`clean`/`compare`, and ritz-lsp's hover and definition.
- **nexus has a stack overflow on user input.**
- **The worst complexity is in the parked browser stack.** lexis `tokenizer_next` is 510 SLOC with CC 173.
- **Several packages are scaffolding with no consumers:** spectree, angelo-simple, ritzutils, and most of rzrz.

## Packages

| Package | SLOC | Status | Worst issue | Recommendation |
|---|---|---|---|---|
| ritzunit | 2,156 | Builds. Its 3 test files never import `src/`. | The gate doesn't use it; its tests test copies (C1, M3) | **Keep**: make it *the* harness for ritz0 and ritz1 |
| ritz-lsp | 455 | Builds; no tests | Advertises hover and definition, returns `null` (M8) | Keep, parked; remove the false capabilities |
| rzrz | 320 | Builds; its one test cannot fail | 4 of 7 commands print a line and exit 0 (M8) | Cut to `build`/`list` or delete until the tooling.md prerequisites land |
| ritzutils | 71 | Builds (harland target); no tests | One `cat` that redeclares harland syscalls (M7) | **Merge** with indium userland |
| rzsh | 1,700 | Builds; tests import production | Two dead alternate `main_*.ritz` files (M7) | Keep (on the M2.3 path) |
| indium | 571 | Builds; no tests | Diverging copy of `harland/user`; image build hides missing binaries (M7) | Keep (track 2, M2.2/M2.3) |
| spectree | 1,705 | `test_only` lib; no consumers | Has no executable and no MCP server (`README.md:17`) | **Archive** (AGAST does this job) |
| nexus | 2,207 | Builds; test-all red (tooling.md F9) | Stack overflow (C2); a dead second architecture (M11); private key in git (M10) | Fix C2 or **archive** (parked #50) |
| lexis | 5,791 | **Does not build** (`rz.toml:67`, #1289) | `tokenizer_next` 510 SLOC, CC 173 (M9) | Keep, parked |
| prism | 5,307 | Builds; test-all red (tooling.md F9) | Two `DamageRegion`s, and the tests cover the dead one (M3) | Keep (indium image ships `hello_gfx`) |
| angelo | 4,499 | Builds | 106 `[[test]]`s in `src/` that no gate runs (M3) | Keep, parked; move the tests |
| angelo-simple | 55 | Builds; no tests | Doesn't use angelo: a gradient PGM writer | **Archive**, or move to `examples/` |
| sage | 2,916 | Builds | `lexer_next` CC 64; i32 token codes (M9) | Keep, parked |
| iris | 2,177 | Builds | No function over threshold; 36 i32-as-bool | Keep, parked |
| tempest | 1,209 | **Does not build** (`rz.toml:69`, #1302) | Imports a nonexistent HashMap API (ritzlib.md M4); bad ritzunit path (M10) | Keep, parked |

## Findings

### C1. Four test harnesses; the gate uses none of the Ritz ones [architecture] — Critical
- **The live harness:**
  - `build.py:2266-2343` runs every test file one after another through `ritz0 --test`.
  - `test_runner.py:705-815` compiles one harness per file that dispatches on argc. It then runs each test as its own subprocess, sequentially, with `timeout=10` hard-coded (`:779`).
  - ritz1 has no harness (`build.py:2291-2300`, #1500).
- **ritzunit's runner is reachable only through `test_runner.py --batch` (`:880-1042`), which has no callers.** It compiles `runner.ritz` as the file that provides `main`. But `main` was moved out to `bin_main.ritz` in 5133247 (2026-04-26), and `runner.ritz` does not import `bin_main`. So reading the code, `--batch` should fail to link with no `main`. Not run.
- **`ritzlib/testing.ritz`** (`register_test` and `extern fn __init_tests`, `:50`, `:117-122`): the only thing that defines `__init_tests` is the golden test `test_ritzlib_output_goldens.py:97`.
- **`ritz0 --emit-test-main`** (`ritz0.py:302-345`, `:353`) is broken twice over:
  - `generate_test_main_source` (`emitter_llvmlite.py:12398-12432`) emits a call to `run_tests_array`, which is defined nowhere (`git grep`).
  - It also emits the legacy `&x` syntax, which the parser rejects (`parser.py:483`).
- **Correction to ritzlib.md, "Dead modules → Not dead":** testing.ritz is *not* live through ritz0 injection. The injection at `emitter_llvmlite.py:12406` lives only in this dead `--emit-test-main` path.
- **Impact:**
  - ritzunit's fork isolation, timeouts, JSON/JUnit output and filtering serve nobody.
  - The live harness has no parallelism and no machine-readable output.
  - ritz1 cannot run any `.ritz` test (tooling.md, "Long-term" item 3).
- **Fix direction:** one harness for both compilers.
  1. ritz0 and ritz1 emit a test table for `[[test]]` functions: a `__ritz_tests` symbol of `{name: StrView, fn}` plus a count.
  2. The ritzunit runner is the `main` linked into every test binary, and `build.py` runs that binary for any `--compiler`.
  3. ritzunit gains `-j N`, a fork pool with a bounded number of children. Parallelism across files stays with G8 #1809.
  4. Delete `testing.ritz`'s runner, `--emit-test-main` and `--batch`.

### C2. nexus: stack buffer overflow while escaping page content [cleanup] — Critical (parked package)
- **The overflow:** `write_escaped` (`nexus/src/main.ritz:114-126`) turns `"` into the 6 bytes `&quot;`. With `<`, `>`, `&` and `'` it is 4-5×.
- **The sizes:** content can be up to 8,192 bytes (`store.ritz:37`, `:280`). The page bodies are `[16384]u8` (`main.ritz:509`, `:743`), and the CSS head is written first.
- **The trigger:** a stored page of 8,192 `"` characters writes about 49 KB into a 16 KB stack buffer.
- **No bounds anywhere:** `write_cstr` and `write_bytes` (`:63-75`) never check one. The same pattern is used for the 404, edit and index pages (`:479`, `:550`, `:609`).
- **The slug goes into `href` unescaped** (`write_bytes`, `:524`, `:752`). `extract_slug` (`:235-257`) accepts any byte except `/`.
- **Fix direction:** build responses in ritzlib `String`/`GrowBuf` (`string_push_*`) and drop the fixed buffers. Escape the slug, or validate it against `[a-z0-9-]`.

### M1. ritzunit finds tests by name prefix, not by `[[test]]` [architecture] — Major
- **How it discovers:** `is_test_name` (`runner.ritz:307-318`) matches every ELF function symbol that starts with `test_` (`:375-388`). The comment at `:3-5` ("@test generates test_ prefix") is stale.
- **What that would run:** 114 functions outside `docs/archive` are named `test_*` but are not `[[test]]`. For example, `mausoleum/test/test_storage.ritz:20` returns a StrView, so it would run and "fail".
- **What it would miss:** a `[[test]]` function with any other name. None exists today (checked by script).
- **The gap behind it:** spec §17.1 (`LANGUAGE_SPEC.md:1614-1621`) never says what a test returns, what its exit code means, or how tests are discovered.
- **Fix direction:**
  - Discover tests from the compiler-emitted table in C1.
  - Specify test semantics in §17.1: return type, pass/fail, discovery.

### M2. ritzunit runner defects [cleanup] — Major
- **The exit code can wrap to 0:** the process exits with `failed + crashed + timeout` (`runner.ritz:571`). Only its low 8 bits reach the shell, so 256 failures exit 0.
- **Overflows are silent:**
  - Discovery stops at `MAX_TESTS = 1024` without a warning (`:39`, `:375`).
  - Both reporters drop every result after 1,024 (`json_reporter.ritz:49`, `:57`; `junit_reporter.ritz:39`).
- **The fork-failure comment is false:** it says "fall back to direct execution", but the code records a FAIL (`:206-211`).
- **Test output is not isolated:**
  - Child stdout and stderr are not captured, so test output mixes into the report.
  - With `--json`, any test that prints to stdout corrupts the document.
  - The only failure detail recorded is the exit code. Assertion messages never reach JSON or JUnit.
- **Timeouts are polling:** the parent busy-polls `wait4` with a 1 ms sleep (`:228-271`).
- **Invalid JSON:**
  - The escaper handles only `" \ \n \t` (`json_reporter.ritz:98-116`), so `\r` or any other control byte produces invalid JSON.
  - It also makes one `write` syscall per byte (`:87-91`, and `reporter.ritz:146-150` for the dots).
- **C in Ritz clothing:** twelve global `g_*` option flags (`runner.ritz:65-76`) belong in an `Options` struct returned by `parse_args`. The parser itself is the deprecated `ritzlib.args` (#1494).
- **Dead code:**
  - `run_test` (`:278`);
  - `struct TestResult` (`types.ritz:24`);
  - `summary_merge` (`types.ritz:69`);
  - `g_color`, which is written but never read (`runner.ritz:76`, `:626`);
  - `TEST_SKIP`, which is never recorded.
- **Duplicated dispatch:** `run_tests` (`:440`, CC 30) repeats the json/junit/text branch for each of four outcomes. A reporter struct of function pointers would remove 12 branches.
- **Missing from ritzlib:**
  - wait-status decoding: `WIFEXITED` and friends are redefined at `:48-59`, and `process.ritz:328-345` writes them inline;
  - wait-with-timeout.

  Both belong in `ritzlib.process` (tooling.md, "Long-term" item 5).

### M3. Tests that test a copy, cannot fail, or never run [cleanup] — Major
- **ritzunit:**
  - `test/test_assertions.ritz:14-40` redefines the assertions it claims to test.
  - None of the 3 test files imports any `src/` module. runner, filter and the reporters have zero tests.
  - `inventory/test/test_inventory.ritz:26-131` redefines `Inventory` instead of importing `inventory/src/lib.ritz`. This accounts for the 186 duplicate-window lines in the metrics.
- **rzrz:** `test/test_args.ritz:44-80` redeclares the CMD constants and asserts that each equals itself. `assert_eq` only increments a counter, and every `[[test]]` returns 0, so the file cannot fail.
- **prism:**
  - `test/test_damage.ritz:7` tests `src/damage.ritz`.
  - Production imports `compositor/damage.ritz` instead (`compositor/mod.ritz:6`). So there are two `DamageRegion` types (`src/damage.ritz:16`, `compositor/damage.ritz:8`) and two `Rect`s.
  - `test/test_core.ritz:12-27` redefines the core types.
- **angelo:**
  - 106 `[[test]]` functions across 20 `src/` files never run.
  - `build.py run_tests` only globs `test/*.ritz`, or the package root for `test_only` packages (`:2280-2287`).
  - angelo has `tests/`, which holds only fixtures.
- **nexus:** its tests import the layered code in M11, which production does not use.
- **Fix direction:**
  - Each test imports the module it covers.
  - The harness fails a package whose `src/` contains `[[test]]` functions that no gate runs, in the spirit of #1345 and #1484.

### M4. Five assertion libraries, because `assert` is test-only and shows no values [language-gap] — Major
- **The libraries:**
  - `ritzunit/src/assertions.ritz` (18 functions);
  - `spire/test/support/test_utils.ritz` (19);
  - `zeus/test/support/helpers.ritz` (15). `zeus/ritz.toml:27` declares ritzunit and then writes its own.
  - `spire/lib/test/mod.ritz` (10);
  - `ritzlib/testing.ritz` (5).
- **Per-type copies:** `assert_eq_i32` and `assert_eq_i64` are separate functions, and so are the lt/le/gt/ge variants for i32. ritzunit's only real importer is `valet/test/test_tls.ritz:5-6`.
- **Cause:**
  - Spec §19.2 (`LANGUAGE_SPEC.md:1721-1726`) allows `assert` only directly inside `[[test]]`, so a helper can't assert.
  - The failure message (`emitter_llvmlite.py:5769-5790`) carries `file:line` but not the operands.
  - `assertions.ritz:11` says it uses interpolation. It uses `eprints` chains, because interpolation only works in `print`/`eprint` (#1824).
- **Language fix (spec + ritz0 + ritz1):**
  - `assert a == b` prints both operands on failure.
  - An assert inside a function called from a test reports the test's call site.

  That collapses about 67 helper definitions.

### M5. No hex or escape-char literals [language-gap] — Major
- **The spec's escape list:** `LANGUAGE_SPEC.md:224` allows only `\n \t \r \\ \" \' \0`.
- **What packages do instead:**
  - `ritzunit/src/reporter.ritz:70-77` builds ESC from the byte 27 ("Ritz doesn't support \x escape sequences").
  - `rzsh/src/input.ritz:214-312` builds `ESC [ n D/C/G` byte by byte, three times over, each with its own digit code.
- **Latent bug in rzsh:** for n ≥ 1000 it emits `:`, because `48 + n/100` overflows one digit. Lines are capped at `MAX_LINE = 512` (`common.ritz:17`), so it cannot trigger today.
- **Fix:** add `\xNN` and `\e` to the spec, ritz0 and ritz1.

### M6. Hand-rolled formatting and C string idioms [cleanup] — Major → append to #1856
- **Integer printers:**
  - `rzsh/src/common.ritz:36`: prints garbage for negative numbers;
  - `indium/user/libharland.ritz:63`, `args_test.ritz:19`, `ping.ritz:20`;
  - `prism/tools/render_test.ritz:278`, `angelo_render_test.ritz:119`;
  - `angelo/src/hello_world.ritz:66`.
- **nexus reimplements ritzlib `str`:** `write_cstr`, `write_bytes` and `cstr_len` (`main.ritz:63-82`).
- **ritz-lsp:**
  - reads one byte per syscall (`transport.ritz:37-42`);
  - parses `Content-Length` by hand (`:76-87`);
  - uses the ritzlib `itoa` that has the `i64::MIN` bug (ritzlib.md M1).
- **Character codes written as numbers:** lexis has 67 `c == NN` compares (for example `tokenizer.ritz:437`, `c == 38  # &`), and `nexus/main.ritz:118-126` does the same. Character literals exist.
- **Smell totals (metrics):**
  - rzsh: 340, of which 260 are `c""` literals;
  - nexus: 307, including 34 `(*u8, len)` pairs, 44 fixed buffers and 15 `memcpy` calls;
  - indium: 187.

### M7. Harland userland is written four times; ritzlib has no harland `sys_open` [architecture] — Major → feeds #1857
- **Two copies of the userland:**
  - `indium/user` and `harland/user` share 22 file names; 7 files are byte-identical (`cmp`).
  - `harland/user` was last changed on 2026-02-17.
  - `harland/ritz.toml:4` says userspace lives in indium, yet `harland/build.py:32` still builds `USER_DIR`.
- **`sys_open(path, flags)` is redefined four times,** each passing `strlen` as the harland length:
  - `harland/user/libharland.ritz:38`
  - `indium/user/libharland.ritz:41`
  - `ritzutils/src/cat.ritz:25`
  - `rzsh/src/main_harland.ritz:36`

  ritzlib defines `sys_open` only for linux (`sys.ritz:575-576`).
- **rzsh has two dead mains:** `src/main_linux.ritz` and `src/main_harland.ritz` have no importers and are not `[[bin]]` entries (`entry = "main::main"`). `os.ritz`'s `[[target_os]]` gating replaced them.
- **Diverged image tools:** indium's `mkimage.py`, `mkiso.sh` and `mkboot.sh` differ from harland's by 29, 87 and 20 diff lines (`diff`). `indium/Makefile` never calls `mkimage.py`.
- **The image build hides missing binaries:** `mkiso.sh:62,66,71,77` and `Makefile:51,58` copy with `cp … 2>/dev/null || true`, so an image can be built without rzsh. M2.3 is "boots to rzsh".
- **Fix direction:**
  - Add harland `sys_open`/`sys_close` behind `[[target_os = "harland"]]` in ritzlib.
  - Delete `harland/user` and harland's user build step.
  - Delete rzsh's `main_linux`/`main_harland`.
  - Merge ritzutils with indium's `echo`/`wc`/`true`/`false`/`seq10` (ritzutils `README.md:28` already proposes it).
  - Make a missing binary fail the image build.

### M8. Developer tools that report success while doing nothing [cleanup] — Major
- **rzrz:**
  - `cmd_test`, `cmd_run`, `cmd_clean` and `cmd_compare` print one line and return 0 (`rzrz/src/main.ritz:276-326`). This breaks the roadmap invariant "a documented command must work".
  - `--all` walks only `projects/*` (`:174`); the workspace is `projects/**` (`rz.toml:16-19`).
  - `build_project` reads all of stdout before touching stderr (`:252-262`). A child that writes more than a pipe buffer of stderr would deadlock. Found by reading; not reproduced.
- **ritz-lsp:**
  - `initialize` advertises `hoverProvider` and `definitionProvider` (`server.ritz:48`), and both return `null` (`:162-172`).
  - Diagnostics are TODOs (`:100`, `:139`). There are no tests.
  - Its real blocker is architectural: the compiler front end is not a library ritz-lsp can import. That sequences it after M1.3 (#1830).

### M9. Complexity hot spots (browser stack, parked) [cleanup / language-gap] — Major
- **lexis:**
  - `tokenizer_next` (`lib/html/tokenizer.ritz:428`) is 510 SLOC, CC 173, depth 6: past the Critical thresholds. It is one if-chain over 25 `t.state == STATE_*` integer constants (`:16-…`). Split it into one function per state, with `enum State` and `match`.
  - `tag_from_name` (`lib/dom/tag.ritz:338`) is 211 SLOC, CC 105: a ladder of `name == "html"` tests. **Language gap:** `match` on StrView literal patterns. Spec §8.2 (`:974-1003`) covers only integer literals and enums.
- **sage:**
  - `check_keyword` (`src/lexer.ritz:183`, 100 SLOC, CC 54) is the same kind of ladder.
  - Tokens and AST tags are i32 codes, not enums, which forces the hand-written name ladders `token_type_name` (`token.ritz:173`) and `ast_node_type_name` (`ast.ritz:516`).
  - `lexer_next` (`:315`) has CC 64.
- **angelo:** `execute_instruction` (`src/hinting/interpreter.ritz:140`, 164 SLOC, CC 129) inlines every opcode body. Split it by opcode family.
- **rzsh:** `main` (`src/main.ritz:236`, 134 SLOC, CC 41, depth 7) handles every key inline. Extract one handler per key.

### M10. Checked-in secrets, transcripts, binaries and rotted manifests [cleanup] — Major
- **A private key in git:** `nexus/deploy/certs/key.pem` is an EC private key for a self-signed `CN=localhost` certificate valid until 2027-02-17 (`openssl x509`). `docker/docker-compose.yml:46-65` mounts it. Generate it at deploy time instead.
- **Agent transcripts:** `logs/claude_transcript_*.txt` in angelo, iris, lexis, prism, sage and tempest, about 383 KB in scope. Counting larb, spire and tome it is 947 KB.
- **Assets:**
  - `angelo/aadhunik.ttf` is byte-identical to `tests/fixtures/aadhunik.ttf` (md5); only `hello_world.ritz:144-149` uses it.
  - `prism/hello.ppm` is generated output.
  - `prism/tools/angelo_render_test.ritz:152` hard-codes `/home/aaron/dev/ritz-lang/angelo/aadhunik.ttf`, a pre-monorepo path that no longer exists.
- **Stale ritzunit leftovers:**
  - `patches/` is superseded: `io.ritz:182` already takes `@String`.
  - `known_issues/` is outside every gate, and `test/test_sizeof.ritz` now pins the sizeof case.
- **Stale docs:** `nexus/wiki/` holds 37 pages that restate package READMEs. `wiki/projects/ritzunit.md:15-25` claims squeeze, cryptosec and mausoleum depend on ritzunit; none does.
- **Manifests:**
  - `tempest/ritz.toml:36` points ritzunit at `../ritz/ritzunit`, which does not exist. Nothing notices, because `[dev-dependencies]` is never read (tooling.md F8).
  - `lexis/ritz.toml:17` declares ritzunit and imports nothing from it.
  - `ritzunit/inventory/ritz.toml` uses `[deps]`, and its path resolves to `projects/ritzunit/ritz/ritzlib`, which does not exist.
  - `ritz-lsp/ritz.toml` declares no ritzlib dependency.

### M11. nexus has two architectures and only one is live [architecture] — Major
- **What is live:** `main.ritz` and `store.ritz`.
- **What nothing imports:** `errors/`, `models/`, `presenters/`, `repos/` and `services/`, about 1,000 SLOC. Production never imports them, and they import APIs that don't exist:
  - `ritzlib.vec`: there is no `vec.ritz`;
  - `ritzlib.str { String, str_from_view, str_concat }`: `String` is in `string.ritz:32`, and the other two are defined nowhere;
  - `valet.valet`: there is no `valet/lib/valet.ritz`, and valet is not a nexus dependency.
- **The nexus tests target this layer,** which fits the nexus red in test-all (tooling.md F9).

### Minor
- **ritzunit README:**
  - `:74` says the binary "takes a compiled test executable". It reads `/proc/self/exe` (`runner.ritz:327`) and accepts no positional argument.
  - `:124` "Used by goliath, cryptosec, spire, spectree, squeeze" is false.
  - `:35` says 6 files and 27 assertions; there are 3 files with 30 `[[test]]`s.
  - `:59` writes `let s: *u8 = "hello"`, but `"hello"` is a StrView.
  - `ritz.toml:10` says build.py fork+execs ritzunit; it doesn't.
- **ritzunit filters:**
  - The glob "except `::`" rule (`filter.ritz:10`) is not implemented (`:182-213`).
  - `@slow` and `@ignore` are name substrings (`:19-23`), because the language has no test tags. [language-gap, low]
- **angelo file loading:**
  - `src/loader/file.ritz:12-14` hands a StrView to `sys_open` and assumes it is NUL-terminated.
  - `:21-28` reads the size from a raw `[144]u8` stat buffer at offset 48, although ritzlib has `struct Stat` (`sys.ritz:472`). The repo has 10 such raw stat buffers.
  - The function duplicates `fs.read_file` (`fs.ritz:336`) and `strview_to_cstr` (`strview.ritz:88`).
- **Missing from ritzlib:**
  - UUID is written twice (`spectree/lib/uuid.ritz`, `spire/lib/model/uuid.ritz`), and hex helpers appear in at least 8 non-test files; ritzlib has neither.
  - Float parsing exists only as `sage/src/lexer.ritz:507`.
- **Packages with no purpose:**
  - angelo-simple never imports angelo.
  - spectree has no consumers.
  - ritzutils is one 71-SLOC `cat`.

## Not findings
- **lexis `tag_name` (CC 124, `tag.ritz:554`)** is a flat `match`: the right shape. The CC counts its arms.
- **`inv:&Inventory`** in ritzunit/inventory is the mutable-borrow parameter form, not the removed `&T` (see the migration text at `parser.py:483`).
- **rzsh's tests import production** (`test_history.ritz:6`, `test_input.ritz:6`), and its `os.ritz` `[[target_os]]` layer is the right pattern. spectree, lexis, iris and sage tests also import their own modules.
- **ritzunit `glob_match`** is a correct linear wildcard matcher with backtracking.

## Tickets filed

AGAST was searched for "ritzunit" and "ritz1 --test". Two other searches returned HTTP 500. Existing tickets this touches: #1500, #1494, #1484, #1809, #1856, #1857.

| # | Title | Pri | Findings | Acceptance criteria |
|---|---|---|---|---|
| #1868 | One test harness for ritz0 and ritz1: compiler-emitted test table, ritzunit as the runner | 75 | C1, M1, M2, M3 (ritzunit parts) | (a) `git grep -nE 'run_batch_tests\|emit_test_main\|__init_tests\|run_tests_array' -- projects ':!*archive*'` is empty. (b) `./rz test ritzunit --compiler ritz1` runs its tests, and the "has no --test harness" line (`build.py:2298`) is gone. (c) Red then green: a non-`[[test]]` `fn test_x` is not run, and a `[[test]] fn check_x` is. (d) A suite with 300 failing tests exits non-zero. (e) A test that prints to stdout leaves `--json` output that parses. (f) Every `ritzunit/src` module is imported by at least one test. (g) `-j N` runs tests concurrently. Depends on #1500 and #1494; coordinate with G8 #1809. |
| #1869 | Language: `assert` reports operands and works in helpers (spec + ritz0 + ritz1) | 60 | M4 | (a) A failing `assert a == b` prints both values, checked by a spec `expect-error` example in `check-doc-examples`. (b) An assert in a helper called from a test reports the test's call site. (c) Afterwards, `git grep -nE '^(pub )?fn assert_eq_i(32\|64)\(' -- projects` is empty outside ritzunit. |
| #1870 | nexus: bounded response building, or archive nexus | 60 | C2, M11 | Either (a) red then green: a stored page of 8,192 `"` renders under valgrind with no invalid writes, no `[N]u8` response bodies remain in `main.ritz`, and the dead layer from M11 is deleted; or (b) nexus is moved out of `members`, with a `[workspace.exclude]` reason. |
| #1871 | Harland userland consolidation: ritzlib harland `sys_open`, one userland, loud image build | 55 (feeds #1857) | M7 | (a) `git grep -nE '^(pub )?fn sys_open\(' -- projects ':!projects/ritz/ritzlib' ':!projects/harland/kernel' ':!*archive*' ':!projects/ritz/ritz1/bootstrap_ritzlib'` is empty. (b) `harland/user` and rzsh's `main_{linux,harland}.ritz` are deleted. (c) `git grep -n '|| true' -- projects/indium/Makefile projects/indium/tools` is empty, and the image build fails when rzsh fails to build. |
| #1872 | Language: `\xNN` and `\e` escapes | 45 | M5 | (a) Spec `:224` lists them, with a compiled example. (b) ritz0 and ritz1 agree in the differential suite. (c) `git grep -nE '= 27 +# ESC' -- projects/ritzunit projects/rzsh` is empty. |
| #1873 | Tests must import production; `[[test]]` outside `test/` must run or fail | 40 | M3 (non-ritzunit parts) | (a) build.py runs or fails `[[test]]` functions under `src/`, red then green on angelo. (b) rzrz's tautology tests are deleted or rewritten to call `parse_args`. (c) prism `src/damage.ritz` is deleted, `test_damage` targets `compositor/damage`, and `test_core` imports `types`. |
| #1874 | Developer tools stop reporting false success | 35 | M8 | (a) Each unimplemented rzrz command exits non-zero with "not implemented", or is removed. (b) A child that writes 1 MiB to stderr does not hang `rzrz build`. (c) ritz-lsp's `initialize` response advertises only implemented capabilities, pinned by a test. |
| #1875 | Archive and cleanup sweep | 35 | M10, Minor, package table | (a) `git ls-files \| grep -E 'logs/claude_transcript\|\.pem$\|prism/hello\.ppm\|^projects/angelo/aadhunik\.ttf'` is empty. (b) spectree and angelo-simple are archived and ritzutils is merged. (c) `ritzunit/patches`, `ritzunit/known_issues` and `nexus/wiki` are removed. (d) The manifest paths in M10 are fixed, and `test_nested_packages.py` passes. |
| #1876 | Language: StrView literal patterns in `match`, then decompose the browser-stack hot spots when un-parked | 40 (language) / 20 (refactor) | M9 | (a) A spec §8.2 example matching `"html" => …` compiles under both compilers. (b) When un-parked, no lexis or sage function is over 150 SLOC or CC 80 (`ritz_metrics.py`). |
| → #1856 | Append evidence: package-level integer formatters and C string idioms | (existing) | M6 | As on #1856, plus: `git grep -nE 'fn (print_num\|write_number)\(' -- projects/{rzsh,indium,prism,angelo}` is empty. |

## Verification notes

- Re-checked by the LARB lead before filing: `run_tests_array` is defined nowhere (only emitted at `ritz0/emitter_llvmlite.py:12429`); nexus `MAX_CONTENT_LEN = 8192` (`store.ritz:37`) against `var body: [16384]u8` (`main.ritz:509`, `:743`) with `write_escaped` expanding `"` to 6 bytes; the gate never runs ritzunit.
- Inferred, not run: `test_runner.py --batch` failing to link after 5133247; the rzrz stdout/stderr pipe deadlock; the nexus/prism test-all failures (cited from tooling.md's CI run).
- AGAST duplicate checks for "test harness" and "nexus" were redone by the lead after the reviewer's searches failed; the only overlaps (#1377, #1697, #1345, #1484, #1268) are cross-referenced in the tickets.
- **Correction to ritzlib.md:** "Not dead: testing.ritz (ritz0 injects it)" is wrong. The injection only happens through `--emit-test-main`, which calls the undefined `run_tests_array`; only a golden test uses `testing.ritz`. ritzlib.md is amended in the same commit.
