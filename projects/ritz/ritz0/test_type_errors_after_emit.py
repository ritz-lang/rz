"""The typing pass's errors are reported on every compile, after emission
(AGAST #4260).

#3556 took the typing pass to zero false errors, but reporting them before
emission swapped the emitter's actionable words (which the 3-compiler
matrices pin, and ritz1 shares) for generic ones.  So ritz0 emits first and
reports type errors only when the emitter accepted the program: every
emitter message stays, and an ill-typed program the emitter would lower is
still refused, with no .ll (or .ritz.sig claiming it) left behind.
"""

import subprocess
import sys
from pathlib import Path

import pytest

import ritz0
from emitter.fn_cache import sig_path_for
from test_typing_pass_only import compile_typing_only

# The emitter lowers this; the typing pass refuses it.
EMITTER_LOWERS = "fn main() -> i32\n    let x: i32 = c\"no\"\n    0\n"
# Both refuse: the emitter's words win (test_string_literal_slots' row).
BOTH_REFUSE = ("fn main() -> i32\n    var s: String = String.new()\n"
               "    let p: *u8 = s\n    0\n")

RITZ_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _ritzlib(monkeypatch):
    """ritzlib.string resolves whatever RITZ_PATH the caller runs with."""
    monkeypatch.setenv("RITZ_PATH", str(RITZ_ROOT))


def _compile(tmp_path, capsys, source):
    src, ll = tmp_path / "a.ritz", tmp_path / "a.ll"
    src.write_text(source)
    ok = ritz0.compile_file(str(src), str(ll))
    out = capsys.readouterr()
    return ok, out.out + out.err, src, ll


def test_type_errors_report_after_the_emitter():
    names = [p.__name__ for p in ritz0.PASSES]
    assert names.index("_emit") < names.index("_check_types") < names.index("_write")


def test_an_ill_typed_program_the_emitter_lowers_is_refused(tmp_path, capsys):
    ok, out, src, ll = _compile(tmp_path, capsys, EMITTER_LOWERS)
    assert ok is False, out
    assert "Type error: " in out and "a.ritz:2:5: cannot initialize i32 with *u8" in out, out
    assert not ll.exists()
    assert not Path(sig_path_for(str(src.resolve()))).exists()


def test_a_refused_program_is_refused_again_not_skipped(tmp_path, capsys):
    """No .ritz.sig records the refused compile as up to date."""
    _compile(tmp_path, capsys, EMITTER_LOWERS)
    ok, out, _, ll = _compile(tmp_path, capsys, EMITTER_LOWERS)
    assert ok is False and "Skipped" not in out, out
    assert not ll.exists()


def test_a_stale_ll_is_not_left_behind(tmp_path, capsys):
    (tmp_path / "a.ll").write_text("; stale\n")
    ok, out, _, ll = _compile(tmp_path, capsys, EMITTER_LOWERS)
    assert ok is False, out
    assert not ll.exists()


def test_the_emitter_s_words_win_when_both_refuse(tmp_path, capsys):
    ok, out, _, _ = _compile(tmp_path, capsys, "import ritzlib.string\n\n" + BOTH_REFUSE)
    assert ok is False, out
    assert "a String is not a `*u8`" in out, out
    assert "Type error: " not in out, out


def test_a_well_typed_program_still_compiles(tmp_path, capsys):
    ok, out, _, ll = _compile(tmp_path, capsys, "fn main() -> i32\n    0\n")
    assert ok is True, out
    assert ll.exists()


@pytest.mark.integration
def test_the_check_types_flag_is_gone(tmp_path):
    src = tmp_path / "a.ritz"
    src.write_text("fn main() -> i32\n    0\n")
    r = subprocess.run([sys.executable, str(Path(__file__).with_name("ritz0.py")),
                        str(src), "-o", str(tmp_path / "a.ll"), "--check-types"],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "--check-types" in r.stderr, r.stderr


def test_a_generic_instance_is_judged_at_the_source_level(tmp_path, capsys):
    """_check_types runs after _monomorph, whose module's table names an
    instance mangled (`Box$i32`): the errors it reports are the source
    module's, which _type kept (ritz1's `@&Vec<String>` args were refused)."""
    ok, out, _, ll = _compile(tmp_path, capsys,
                              "struct Box<T>\n    v: T\n\n"
                              "var g_box: Box<i32>\n\n"
                              "fn get<T>(b: @Box<T>) -> T\n    b.v\n\n"
                              "fn main() -> i32\n    get<i32>(@g_box)\n")
    assert ok is True, out
    assert ll.exists()


# A `name:& T` slot is physically a pointer (AGAST #3034), so a fn with one
# fits a `fn(@T)` slot (test_ritz1_borrow_array.py's fn_value row).
LENT_AS_VALUE = ("fn f(a:& [2]i32) -> i32\n    return a[1]\n\n"
                 "fn main() -> i32\n    let h: fn(@[2]i32) -> i32 = f\n"
                 "    var b: [2]i32 = [1, 3]\n    return h(@b)\n")


def test_a_lent_slot_fits_a_reference_param_of_a_fn_type(tmp_path, capsys):
    ok, out, _, ll = _compile(tmp_path, capsys, LENT_AS_VALUE)
    assert ok is True, out
    assert ll.exists()


def test_a_lent_slot_still_needs_its_pointee(tmp_path, capsys):
    ok, out, _, _ = _compile(tmp_path, capsys,
                             LENT_AS_VALUE.replace("fn(@[2]i32)", "fn(@i32)")
                             .replace("return h(@b)", "return h(@b[0])"))
    assert ok is False, out


# Rules the typing pass lacked, which the emitter lowers: each was a refused
# row of test_ritz1_whole_array.py once the typing pass's errors reported.
BYTES = ("fn g(s: StrView) -> i32\n    return s.len as i32\n\n"
         "pub fn main() -> i32\n    var a: [3]u8 = [0, 0, 3]\n"
         "    var b: [3]i8 = [0, 0, 3]\n    var c: [3]i32 = [0, 0, 3]\n")


@pytest.mark.parametrize("use", [
    "let s: StrView = a\n    return s.len as i32",
    "let s: StrView = @a\n    return s.len as i32",
    "return g(a)", "return g(@a)", "return g(b)", "return g(@b)",
])
def test_a_byte_array_views_as_a_strview(tmp_path, capsys, use):
    """`[N]u8` / `[N]i8`, bare or `@`, is `StrView { &a[0], N }`."""
    ok, out, _, _ = _compile(tmp_path, capsys, BYTES + "    " + use + "\n")
    assert ok is True, out


@pytest.mark.parametrize("use", ["return g(c)", "return g(@c)"])
def test_another_array_is_no_strview(tmp_path, use):
    """The typing pass's verdict: the emitter refuses these too, first."""
    src = tmp_path / "a.ritz"
    src.write_text(BYTES + "    " + use + "\n")
    r = compile_typing_only(src, tmp_path / "a.ll", ritz_path=RITZ_ROOT)
    assert r.returncode != 0 and "expected StrView" in r.stderr, r.stdout + r.stderr


GENERIC_ELEM = ("struct Box<T>\n    v: T\n    w: i64\n\n"
                "fn g<T>(a: [3]Box<T>) -> T\n    return a[2].v\n\n"
                "pub fn main() -> i32\n    var a: [3]Box<i32>\n    a[2].v = 3\n")


@pytest.mark.parametrize("call", ["g<i32>(a)", "g(a)"])
def test_an_array_of_a_generic_fits_its_type_param_s_slot(tmp_path, capsys, call):
    ok, out, _, _ = _compile(tmp_path, capsys, GENERIC_ELEM + f"    return {call}\n")
    assert ok is True, out


def test_an_array_of_another_generic_instance_is_refused(tmp_path):
    """Box<i64> elements aren't Box<i32>'s: same name, other args."""
    src = GENERIC_ELEM.replace("fn g<T>(a: [3]Box<T>) -> T", "fn g(a: [3]Box<i64>) -> i64") \
        .replace("    return a[2].v\n", "    return a[2].v\n")
    path = tmp_path / "a.ritz"
    path.write_text(src + "    return g(a) as i32\n")
    r = compile_typing_only(path, tmp_path / "a.ll", ritz_path=RITZ_ROOT)
    assert r.returncode != 0 and "Type error: " in r.stderr and "same element type" in r.stderr, \
        r.stdout + r.stderr


# Methods the emitter dispatches that the typing pass never declares
# (test_method_needs_impl.py's deref_target_method and vec_len_builtin).
DEREF_METHOD = ("struct Inner\n    x: i32\n\nimpl Inner\n    fn get(self: @Inner) -> i32\n"
                "        self.x\n\nstruct Wrap\n    inner: Inner\n\nimpl Deref for Wrap\n"
                "    fn deref(self: @Wrap) -> @Inner\n        @self.inner\n\n"
                "pub fn main() -> i32\n    let w = Wrap { inner: Inner { x: 7 } }\n    w.get()\n")
VEC_LEN = ("struct Vec<T>\n    data: *T\n    len: i64\n    cap: i64\n\n"
           "pub fn main() -> i32\n    let v = Vec<i32> { data: null, len: 3, cap: 0 }\n"
           "    v.len() as i32\n")


@pytest.mark.parametrize("src", [DEREF_METHOD, VEC_LEN], ids=["deref_target", "vec_len"])
def test_a_method_the_emitter_dispatches_is_no_type_error(tmp_path, capsys, src):
    ok, out, _, _ = _compile(tmp_path, capsys, src)
    assert ok is True, out


def test_a_deref_target_s_missing_method_is_still_refused(tmp_path, capsys):
    ok, out, _, _ = _compile(tmp_path, capsys, DEREF_METHOD.replace("w.get()", "w.nope()"))
    assert ok is False, out


# LANGUAGE_SPEC's byte pointer (LARB R71): any `*T` or `@T` fits a `*u8`,
# and a `*u8` fits any `*T` (the spec's own example, docs line ~796).
BYTE_POINTER = ("fn first(p: *[3]i32) -> i32\n    p[0]\n\n"
                "fn main() -> i32\n    var g: [4]i32\n    g[0] = 7\n"
                "    let q: *[4]i32 = @g\n    let bytes: *u8 = q\n"
                "    first(bytes) + first(q as *[3]i32) - 14\n")


def test_the_byte_pointer_is_the_way_between(tmp_path, capsys):
    ok, out, _, _ = _compile(tmp_path, capsys, BYTE_POINTER)
    assert ok is True, out


def test_other_pointees_still_differ(tmp_path):
    """The typing pass's verdict: `*[4]i32` into `*i64` isn't the byte pointer."""
    src = tmp_path / "a.ritz"
    src.write_text("fn main() -> i32\n    var g: [4]i32\n    let q: *[4]i32 = @g\n"
                   "    let w: *i64 = q\n    0\n")
    r = compile_typing_only(src, tmp_path / "a.ll", ritz_path=RITZ_ROOT)
    assert r.returncode != 0 and "Type error: " in r.stderr, r.stdout + r.stderr


# LARB R79: any async fn's generated future (`u_Future`) fits a reference to a
# `Future`, at a user fn's `@&Future` param too, not just `future_poll`'s
# (test_async_future_ref's named_future_and_unit_fn).
DRIVE = "fn drive(f: @&Future) -> i32\n    var n: i32 = 1\n    while !future_poll(f)\n        n = n + 1\n    n\n\n"


def test_an_async_fn_s_future_fits_a_future_ref(tmp_path, capsys):
    ok, out, _, _ = _compile(tmp_path, capsys,
                             "var DONE: i32 = 0\n\nasync fn u()\n    DONE = 5\n\n" + DRIVE
                             + "pub fn main() -> i32\n    var p: u_Future = u()\n    drive(@&p)\n    DONE\n")
    assert ok is True, out


def test_another_struct_is_no_future(tmp_path):
    """The typing pass's verdict: a plain struct isn't some async fn's future."""
    src = tmp_path / "a.ritz"
    src.write_text("struct S\n    x: i32\n\n" + DRIVE
                   + "pub fn main() -> i32\n    var s = S { x: 1 }\n    drive(@&s)\n")
    r = compile_typing_only(src, tmp_path / "a.ll", ritz_path=RITZ_ROOT)
    assert r.returncode != 0 and "expected @&Future, got @&S" in r.stderr, r.stdout + r.stderr
