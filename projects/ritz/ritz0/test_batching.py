#!/usr/bin/env python3
"""batching.py: one compile for a matrix's rows (AGAST #2806).

The merger is pure text and tested in process; the runners compile real
programs with ritz0, so a crash, a refusal or a wrong answer in one row is
shown not to cost any other row its own verdict.
"""

import os
import subprocess
from pathlib import Path

import pytest

import batching
import fast_link
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
ENV = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))


def _row(body, entry="    f()\n", top=""):
    return f"{top}{body}\npub fn main() -> i32\n{entry}"


# ---- merge: pure text ----------------------------------------------------

@pytest.mark.unit
def test_rows_become_functions_and_main_dispatches_on_argc():
    m = batching.merge([_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    4\n")])
    assert "fn __row0() -> i32" in m.text and "fn __row1() -> i32" in m.text
    assert "pub fn main(argc: i32, argv: **u8) -> i32" in m.text
    assert "    if argc == 1\n        return __row0()\n" in m.text
    assert "    if argc == 2\n        return __row1()\n" in m.text
    assert m.ok == [True, True]


@pytest.mark.unit
def test_names_that_collide_are_renamed_per_row():
    m = batching.merge([_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    4\n")])
    assert "fn f__r0() -> i32\n    3\n" in m.text
    assert "fn f__r1() -> i32\n    4\n" in m.text
    assert "fn __row0() -> i32\n    f__r0()\n" in m.text
    assert "\nfn f()" not in m.text


@pytest.mark.unit
def test_an_identical_item_is_shared_once_and_keeps_its_name():
    pre = "struct P\n    x: i32\n\n"
    m = batching.merge([_row(pre + "fn f() -> i32\n    3\n"), _row(pre + "fn f() -> i32\n    4\n")])
    assert m.text.count("struct P\n") == 1
    assert "P__r" not in m.text


@pytest.mark.unit
def test_an_item_that_uses_a_renamed_name_is_not_shared():
    # `h` is the same text in both rows, but each must call its own row's `g`.
    rows = [_row(f"fn g() -> i32\n    {n}\n\nfn h() -> i32\n    g()\n\nfn f() -> i32\n    h()\n")
            for n in (3, 4)]
    m = batching.merge(rows)
    assert "fn h__r0() -> i32\n    g__r0()\n" in m.text
    assert "fn h__r1() -> i32\n    g__r1()\n" in m.text


@pytest.mark.unit
def test_a_renamed_type_renames_its_uses_and_enum_variants():
    rows = [_row(f"enum E\n    A\n    B{n}\n\nfn f() -> i32\n    var e: E = A\n    0\n") for n in (1, 2)]
    m = batching.merge(rows)
    assert "enum E__r0\n    A__r0\n    B1\n" in m.text
    assert "var e: E__r1 = A__r1" in m.text


@pytest.mark.unit
def test_methods_of_a_shared_type_are_renamed_when_they_collide():
    pre = "struct R\n    n: i32\n\n"
    rows = [_row(pre + f"impl R\n    fn g(self: *R) -> i32\n        {n}\n\n"
                 "fn f() -> i32\n    var r: R = R { n: 0 }\n    r.g()\n") for n in (3, 4)]
    m = batching.merge(rows)
    assert m.text.count("struct R\n") == 1
    assert "fn g__r0(self: *R)" in m.text and "r.g__r1()" in m.text


@pytest.mark.unit
def test_strings_and_comments_are_not_renamed():
    rows = [_row('fn f() -> i32\n    let s: *u8 = c"f"  # f\n    3\n'), _row("fn f() -> i32\n    4\n")]
    m = batching.merge(rows)
    assert 'let s: *u8 = c"f"  # f\n' in m.text


@pytest.mark.unit
def test_imports_are_hoisted_once():
    rows = [_row("fn f() -> i32\n    3\n", top="import ritzlib.gvec\n\n"),
            _row("fn f() -> i32\n    4\n", top="import ritzlib.gvec\nimport ritzlib.span\n\n")]
    m = batching.merge(rows)
    assert m.text.startswith("import ritzlib.gvec\nimport ritzlib.span\n")
    assert m.text.count("import ritzlib.gvec") == 1


@pytest.mark.unit
def test_a_row_with_no_plain_main_is_left_out():
    rows = [_row("fn f() -> i32\n    3\n"), "fn main(argc: i32, argv: **u8) -> i32\n    0\n"]
    m = batching.merge(rows)
    assert m.ok == [True, False]
    assert "__row1" not in m.text


@pytest.mark.unit
def test_a_mark_lands_where_its_row_lands_after_renaming():
    rows = [_row("fn f() -> i32\n    3\n"),
            _row("fn g(b: i64) -> i32\n    3\n\nfn f() -> i32\n    g(\x01f)\n")]
    m = batching.merge(rows)
    assert "\x01" not in m.text
    line, col = (int(x) for x in m.marks[1].split(":"))
    assert m.text.splitlines()[line - 1][col - 1:].startswith("f__r1)")
    assert m.marks[0] is None


@pytest.mark.unit
def test_every_line_of_a_row_is_in_its_region_and_no_other():
    rows = [_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    4\n")]
    m = batching.merge(rows)
    lines = m.text.splitlines()
    (a0, a1), (b0, b1) = m.regions
    assert a1 < b0
    assert "fn __row0" in "\n".join(lines[a0 - 1:a1]) and "fn __row1" in "\n".join(lines[b0 - 1:b1])
    assert batching.row_of(m, a0) == 0 and batching.row_of(m, b1) == 1
    assert batching.row_of(m, len(lines)) is None  # the dispatching main


@pytest.mark.unit
def test_suffixes_come_off_a_rows_diagnostics():
    assert batching.unrename("main.ritz:9:5: H__r12.b wants f__r3") == "main.ritz:9:5: H.b wants f"


# ---- leaning: what a row's own module needs from outside (AGAST #2867) -----

_LL = '''\
@.str = private constant [2 x i8] c"@\\00"
@"g$i32" = global i32 0
define i32 @"vec_get$i32"(ptr %v, i64 %i) {
  %r = call i64 @realloc(ptr null, i64 0)
  ret i32 0
}
define weak_odr i32 @f__r2(i64 %p) {
  ret i32 0
}
declare i64 @realloc(...)
declare i64 @"Vec$i32_get"(...)
declare void @llvm.memset.p0.i64(ptr, i8, i64, i1)
declare i32 @f__r3(...)
'''


@pytest.mark.unit
def test_externals_are_what_a_module_declares():
    # Intrinsics are the backend's own; a row's renamed names come back as the row's.
    assert batching.externals(_LL) == {"realloc", "Vec$i32_get", "f"}


@pytest.mark.unit
def test_a_row_leans_on_what_it_needs_from_outside_and_the_batch_did_not():
    # #2519's ritz1 bug: alone, the row lowers `w.get(1)` to an external
    # `Vec$i32_get` because nothing registered `vec_get$i32`; batched, another
    # row registered it and the call resolved.
    row = "declare i64 @realloc(...)\ndeclare i64 @\"Vec$i32_get\"(...)\n"
    batch = "define i32 @\"vec_get$i32\"(ptr %v) {\n  ret i32 0\n}\ndeclare i64 @realloc(...)\n"
    assert batching.leans(row, batch) == {"Vec$i32_get"}
    assert batching.leans("declare i64 @realloc(...)\n", batch) == set()


_REACH = '''\
define i32 @__row0() {
  %r = call i32 @f__r0()
  ret i32 %r
}
define i32 @f__r0() {
  %v = alloca %"Vec$i32"
  ret i32 0
}
define i32 @__row1() {
  %r = call i32 @g()
  ret i32 %r
}
define i32 @g() {
  ret i32 0
}
declare i32 @"h$i32"(...)
'''


@pytest.mark.unit
def test_a_row_reaches_a_generic_instance_through_its_calls_and_types():
    # __row0 calls f__r0, whose body holds a Vec$i32; __row1's calls hold none
    # (the `$` in a declare after g's body is no part of it); __row2 isn't
    # there, and what isn't known is checked.
    assert batching.reaches_generic(_REACH, ["__row0", "__row1", "__row2"]) == {"__row0", "__row2"}


# ---- runners: real compiles, ritz0 ----------------------------------------

def _build(compiler, src, work):
    ll = work / "main.ll"
    comp = run_ritz0([str(src), "-o", str(ll)], cwd=work, env=ENV, timeout=300)
    if comp.returncode != 0 or not ll.exists():
        return False, comp.stdout + comp.stderr, None
    exe = work / "main"
    link = fast_link.clang(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"],
                           cwd=work, capture_output=True, text=True)
    return link.returncode == 0, link.stderr, exe if link.returncode == 0 else None


def _compile(compiler, src, work):
    comp = run_ritz0([str(src), "-o", str(work / "main.ll")], cwd=work, env=ENV, timeout=300)
    return comp.returncode, comp.stdout + comp.stderr


@pytest.mark.integration
def test_each_row_answers_for_itself(tmp_path):
    rows = [_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    4\n"),
            _row("fn f() -> i32\n    var p: *i32 = 0 as *i32\n    *p\n"),  # crashes
            _row("fn f() -> i32\n    5\n")]
    assert batching.run_rows("ritz0", rows, _build, tmp_path, compile=_compile) == [3, 4, None, 5]


@pytest.mark.integration
def test_a_row_that_does_not_compile_costs_no_other_row(tmp_path):
    rows = [_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    undefined_thing()\n"),
            _row("fn f() -> i32\n    5\n")]
    assert batching.run_rows("ritz0", rows, _build, tmp_path, compile=_compile) == [3, None, 5]


def _vec(n):
    return f"fn f() -> i32\n    var v: Vec<i32> = vec_new<i32>()\n    v.len as i32 + {n}\n"


GVEC = "import ritzlib.gvec\n\n"


@pytest.mark.integration
def test_a_row_that_only_compiles_beside_another_gets_no_answer(tmp_path):
    # Imports are hoisted into the batch, so row 1's `vec_new` is row 0's
    # import's.  Alone, row 1 is "Unknown function: vec_new" (AGAST #2867).
    rows = [_row(_vec(4), top=GVEC), _row(_vec(4))]
    assert batching.run_rows("ritz0", rows, _build, tmp_path, compile=_compile) == [4, None]


def _compile_failing(marker):
    """`_compile`, failing alone any row whose program holds `marker`."""
    def compile(compiler, src, work):
        if marker in src.read_text():
            return 1, "alone, no"
        return _compile(compiler, src, work)
    return compile


@pytest.mark.integration
def test_a_row_missing_an_import_the_batch_has_is_compiled_alone(tmp_path):
    # Row 1 reaches nothing generic: its import set is what makes it suspect.
    rows = [_row("fn f() -> i32\n    3\n", top="import ritzlib.str\n\n"), _row("fn f() -> i32\n    4\n")]
    compile = _compile_failing("    4\n")
    assert batching.run_rows("ritz0", rows, _build, tmp_path, compile=compile) == [3, None]


@pytest.mark.integration
def test_a_row_that_reaches_no_instance_is_not_compiled_alone(tmp_path):
    # Same imports, nothing generic: nothing another row emits can be its.
    def compile(compiler, src, work):
        raise AssertionError("compiled alone")
    rows = [_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    4\n")]
    assert batching.run_rows("ritz0", rows, _build, tmp_path, compile=compile) == [3, 4]


@pytest.mark.integration
def test_a_row_that_leans_on_another_rows_instance_gets_no_answer(tmp_path):
    # #2519's shape, with the compiler's bug played by `compile`: alone, row 1's
    # module wants an instance only the batch defines, and would not link.
    def compile(compiler, src, work):
        code, out = _compile(compiler, src, work)
        if "+ 4\n" in src.read_text():
            with open(work / "main.ll", "a") as fh:
                fh.write('\ndeclare i32 @"vec_get$i32"(...)\n')
        return code, out
    rows = [_row(_vec(n), top=GVEC) for n in (3, 4, 5)]
    assert batching.run_rows("ritz0", rows, _build, tmp_path, compile=compile) == [3, None, 5]


@pytest.mark.unit
def test_a_batched_run_needs_the_rows_own_compile():
    # Without one the batch can't tell a row that leans on another (#2867).
    with pytest.raises(TypeError):
        batching.run("ritz0", _row("fn f() -> i32\n    3\n"), _build)


@pytest.mark.integration
def test_each_refusal_gets_its_own_diagnostics(tmp_path):
    # ritz0's checker reports every element-type mismatch in a file.
    rows = [_row(f"fn f(a: [4]{t}) -> i32\n    var b: [4]i32 = \x01a\n    3\n") for t in ("i64", "u32")]
    rows.insert(1, _row("fn f() -> i32\n    3\n"))  # accepted: no diagnostic of its own
    got = batching.refuse_rows("ritz0", rows, _compile, tmp_path)
    assert got[1] is None
    for i in (0, 2):
        out, where = got[i]
        assert f"main.ritz:{where}: an array only fits" in out, (where, out)
        assert out.count("\n") == 1, out
    assert len(list(tmp_path.iterdir())) == 1, "one compile"


@pytest.mark.integration
def test_a_compiler_that_stops_at_its_first_error_answers_one_row(tmp_path):
    # ritz0's emitter stops at its first error: the other rows are left to compile alone.
    rows = [_row(f"fn f() -> i32\n    var y: bool = \x01{n}\n    3\n") for n in (1, 2, 3)]
    got = batching.refuse_rows("ritz0", rows, _compile, tmp_path)
    assert got[1:] == [None, None]
    assert "cannot use an integer as bool" in got[0][0]


@pytest.mark.integration
def test_an_accepted_batch_answers_no_refusal(tmp_path):
    rows = [_row("fn f() -> i32\n    3\n"), _row("fn f() -> i32\n    4\n")]
    assert batching.refuse_rows("ritz0", rows, _compile, tmp_path) == [None, None]


# ---- the pytest side: kill switch ----------------------------------------

@pytest.mark.unit
def test_batching_is_off_outside_a_batched_test():
    assert batching.run("ritz0", _row("fn f() -> i32\n    3\n"), _build, compile=_compile) is None
    assert batching.refused("ritz0", _row("fn f() -> i32\n    3\n"), _compile) is None


@pytest.mark.unit
def test_the_env_switch_turns_it_off(monkeypatch):
    monkeypatch.setenv("RITZ_TEST_BATCH", "0")
    assert not batching.enabled()
    monkeypatch.setenv("RITZ_TEST_BATCH", "1")
    assert batching.enabled()


# ---- the pytest side: a nested session ----------------------------------

_NESTED_CONFTEST = '''
import pytest
import batching

def pytest_configure(config):
    for name in ("batched", "unit", "integration"):
        config.addinivalue_line("markers", name + ": x")

@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):
    batching.assign_groups(items)

@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    return batching.pyfunc_call(pyfuncitem)
'''

_NESTED_TESTS = '''
import itertools
import os
import subprocess
import pytest
import batching
import test_batching as tb

pytestmark = pytest.mark.batched

# name -> (what the row returns, what the test wants)
ROWS = {"a": (3, 3), "b": (4, 4), "c": (5, 5), "wrong": (7, 6)}
_drift = itertools.count()


def _program(name):
    got = ROWS[name][0] if name != "drifts" else 8 + next(_drift)  # a new program per call
    return f"fn f() -> i32\\n    {got}\\n\\npub fn main() -> i32\\n    f()\\n"


def _run(tmp_path, name):
    got = batching.run("ritz0", _program(name), tb._build, compile=tb._compile)
    if got is not None:
        return got
    with open(os.environ["PER_ROW_LOG"], "a") as fh:
        fh.write(name + "\\n")
    ok, out, exe = tb._build("ritz0", _write(tmp_path, _program(name)), tmp_path)
    assert ok, out
    return subprocess.run([str(exe)]).returncode


def _write(tmp_path, text):
    src = tmp_path / "main.ritz"
    src.write_text(text)
    return src


@pytest.mark.parametrize("name", sorted(ROWS) + ["drifts"])
def test_row(tmp_path, name):
    want = ROWS[name][1] if name in ROWS else None
    got = _run(tmp_path, name)
    assert want is None or got == want, f"{name}: got {got}"
'''


def _nested(tmp_path, *args, batch="1"):
    (tmp_path / "conftest.py").write_text(_NESTED_CONFTEST)
    (tmp_path / "test_nested.py").write_text(_NESTED_TESTS)
    log, per_row = tmp_path / "batch.log", tmp_path / "per_row.log"
    env = dict(ENV, PYTHONPATH=str(Path(__file__).resolve().parent), RITZ_TEST_BATCH=batch,
               RITZ_TEST_BATCH_LOG=str(log), PER_ROW_LOG=str(per_row))
    proc = subprocess.run(
        ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--disable-plugin-autoload",
         "-p", "xdist", "--basetemp", str(tmp_path / "base"), *args, "test_nested.py"],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300, check=False)
    read = (lambda p: p.read_text().splitlines() if p.exists() else [])
    return proc, read(log), read(per_row)


@pytest.mark.integration
@pytest.mark.parametrize("workers", [[], ["-n", "2", "--dist", "loadgroup"]], ids=["serial", "xdist"])
def test_one_compile_answers_the_rows_and_a_failure_is_its_own(tmp_path, workers):
    proc, log, per_row = _nested(tmp_path, *workers)
    out = proc.stdout + proc.stderr
    assert "1 failed, 4 passed" in out, out
    # The failure is the per-row run's, with its own message.
    assert "wrong: got 7" in out, out
    compiles = [ln for ln in log if " run ritz0 " in ln]
    assert len(compiles) == 1 and "rows=5 answered=5" in compiles[0], log
    # Retried per row: the wrong row.  Compiled per row: it, and the row whose
    # live program is not the one recorded.
    assert [ln.split()[-1].split("::")[1] for ln in log if " retry " in ln] == \
        ["test_row[wrong]" + ("@" + compiles[0].split("@")[1].split()[0] if "@" in compiles[0] else "")]
    assert sorted(per_row) == ["drifts", "wrong"], per_row
    assert any(" miss changed " in ln and "drifts" in ln for ln in log), log


@pytest.mark.integration
def test_off_compiles_every_row_alone(tmp_path):
    proc, log, per_row = _nested(tmp_path, batch="0")
    assert "1 failed, 4 passed" in proc.stdout, proc.stdout + proc.stderr
    assert log == [] and sorted(per_row) == ["a", "b", "c", "drifts", "wrong"]


@pytest.mark.unit
def test_a_per_row_compile_while_recording_leaves_the_row_out():
    batching.per_row()  # no batched test running: nothing to do
    batching._active = batching._Context(item=None, mode="record")
    try:
        with pytest.raises(batching._Recorded) as rec:
            batching.per_row()
        assert rec.value.call is None
    finally:
        batching._active = None
