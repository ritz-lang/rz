"""Matrix test files must not share fixed /tmp paths (AGAST #1735).

run_regression_matrix.py submits (file, compiler) jobs file-major onto a
thread pool, so a file's ritz0, ritz1 and ritz1_selfhosted runs execute at
the same time -- and other rooms gate on the same host. test_level11 wrote
`/tmp/ritz_test_11b.txt` from all three: one run's O_TRUNC landed between
another's write and read-back, `assert n == 9` failed, and CI reported

    ritz1_selfhosted  test_level11  FAIL 6/7 [bad-exit]
    -> test_level11::test_write_multiple_chunks: bad-exit (code=1)

on 68396dd, then passed on the next commit. It looked like a miscompile from
alloca hoisting; it was a race that any compiler column could lose.

Two checks:
  * unit: no file in ritz0/test names a literal /tmp path, so the whole
    class of collision is caught before it gets a chance to flake.
  * integration: the level11 file tests run 4-way concurrently, many rounds,
    with zero failures. Against the fixed-path version this fails reliably
    (~1% of runs per test, over 800 runs per test).
"""

import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

MATRIX = Path(__file__).resolve().parent / "run_regression_matrix.py"


def _load():
    spec = importlib.util.spec_from_file_location("_matrix_hermetic", MATRIX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


matrix = _load()

# Any string literal (c"...", "...") whose value starts with /tmp/ -- except a
# name prefix ending in `_`, which exists to have a unique suffix (the pid)
# appended at runtime, as test_level11's l11_tmp_path does.
FIXED_TMP = re.compile(r'"/tmp/(?:[^"]*[^_"])?"')


def fixed_tmp_paths(src):
    """[(line_no, literal)] for every literal /tmp path in a Ritz source."""
    hits = []
    for n, line in enumerate(src.splitlines(), 1):
        code = line.split("#", 1)[0]
        hits += [(n, m.group(0)) for m in FIXED_TMP.finditer(code)]
    return hits


@pytest.mark.unit
def test_detector_flags_fixed_tmp_literal():
    src = 'fn f() -> i32\n  let p: *i8 = c"/tmp/ritz_test_11b.txt"\n  0\n'
    assert fixed_tmp_paths(src) == [(2, '"/tmp/ritz_test_11b.txt"')]


@pytest.mark.unit
def test_detector_ignores_comments_and_runtime_paths():
    src = (
        '# Note: these tests use /tmp\nfn f() -> i32\n  buf[0] = 47  # "/tmp/x"\n  0\n'
    )
    assert fixed_tmp_paths(src) == []


@pytest.mark.unit
def test_detector_allows_a_prefix_for_a_unique_suffix():
    src = '  let prefix: *i8 = c"/tmp/ritz_l11_"\n  let p: *i8 = c"/tmp/"\n'
    assert fixed_tmp_paths(src) == [(2, '"/tmp/"')]


@pytest.mark.unit
def test_no_matrix_test_file_uses_a_fixed_tmp_path():
    offenders = {
        path.name: hits
        for path in sorted(matrix.TEST_DIR.glob("*.ritz"))
        if (hits := fixed_tmp_paths(path.read_text()))
    }
    assert offenders == {}, (
        "matrix runs each file under 3 compilers concurrently; a fixed /tmp "
        f"path makes them race. Build a per-pid path instead: {offenders}"
    )


FILE_IO_TESTS = [
    "test_create_write_read_file",
    "test_write_multiple_chunks",
    "test_large_buffer",
]


@pytest.fixture(scope="module")
def level11_exe(tmp_path_factory):
    if not matrix.RUNTIME_O.exists():
        subprocess.run(
            ["make", "-s", "-C", str(matrix.RUNTIME_O.parent)],
            check=True,
            capture_output=True,
            timeout=120,
        )
    td = str(tmp_path_factory.mktemp("level11"))
    env = os.environ.copy()
    env["RITZ_PATH"] = matrix.RITZ_PATH_ENV
    objs, err = matrix.build_ritzlib_objs(td, env)
    assert not err, err
    base, _ = matrix.resolve_ritzlib_modules()
    deps = matrix.DepObjects(td, env, base, objs)
    results = matrix.run_file("test_level11", "ritz0", None, deps, env, td)
    bad = {u: r for u, r in results.items() if r[0] != "pass"}
    assert not bad, bad
    fns = [
        name
        for name, _ in matrix.find_test_fns(
            (matrix.TEST_DIR / "test_level11.ritz").read_text()
        )
    ]
    exe = Path(td) / "ritz0" / "test_level11" / "test_level11.exe"
    return exe, fns


@pytest.mark.integration
@pytest.mark.parametrize("test_fn", FILE_IO_TESTS)
def test_level11_file_io_survives_concurrent_runs(level11_exe, test_fn):
    exe, fns = level11_exe
    sel = matrix.selector_arg(fns.index(test_fn))
    failures = []
    for _ in range(200):
        procs = [
            subprocess.Popen([str(exe), sel], stderr=subprocess.PIPE) for _ in range(4)
        ]
        for p in procs:
            _, err = p.communicate(timeout=10)
            if p.returncode != 0:
                failures.append((p.returncode, err.decode(errors="replace").strip()))
    assert failures == [], f"{len(failures)}/800 concurrent runs failed: {failures[:3]}"
