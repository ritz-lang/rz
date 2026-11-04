"""ritz1 rejects a constant defined differently in two imported modules (#2149).

Module `ca` has `pub const X: i32 = -1`, module `cb` has `pub const X: i32 =
-2`, and `t` imports both.  ritz0's import resolver rejects this with
"Conflicting constant definition for 'X': defined differently in multiple
files"; ritz1 used to accept it and silently pick one value.

Two definitions are the same iff they have the same declared type and a
structurally identical initializer (ritz0 `ImportResolver._consts_equal`),
so identical compound forms from #2112 (`-1`, arithmetic, names, casts) stay
accepted.  ritz0 is the oracle for every case: each test first asserts
ritz0's verdict, then that both ritz1 binaries agree.

* `test_differing_const_rejected`: pairs differing in one component.
* `test_identical_const_runs`: identical compound pairs compile, link and
  run on ritz1 with the right value.
* `test_local_vs_import_rejected` / `test_nested_import_rejected`: the
  conflict is caught between the main file and an import, and through an
  import of an import, as ritz0 does; `..._names_defining_file`: the
  diagnostic names the file that defined the clashing const.
* `test_gated_vs_ungated_accepted` / `test_gated_vs_gated_rejected`: ritz0
  never compares a `[[target_os]]` const with an ungated one (ritzunit's
  reporter.ritz relies on it), but two gated ones for the same target must
  match.
"""

import os
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

RITZ1S = ["ritz1", "ritz1_selfhosted"]

CONFLICT = "Conflicting constant definition for 'X': defined differently in multiple files"

MAIN = """import ca
import cb

fn main() -> i32
    (X as i32) + fa() - fb() + 50
"""


def _module(const_line, fn):
    """A module defining helpers K / KK, the constant `X`, and a fn reading X."""
    return (f"pub const K: i32 = 4\npub const KK: i32 = 4\n{const_line}\n"
            f"pub fn {fn}() -> i32\n    X as i32\n")


def _setup(tmp_path, a_line, b_line):
    (tmp_path / "ca.ritz").write_text(_module(a_line, "fa"))
    (tmp_path / "cb.ritz").write_text(_module(b_line, "fb"))
    (tmp_path / "t.ritz").write_text(MAIN)


def _compile(compiler, tmp_path, name, extra=()):
    src = tmp_path / f"{name}.ritz"
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    if compiler == "ritz0":
        proc = run_ritz0([str(src), "-o", str(ll), *extra], cwd=tmp_path, env=env,
                         timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary), str(src), "-o", str(ll)],
                              cwd=tmp_path, env=env, capture_output=True,
                              text=True, timeout=300)
    return proc, ll


def _assert_rejected(compiler, tmp_path, diag=CONFLICT):
    proc, _ = _compile(compiler, tmp_path, "t")
    out = proc.stderr + proc.stdout
    assert proc.returncode != 0, f"{compiler} accepted a conflicting const:\n{out}"
    assert diag in out, f"{compiler}: wrong diagnostic:\n{out}"


def _run_ritz1(compiler, tmp_path):
    """Compile t, ca and cb to separate objects, link, run; return the exit code."""
    objs = [str(RITZ_START)]
    for name in ("t", "ca", "cb"):
        proc, ll = _compile(compiler, tmp_path, name)
        out = proc.stderr + proc.stdout
        assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
        objs.append(str(ll))
    exe = tmp_path / f"t_{compiler}"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


# (id, ca's line, cb's line): each pair differs in exactly one component.
DIFFERENT = [
    ("int", "pub const X: i32 = 1", "pub const X: i32 = 2"),
    ("type", "pub const X: i32 = 1", "pub const X: i64 = 1"),
    ("unary_operand", "pub const X: i32 = -1", "pub const X: i32 = -2"),
    ("unary_op", "pub const X: i32 = -1", "pub const X: i32 = !1"),
    ("binop_op", "pub const X: i32 = 2 + 3", "pub const X: i32 = 2 * 3"),
    ("binop_left", "pub const X: i32 = 2 + 3", "pub const X: i32 = 1 + 3"),
    ("binop_right", "pub const X: i32 = 2 + 3", "pub const X: i32 = 2 + 4"),
    ("nested_inner", "pub const X: i32 = (2 + 3) * 2", "pub const X: i32 = (2 + 4) * 2"),
    ("ident_name", "pub const X: i32 = K * 2", "pub const X: i32 = KK * 2"),
    ("cast_target", "pub const X: i64 = -1 as i64", "pub const X: i64 = -1 as u64"),
    ("cast_operand", "pub const X: i64 = -1 as i64", "pub const X: i64 = -2 as i64"),
    # Same folded value, different expression: ritz0 compares structure.
    ("same_value", "pub const X: i32 = 5", "pub const X: i32 = 2 + 3"),
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("a_line,b_line", [d[1:] for d in DIFFERENT],
                         ids=[d[0] for d in DIFFERENT])
def test_differing_const_rejected(compiler, tmp_path, a_line, b_line):
    _setup(tmp_path, a_line, b_line)
    _assert_rejected("ritz0", tmp_path)
    _assert_rejected(compiler, tmp_path)


# (id, line, exit code of t = X + 50, ritz0 runs it).  ritz0's emitter lowers
# only literal and `-literal` const values, so for the compound forms its
# resolver accepting them is pinned by test_import_const_conflict instead.
SAME = [
    ("int", "pub const X: i32 = 7", 57, True),
    ("unary_neg", "pub const X: i32 = -1", 49, True),
    ("binop", "pub const X: i32 = 2 + 3", 55, False),
    ("nested", "pub const X: i32 = (2 + 3) * 2", 60, False),
    ("ident", "pub const X: i32 = K * 2", 58, False),
    ("cast", "pub const X: i64 = -1 as i64", 49, False),
]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("line,code,oracle", [s[1:] for s in SAME],
                         ids=[s[0] for s in SAME])
def test_identical_const_runs(compiler, tmp_path, line, code, oracle):
    _setup(tmp_path, line, line)
    if oracle:
        proc, _ = _compile("ritz0", tmp_path, "t")
        assert proc.returncode == 0, proc.stderr + proc.stdout
    assert _run_ritz1(compiler, tmp_path) == code


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_local_vs_import_rejected(compiler, tmp_path):
    (tmp_path / "ca.ritz").write_text(_module("pub const X: i32 = -1", "fa"))
    (tmp_path / "t.ritz").write_text(
        "import ca\n\nconst X: i32 = -2\n\nfn main() -> i32\n    X + fa() + 50\n")
    _assert_rejected("ritz0", tmp_path)
    _assert_rejected(compiler, tmp_path)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_nested_import_rejected(compiler, tmp_path):
    _setup(tmp_path, "pub const X: i32 = -1", "pub const Y: i32 = 0")
    (tmp_path / "cc.ritz").write_text("pub const X: i32 = -2\n")
    (tmp_path / "cb.ritz").write_text(
        "import cc\n\npub fn fb() -> i32\n    X as i32\n")
    _assert_rejected("ritz0", tmp_path)
    _assert_rejected(compiler, tmp_path)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_nested_import_names_defining_file(compiler, tmp_path):
    """The diagnostic points at cc.ritz, not cb.ritz that merged it in."""
    _setup(tmp_path, "pub const X: i32 = -1", "pub const Y: i32 = 0")
    (tmp_path / "cc.ritz").write_text("pub const Y: i32 = 0\npub const X: i32 = -2\n")
    (tmp_path / "cb.ritz").write_text(
        "import cc\n\npub fn fb() -> i32\n    X as i32\n")
    proc, _ = _compile(compiler, tmp_path, "t")
    assert f"{tmp_path / 'cc.ritz'}:2:1: {CONFLICT}" in proc.stderr + proc.stdout


GATED = '[[target_os = "linux"]]\npub const X: i32 = -1'


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_gated_vs_ungated_accepted(compiler, tmp_path):
    """ritz0 never compares a [[target_os]] const with an ungated one.

    ritzunit's reporter.ritz relies on it: its own `const TIOCGWINSZ: i64`
    sits beside ritzlib.sys's `[[target_os = "linux"]] ... u64` one.
    """
    _setup(tmp_path, GATED, "pub const X: i32 = -2")
    for c in ("ritz0", compiler):
        proc, _ = _compile(c, tmp_path, "t")
        assert proc.returncode == 0, f"{c}:\n{proc.stderr + proc.stdout}"


@pytest.mark.integration
@pytest.mark.parametrize("compiler", RITZ1S)
def test_gated_vs_gated_rejected(compiler, tmp_path):
    _setup(tmp_path, GATED, GATED.replace("-1", "-2"))
    diag = "Conflicting constant definition for 'X': defined differently for same target_os"
    _assert_rejected("ritz0", tmp_path, diag)
    _assert_rejected(compiler, tmp_path, diag)
