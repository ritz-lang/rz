# known-failures/

Every failure any gate excuses, one file per AGAST ticket (`<agast>.toml`),
read by one parser and judged by one rule: `projects/ritz/tools/known_failures.py`
(AGAST #1834). No gate keeps a private list.

```toml
[[entry]]
gate     = "matrix"             # build | parity | matrix | regression | examples | doc
compiler = "ritz1"              # which compiler the excuse holds under
unit     = "test_trait_bounds"  # what failed, in the gate's own key
reason   = "trait bounds on generic params"
agast    = 1621                 # the ticket; must equal the file name
```

| gate | read by | compiler | unit |
|------|---------|----------|------|
| `build` | `rz build --all`, `rz test --all`, train.sh package tests | `any` (every compiler), or ritz0, ritz1, ritz1_selfhosted (that sweep only) | rz project id (`lexis`, `ritz/ritzlib/tests`) |
| `parity` | `rz test --all --compiler C` (C's sweep only; never ritz0) | ritz1, ritz1_selfhosted | rz project id whose tests pass under ritz0 |
| `matrix` | `tools/run_regression_matrix.py` | ritz0, ritz1, ritz1_selfhosted | `file` (its build failures only) or `file::fn` |
| `regression` | `scripts/regression.sh` (via the CLI) | ritz0, ritz1 (covers ritz1_selfhosted) | example key: path under `examples/`, `/` → `_` |
| `examples` | `tools/example_tests.py` | ritz0 | test file under `examples/` |
| `doc` | `tools/check_doc_examples.py` | ritz1, ritz1_selfhosted | `<DOC.md> <12-hex block digest>` |
| `refusal` | `tools/refusal_parity.py` (in the "ritz0 unit tests" step) | ritz1 | ritz0 test id, `tests/test_x.py::name[param]`, of a ritz0-only file |

## Rules (enforced by the parser, so no gate can honour a bad excuse)

- Every entry cites the AGAST ticket tracking the failure, as `agast` and as
  the file name. Fixing the ticket deletes its file, so two fixes never touch
  the same hunk (the reason this is a directory, AGAST #3963).
- An excused unit that fails is **advisory**: printed with its ticket.
- An excused unit that **passes** fails the gate (strict xpass): the list
  only shrinks. One that did not run (a filtered sweep) is neither.
- An unexcused failure always gates. No continue-on-error anywhere.
- Some things are never excusable, and have no gate name to write:
  - **Stage 5** of `scripts/regression.sh` compares ritz1's and
    ritz1_selfhosted's accept sets with no list at all. Two compilers
    disagreeing is a self-hosting bug. That is also why a `regression` ritz1
    entry covers ritz1_selfhosted, and a selfhosted-only one is refused.
  - **A test-side excuse** for `rz test --all` under ritz0, the reference. A
    behavioural failure is never excusable. A package that cannot compile
    also fails its tests, so the test sweep reads the `build` entries.
    Under ritz1 or ritz1_selfhosted it also reads `parity` (AGAST #4591):
    a package that builds there but whose tests pass only under ritz0 is a
    self-hosted compiler bug, tracked like the matrix's per-fn ritz1
    entries. It never applies to ritz0's sweep, and the build sweep ignores it.
- New entries are not prevented, only stale ones. Review additions.

`python3 projects/ritz/tools/known_failures.py check` validates every file;
`... list --gate G --compiler C` and `... verdict --gate G --compiler C UNIT
pass|fail` are what shell callers use.

## Deliberately not listed

- `build` harland: bootx64 fails locally only ("lld-link not found"). CI
  installs lld via `.github/actions/install-toolchain`; an entry would encode a
  local-environment artifact and xpass-fail the first correct CI link.
- pytest's own `xfail(strict=True)` markers in `projects/ritz/ritz0` stay
  where they are: pytest already applies strict xpass to them, per test.
