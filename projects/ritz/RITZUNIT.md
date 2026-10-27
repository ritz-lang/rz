# Ritzunit

Ritzunit is the test runner of every Ritz test binary. The language side —
what a test is, how its result is read, the compiler-emitted test table — is
specified in `docs/LANGUAGE_SPEC.md` §17.1. The runner's options are in
`projects/ritzunit/README.md`.

## Writing tests

```ritz
[[test]]
fn test_addition() -> i32
    assert 2 + 2 == 4
    0
```

- `[[test]]` makes a function a test; its name does not. A helper named
  `test_setup` without the attribute is not run.
- A test takes no parameters and returns an integer or nothing. 0 (or
  nothing) passes; anything else fails. A failed `assert` exits with status 1
  and writes its diagnostic to stderr.
- Tests live in `test/*.ritz` of a package.

## Running tests

```bash
./rz test <project>
```

Each test file becomes one binary: the file compiled in test mode, linked with
ritzunit as `main`. It is run once; ritzunit forks a child per test, so a
crash, `exit` or hang is attributed to the test that caused it. Each test may
run for 10 s.

A test's stdout and stderr are captured. For a test that did not pass, they
are printed under its result. `./rz test` reports them in its failure list.

## Debugging a test

`ritz0/test_runner.py`'s `build_test_binary(source, scratch_dir)` builds a
file's binary without running it, which you can then run yourself:

```bash
$BIN -v            # each test as it runs
$BIN -f 'name*'    # only matching tests
$BIN --no-fork     # in-process, for a debugger (no output capture)
$BIN --json        # the report ./rz test reads
```
