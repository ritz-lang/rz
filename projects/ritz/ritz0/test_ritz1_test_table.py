"""AGAST #1908: ritz1 emits the `[[test]]` table that ritzunit runs.

Port of ritz0/test_test_table.py (#1868) to ritz1. `ritz1 --test-table`
compiles a file as the root of a test binary (LANGUAGE_SPEC.md §17.1):

    @__ritz_tests        [N x { { ptr, i64 } name, ptr run }]
    @__ritz_tests_count  i64 N
    @__ritz_test_table   ptr (ptr count)   -- what the runner calls
    @_start              calls the runner's main(argc, argv)

with one entry per `[[test]]` fn of the input file, in source order. The
attribute decides membership, not the `test_` prefix. `run` is always
`fn() -> i32`: a unit or non-i32 test is wrapped, 0 -> 0 and anything else
-> 1, so a test returning 256 cannot pass by truncation.

ritz1 caches a file's IR in its `.ritz.sig`. Test-mode IR is not the
module's IR, so test mode must neither be served from the sig nor write it.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"

pytestmark = pytest.mark.integration

SOURCE = """\
[[test]]
fn check_first() -> i32
    0

fn test_helper_not_a_test() -> i32
    1

[[test]]
fn test_unit()
    let x: i32 = 1

[[test]]
fn test_wide() -> i64
    256

[[test]]
fn test_flag() -> bool
    false
"""


def _compile(tmp_path: Path, src: str, *flags: str, name: str = "t"):
    path = tmp_path / f"{name}.ritz"
    if not path.exists() or path.read_text() != src:
        path.write_text(src)
    ll = tmp_path / f"{name}.ll"
    if ll.exists():
        ll.unlink()
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(RITZ1_BIN), str(path), "-o", str(ll), *flags],
                          cwd=tmp_path, env=env, capture_output=True, text=True,
                          timeout=120)
    return proc, ll


def _ir(tmp_path: Path, src: str, test_mode: bool = True) -> str:
    proc, ll = _compile(tmp_path, src, *(["--test-table"] if test_mode else []))
    assert proc.returncode == 0, proc.stderr
    return ll.read_text()


def _table(ir: str) -> str:
    table = re.search(r'^@__ritz_tests = .*$', ir, re.M)
    assert table, f"no @__ritz_tests in test-mode IR:\n{ir}"
    return table.group(0)


def _table_names(ir: str) -> list:
    """Names in @__ritz_tests, in order, decoded from their string constants."""
    names = []
    for gname, length in re.findall(r'ptr @(__ritz_test_name\.\d+), i64 (\d+)', _table(ir)):
        const = re.search(rf'^@{re.escape(gname)} = .*c"([^"]*)"', ir, re.M)
        assert const.group(1).endswith("\\00"), "names are NUL-terminated"
        names.append(const.group(1)[:-3])
        assert int(length) == len(names[-1]), "len excludes the NUL"
    return names


def _clang_ok(tmp_path: Path, ir: str) -> None:
    ll = tmp_path / "verify.ll"
    ll.write_text(ir)
    r = subprocess.run(["clang", "-c", "-O2", "-Wno-override-module", str(ll),
                        "-o", str(tmp_path / "verify.o")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_table_lists_exactly_the_test_attributed_functions_in_order(ritz1_bin, tmp_path):
    """[[test]] decides membership: `check_first` is in, `test_helper_*` is out."""
    assert _table_names(_ir(tmp_path, SOURCE)) == [
        "check_first", "test_unit", "test_wide", "test_flag"]


def test_count_and_accessor_are_emitted_with_external_linkage(ritz1_bin, tmp_path):
    ir = _ir(tmp_path, SOURCE)
    assert re.search(r'^@__ritz_tests_count = constant i64 4$', ir, re.M), ir
    accessor = re.search(r'^define .*@__ritz_test_table\(.*$', ir, re.M)
    assert accessor, ir
    assert "internal" not in accessor.group(0) and "private" not in accessor.group(0)
    assert re.search(r'store i64 4, ptr %count', ir), ir


def test_every_entry_is_called_as_fn_returning_i32(ritz1_bin, tmp_path):
    """i32 tests go in directly; unit/i64/bool ones through an i32 wrapper.

    `test_wide` returns 256. Truncated to an exit status that is 0: a pass.
    """
    ir = _ir(tmp_path, SOURCE)
    table = _table(ir)
    assert "ptr @check_first }" in table, table
    for name in ("test_unit", "test_wide", "test_flag"):
        assert f"ptr @{name} " not in table, f"{name} must be wrapped: {table}"
    wide = re.search(r'^define internal i32 @__ritz_test_run\.\d+\(\) \{\n(?:(?!^\}).*\n)*'
                     r'.*call i64 @test_wide\(\)\n(?:(?!^\}).*\n)*\}', ir, re.M)
    assert wide, ir
    assert "icmp ne i64" in wide.group(0) and "trunc" not in wide.group(0), wide.group(0)
    unit = re.search(r'call void @test_unit\(\)\n  ret i32 0', ir)
    assert unit, ir
    assert re.search(r'call i1 @test_flag\(\)\n  %failed = icmp ne i1 %r, 0', ir), ir


def test_test_mode_starts_in_the_runners_main(ritz1_bin, tmp_path):
    """The test file has no `main`; _start calls ritzunit's `main(argc, argv)`."""
    ir = _ir(tmp_path, SOURCE)
    assert "define void @_start() naked" in ir
    assert "call main" in ir
    assert "leaq 8(%rsp), %rsi" in ir  # argv is passed
    assert re.search(r'^declare i32 @main\(i32, ptr\)$', ir, re.M), ir


def test_test_mode_drops_the_files_own_main(ritz1_bin, tmp_path):
    """A file's own `main` would clash with the runner's: test mode leaves it out."""
    ir = _ir(tmp_path, SOURCE + "\nfn main() -> i32\n    42\n")
    assert not re.search(r'^define .*@main\(', ir, re.M), ir


def test_normal_mode_emits_no_table(ritz1_bin, tmp_path):
    ir = _ir(tmp_path, SOURCE + "\nfn main() -> i32\n    42\n", test_mode=False)
    assert "__ritz_tests" not in ir and "__ritz_test_table" not in ir
    assert "@_start" not in ir
    assert re.search(r'^define .*@main\(', ir, re.M), ir


def test_file_without_tests_has_an_empty_table(ritz1_bin, tmp_path):
    ir = _ir(tmp_path, "fn helper() -> i32\n    0\n")
    assert re.search(r'^@__ritz_tests_count = constant i64 0$', ir, re.M), ir
    assert re.search(r'^@__ritz_tests = constant \[0 x .*zeroinitializer$', ir, re.M), ir
    _clang_ok(tmp_path, ir)


def test_imported_tests_are_not_this_files_tests(ritz1_bin, tmp_path):
    """A [[test]] fn of an imported module belongs to that module's binary."""
    (tmp_path / "dep.ritz").write_text("[[test]]\npub fn test_in_dep() -> i32\n    0\n")
    ir = _ir(tmp_path, "import dep\n\n[[test]]\nfn test_here() -> i32\n    0\n")
    assert _table_names(ir) == ["test_here"]


def test_target_os_filtered_test_is_not_in_the_table(ritz1_bin, tmp_path):
    src = ('[[test]]\n[[target_os = "harland"]]\nfn test_other_os() -> i32\n    0\n\n'
           '[[test]]\nfn test_linux() -> i32\n    0\n')
    assert _table_names(_ir(tmp_path, src)) == ["test_linux"]


def test_attribute_does_not_leak_to_the_next_item(ritz1_bin, tmp_path):
    """`[[test]]` on an item that is not added must not mark the fn after it.

    It used to be `[[test]]` on a struct; that is a located error since
    AGAST #1847 (LANGUAGE_SPEC §17), so the item here is a fn that
    `target_os` filters out — its dispatcher must still clear the note.
    """
    src = ('[[test]]\n[[target_os = "harland"]]\nfn test_other_os() -> i32\n    0\n\n'
           'fn test_after_filtered() -> i32\n    0\n')
    assert _table_names(_ir(tmp_path, src)) == []


def test_test_with_parameters_is_rejected(ritz1_bin, tmp_path):
    proc, ll = _compile(tmp_path, "[[test]]\nfn takes_arg(x: i32) -> i32\n    x\n",
                        "--test-table")
    assert proc.returncode != 0 and not ll.exists()
    assert re.search(r"\[\[test\]\] function 'takes_arg'.*no parameters", proc.stderr), proc.stderr


def test_test_with_non_integer_result_is_rejected(ritz1_bin, tmp_path):
    proc, ll = _compile(tmp_path, "[[test]]\nfn gives_ptr() -> *u8\n    null\n",
                        "--test-table")
    assert proc.returncode != 0 and not ll.exists()
    assert re.search(r"\[\[test\]\] function 'gives_ptr'.*must return", proc.stderr), proc.stderr


def test_test_mode_ir_passes_clang(ritz1_bin, tmp_path):
    _clang_ok(tmp_path, _ir(tmp_path, SOURCE + "\nfn main() -> i32\n    42\n"))


def test_test_mode_neither_reads_nor_writes_the_sig_cache(ritz1_bin, tmp_path):
    """Normal, test, normal, test: each output is its own mode's IR.

    ritz1 serves an unchanged file's IR from its `.ritz.sig`. Served in test
    mode, the table would be missing; written by test mode, a later normal
    build would get the table and lose `main`.
    """
    src = SOURCE + "\nfn main() -> i32\n    42\n"
    for _ in range(2):
        normal = _ir(tmp_path, src, test_mode=False)
        assert "__ritz_tests" not in normal and re.search(r'^define .*@main\(', normal, re.M)
        test = _ir(tmp_path, src)
        assert "__ritz_tests" in test and not re.search(r'^define .*@main\(', test, re.M)


# --- end to end: a ritz1-built test binary, ritzunit included ---------------

E2E_SOURCE = """\
import ritzlib.sys

struct Slot
    pid: i64
    done: u8

fn test_helper_not_a_test() -> i32
    1

[[test]]
fn check_runs_without_the_prefix() -> i32
    0

[[test]]
fn test_wide_nonzero_fails() -> i64
    256

[[test]]
fn test_unit_passes()
    let x: i32 = 1

[[test]]
fn test_fails() -> i32
    3

[[test]]
fn test_ptr_index_member() -> i32
    var buf: [3]Slot
    let p: *Slot = @buf[0]
    p[2].pid = 7
    let q: *Slot = @p[2]
    if q.pid != 7
        return 1
    0

fn main() -> i32
    42
"""


def test_ritz1_test_binary_runs_exactly_the_test_table(ritz1_bin, tmp_path, monkeypatch):
    """Acceptance (#1908): under ritz1, `fn test_x` is not run, `[[test]] fn check_x` is.

    The whole binary (test file, ritzlib, ritzunit's runner) is ritz1's.
    """
    import json
    import sys
    sys.path.insert(0, str(RITZ_ROOT / "ritz0"))
    import test_runner

    monkeypatch.setenv("RITZ_PATH", str(RITZ_ROOT))
    src = tmp_path / "test_e2e.ritz"
    src.write_text(E2E_SOURCE)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    calls = []
    real_run = test_runner.subprocess.run

    def spy(cmd, *a, **kw):
        calls.append([str(c) for c in cmd])
        return real_run(cmd, *a, **kw)

    monkeypatch.setattr(test_runner.subprocess, "run", spy)
    exe, error = test_runner.build_test_binary(str(src), str(scratch), "ritz1")
    monkeypatch.setattr(test_runner.subprocess, "run", real_run)
    assert error is None, error
    # ritz1 built it: ritz0 compiled nothing, and the harness is ritz1's test mode.
    assert not [c for c in calls if any(x.endswith("ritz0.py") for x in c)], calls
    assert [c for c in calls if c[0] == str(RITZ1_BIN) and "--test-table" in c
            and c[1] == str(src.resolve())], calls
    run = subprocess.run([exe, *test_runner.runner_args()], capture_output=True, timeout=60)
    assert run.returncode == 1, run  # one test failed
    report = json.loads(run.stdout)
    status = {t["name"]: t["status"] for t in report["tests"]}
    assert status == {
        "check_runs_without_the_prefix": "pass",
        "test_wide_nonzero_fails": "fail",
        "test_unit_passes": "pass",
        "test_fails": "fail",
        "test_ptr_index_member": "pass",
    }, report
