# Cutover survey

The counts that `../../../razm/DESIGN.md` "Coverage before the switch" asks
for before `build_pipeline.py` calls rllvm (AGAST #4807). The frozen corpus
beside this file stays the routine test. This is a one-time measurement over
real emitted IR, repeated by hand when the emitter or the subset changes.

## Command

```bash
./rz test rllvm --survey DIR [--profile hosted|shim|small-pic|kernel|large]
```

It builds rllvm, then runs it on every `.ll` under DIR with the profile's
argv (`corpus.PROFILE_FLAGS`, the same argv clang gets). It builds no IR.
Each file gets one line, `accepted`, `rejected FILE:LINE CONSTRUCT` (exit 2),
or `failed` (exit 1, a signal or a timeout). Then come the rejected
constructs, most files first, and a summary line. It exits 1 if any file
failed, since the pipeline treats a failure as a build error with no
fallback, or if DIR holds no `.ll`.

## Counts (base `4fa5cf0c4`, 2026-11-27)

The subset is ritz1's IR (DESIGN "LLVM IR subset"), so ritz1 is the
cutover's input:

| Profile | IR | Files | Accepted | Rejected | Failed |
|---|---|---:|---:|---:|---:|
| hosted | rllvm's and ritzlib's modules (pipeline) + ritzlib's 64 test modules | 115 | 115 | 0 | 0 |
| kernel | `harland` kernel modules | 155 | 155 | 0 | 0 |
| small-pic | `indium`, every bin but `minimal_syscall` (the `pic` bins and their imports) | 75 | 75 | 0 | 0 |
| large | `indium` `minimal_syscall` | 1 | 1 | 0 | 0 |

The same packages built by ritz0 (the default `--compiler`):

| Profile | Files | Accepted | Rejected | Failed |
|---|---:|---:|---:|---:|
| hosted (pipeline modules) | 49 | 0 | 49 | 0 |
| kernel | 155 | 0 | 155 | 0 |
| small-pic | 75 | 0 | 75 | 0 |
| large | 1 | 0 | 1 | 0 |

## Outcomes

- **ritz1:** no construct is rejected, so none is added to the subset and no
  file stays on clang.
- **ritz0:** every file stays on clang through the exit-2 fallback. The first
  construct rllvm reports is one of three, all part of ritz0's dialect rather
  than gaps in the subset:
  - `type 'metadata'`: the `llvm.dbg.declare` declaration ritz0 writes in
    every module that has locals.
  - `typed pointer '<T>*'`: any pointee other than `i8`, `i8*` and
    `[1 x i8]`, for example `i32*` or `%"struct.ritz_module_1.StrView"*`.
  - `function type '<T> (...)'`: a typed function pointer, `i8* (i64)*`.
    Before #4807 this exited 1 (`expected '}'`), a build failure with no
    fallback, in 18 small-pic files. It now exits 2.

  Adding these would mean accepting ritz0's typed-pointer IR, and DESIGN
  scopes the subset to ritz1's. ritz0 builds keep clang.

## How the IR was produced

The IR is a `--debug` build's, uncached so that every module is emitted:

```bash
export RITZ_PATH=$PWD/projects/ritz:$PWD/projects
python3 projects/ritz/build.py build projects/indium  -g --no-cache --compiler ritz1   # build/debug/obj/
python3 projects/ritz/build.py build projects/harland -g --no-cache --compiler ritz1   # build/debug/obj/
python3 projects/ritz/build.py build projects/rllvm   -g --no-cache --compiler ritz1   # projects/ritz/build/
# ritzlib's test modules, as corpus/regen.sh compiles a source:
(cd projects/ritz/ritzlib/tests && ritz1 test_X.ritz -o OUT/test_X.ll -I ../.. -I .)
```

A package's bins share one `obj/` directory, so the per-profile directories
were split by hand. `minimal_syscall_*.ll` is the large set, and indium's
other `.ll` files are the small-pic set. For the kernel set, harland's ten
modules last written by a UEFI bin are left out (ritz0 marks them
`x86_64-unknown-uefi`; ritz1 writes one triple for every target). Four of
those (`digits`, `cmp`, `option`, `strview`) are also kernel imports, and
the hosted and small-pic sets accept them.

## After the survey (AGAST #4808)

The cutover's first builder run met one construct the survey's IR did not
have: ritz1 now writes an ownership mask wider than `i32` as a `u0x` hex
literal (`ritz1/src/ownership.ritz` `own_set_const`), first in buddhafinger.
rllvm exited 1 on it (`expected a constant`), a build failure. `u0x` and
`s0x` literals are now in the subset (`lex.ritz` `is_prefixed_hex`,
`tests/test_lower.py` `test_hex_integer_literals_match_clang`).
