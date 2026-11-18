"""AGAST #200 (#198 Phase 1): the Ritz-native `main` and its one entry path.

    pub fn main()
    pub fn main(args: Span<StrView>)
    pub fn main(args: Span<StrView>, env: Span<StrView>)

each with or without `-> i32`; without it `main` returns 0. One `_start`
(runtime/ritz_start.x86_64.ll, or ritz0's inline copy) calls
`main(argc, argv, envp)`. For a Span main, or one with no return type, the
compiler renames the fn `__ritz_main` and adds an adapter `main` written in
Ritz (ritz0/main_abi.py, ritz1/src/main_abi.ritz). Any other shape is
refused at `main`.

Each RUNS row can fail for its own reason:
  span2       the adapter builds args and env (lengths, bytes, count)
  span1_tail  a `main` with no return type returns 0, even with an i32 tail
              (ritz0 returned the tail; ritz1 emitted `void @main`)
  unit        `pub fn main()`, the zero-ceremony shape, also returns 0
              over an i32 tail (ritz0 returned the tail)
  c_noret     a C-shaped main with no return type (`-> void` is none) gets
              argc/argv through the adapter
Each REFUSED row is one message. The C shapes' own behaviour is every other
test in the suite.
"""

import os
import re
import subprocess

import pytest

import main_abi
from conftest import RITZ_ROOT
from test_ref_into_value import COMPILERS, _assert_refused, _compile, _link

pytestmark = [pytest.mark.integration]

ARGS = ["hello", "wor"]
ENV = {"FOO": "1", "BAR": "22"}

RUNS = {
    "span2": ("""\
pub fn main(args: Span<StrView>, env: Span<StrView>) -> i32
    if args.len != 3
        return 101
    if args[1].len != 5 or args[1].ptr[0] != 'h' or args[2].ptr[2] != 'r'
        return 102
    if env.len != 2
        return 103
    var total: i64 = 0
    var i: i64 = 0
    while i < env.len
        total = total + env[i].len
        i = i + 1
    total as i32
""", len("FOO=1") + len("BAR=22")),
    "span1_tail": ("""\
fn seven() -> i32
    7

pub fn main(args: Span<StrView>)
    seven()
""", 0),
    "unit": ("""\
fn seven() -> i32
    7

pub fn main()
    seven()
""", 0),
    "c_noret": ("""\
fn main(argc: i32, argv: **u8) -> void
    let n: i32 = argc
""", 0),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(RUNS))
def test_main_shape_runs(tmp_path, compiler, name):
    src, want = RUNS[name]
    comp, ll, work = _compile(compiler, tmp_path, f"main_{name}", src)
    assert comp.returncode == 0 and ll.exists(), f"{compiler} refused {name}:\n{comp.stdout}{comp.stderr}"
    link, exe = _link(compiler, ll, work)
    assert link.returncode == 0, link.stderr[-2000:]
    got = subprocess.run([str(exe), *ARGS], env=ENV, capture_output=True, timeout=60).returncode
    assert got == want, f"{compiler}: {name} exited {got}, want {want}"


REFUSED = {
    "param": ("^pub fn main(n: i64) -> i32\n    0\n", main_abi.MSG_SHAPE),
    "three_spans": ("^pub fn main(a: Span<StrView>, b: Span<StrView>, c: Span<StrView>) -> i32\n    0\n",
                    main_abi.MSG_SHAPE),
    "ret": ("^pub fn main() -> i64\n    0\n", main_abi.MSG_RET),
    "not_pub": ("^fn main(args: Span<StrView>) -> i32\n    0\n", main_abi.MSG_PUB),
}


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(REFUSED))
def test_main_shape_refused(tmp_path, compiler, name):
    src, msg = REFUSED[name]
    _assert_refused(compiler, tmp_path, f"main_{name}", src, msg)


RITZ1_MAIN_ABI = RITZ_ROOT / "ritz1" / "src" / "main_abi.ritz"


def _ritz_strings(text: str) -> str:
    """Every `"..."` / `c"..."` literal in a Ritz source, unescaped and
    joined: what ritz1 says and generates, comparable with ritz0's."""
    lits = re.findall(r'c?"((?:[^"\\]|\\.)*)"', text)
    return "".join(bytes(s, "utf-8").decode("unicode_escape") for s in lits)


@pytest.mark.unit
def test_ritz1_says_and_generates_what_ritz0_does():
    """The messages and the runtime text are one spec in two compilers;
    the run/refuse rows above check behaviour, this checks the bytes."""
    ritz1 = _ritz_strings(RITZ1_MAIN_ABI.read_text())
    for text in (main_abi.MSG_SHAPE, main_abi.MSG_RET, main_abi.MSG_PUB, main_abi.RUNTIME_SOURCE):
        assert text in ritz1, f"ritz1/src/main_abi.ritz lacks:\n{text}"


@pytest.mark.unit
def test_one_entry_shim_per_os():
    """One entry path: runtime/ holds one `_start` per OS, each calling
    main(argc, argv, envp)."""
    shims = sorted(p.name for p in (RITZ_ROOT / "runtime").glob("*.ll"))
    assert shims == ["ritz_start.harland.x86_64.ll", "ritz_start.x86_64.ll"]
    for name in shims:
        text = (RITZ_ROOT / "runtime" / name).read_text()
        assert "declare i32 @main(i32 %argc, i8** %argv, i8** %envp)" in text, name
