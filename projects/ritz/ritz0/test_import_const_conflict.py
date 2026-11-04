"""Identical compound constants imported from two modules are not a conflict (#2112).

`ImportResolver._exprs_equal` used to compare only literal / array nodes and
return False for everything else, so `pub const X: i32 = -1` (a UnaryOp)
defined identically in two imported modules was rejected with
"Conflicting constant definition ... defined differently in multiple files".

Each case builds two sibling modules `ca` / `cb` that both define `X`, and a
main module `t` importing both.

* `test_identical_negative_const_runs`: the reported case, end-to-end on all
  three compilers (ritz1 never had the bug; it pins the behaviour).
* `test_identical_compound_const_resolves`: identical UnaryOp / BinOp /
  Ident / Cast values pass ritz0's import resolver.
* `test_identical_compound_const_runs`: the same values end-to-end on all
  three compilers (ritz0's emitter folds them since #2150).
* `test_differing_compound_const_rejected`: definitions that differ in one
  component (operator, operand, name, cast target) are still a conflict.
"""

import os
import subprocess
from pathlib import Path

import pytest

import module_interface
from import_resolver import ImportError as RitzImportError
from import_resolver import ImportResolver
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

CONFLICT = "Conflicting constant definition for 'X'"

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


def _resolve(tmp_path):
    """Run ritz0's import resolver over t.ritz exactly as ritz0.py does."""
    path = str(tmp_path / "t.ritz")
    module = module_interface.parse_source((tmp_path / "t.ritz").read_text(), path)
    resolver = ImportResolver(str(tmp_path), use_cache=False,
                              source_roots=[str(tmp_path)],
                              use_interfaces=module_interface.enabled())
    return resolver.resolve(module, path)


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


def _run(compiler, tmp_path):
    """Compile t, ca and cb to separate objects, link, run; return the exit code."""
    objs = []
    for name in ("t", "ca", "cb"):
        # ritz0 emits a _start unless told not to; only the main object may.
        extra = ("--no-runtime",) if compiler == "ritz0" and name != "t" else ()
        proc, ll = _compile(compiler, tmp_path, name, extra)
        out = proc.stderr + proc.stdout
        assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
        objs.append(str(ll))
    if compiler != "ritz0":
        objs.insert(0, str(RITZ_START))
    exe = tmp_path / f"t_{compiler}"
    link = subprocess.run(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_identical_negative_const_runs(compiler, tmp_path):
    _setup(tmp_path, "pub const X: i32 = -1", "pub const X: i32 = -1")
    assert _run(compiler, tmp_path) == 49


SAME = [
    ("unary_neg", "pub const X: i32 = -1"),
    ("binop", "pub const X: i32 = 2 + 3"),
    ("nested", "pub const X: i32 = (2 + 3) * 2"),
    ("ident", "pub const X: i32 = K * 2"),
    ("cast", "pub const X: i64 = -1 as i64"),
]


@pytest.mark.unit
@pytest.mark.parametrize("line", [s[1] for s in SAME], ids=[s[0] for s in SAME])
def test_identical_compound_const_resolves(tmp_path, line):
    _setup(tmp_path, line, line)
    module = _resolve(tmp_path)
    consts = [i for i in module.items if getattr(i, "name", None) == "X"]
    assert len(consts) == 1, consts


# main exits X + 50.
SAME_EXIT = {"unary_neg": 49, "binop": 55, "nested": 60, "ident": 58, "cast": 49}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("line", [s[1] for s in SAME], ids=[s[0] for s in SAME])
def test_identical_compound_const_runs(compiler, tmp_path, line):
    _setup(tmp_path, line, line)
    case = next(s[0] for s in SAME if s[1] == line)
    assert _run(compiler, tmp_path) == SAME_EXIT[case]


# (id, ca's line, cb's line): each pair differs in exactly one component.
DIFFERENT = [
    ("unary_operand", "pub const X: i32 = -1", "pub const X: i32 = -2"),
    ("unary_op", "pub const X: i32 = -1", "pub const X: i32 = !1"),
    ("binop_op", "pub const X: i32 = 2 + 3", "pub const X: i32 = 2 * 3"),
    ("binop_left", "pub const X: i32 = 2 + 3", "pub const X: i32 = 1 + 3"),
    ("binop_right", "pub const X: i32 = 2 + 3", "pub const X: i32 = 2 + 4"),
    ("nested_inner", "pub const X: i32 = (2 + 3) * 2", "pub const X: i32 = (2 + 4) * 2"),
    ("ident_name", "pub const X: i32 = K * 2", "pub const X: i32 = KK * 2"),
    ("cast_target", "pub const X: i64 = -1 as i64", "pub const X: i64 = -1 as u64"),
    ("cast_operand", "pub const X: i64 = -1 as i64", "pub const X: i64 = -2 as i64"),
]


@pytest.mark.unit
@pytest.mark.parametrize("a_line,b_line", [d[1:] for d in DIFFERENT],
                         ids=[d[0] for d in DIFFERENT])
def test_differing_compound_const_rejected(tmp_path, a_line, b_line):
    _setup(tmp_path, a_line, b_line)
    with pytest.raises(RitzImportError, match=CONFLICT):
        _resolve(tmp_path)
