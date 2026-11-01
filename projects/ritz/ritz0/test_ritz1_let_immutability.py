"""ritz1 enforces `let` immutability exactly where ritz0 does (AGAST #2028).

ritz0 rejects every mutation of a `let`'s own storage since #2026 (and a
whole-binding `x = v` since before that). ritz1 accepted all of them, so the
two compilers disagreed about which programs are valid.

The case tables come from ritz0's own test_let_immutability.py, the single
source of truth for the rule, rather than being copied: a future change to
the rule cannot silently skip ritz1. Each case runs through ritz1 and
ritz1_selfhosted, since the acceptance asks for both.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent
RITZ1_DIR = RITZ_ROOT / "ritz1"
SELFHOSTED_BIN = RITZ1_DIR / "build" / "ritz1_selfhosted"

_spec = importlib.util.spec_from_file_location(
    "_ritz0_let_rule", HERE / "test_let_immutability.py")
RULE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RULE)

COMPILERS = ["ritz1", "ritz1_selfhosted"]

# ritz1-only cases on top of ritz0's tables: the whole-binding forms (ritz0
# tests those elsewhere) and the statement shapes ritz1's grammar gives
# their own AST kinds (`a[i] =`, `p.f[i] =`, compound forms).
EXTRA_REJECTED = [
    ("whole-binding", "let k: i64 = 4\nk = 5", "k", "whole"),
    ("whole-binding-compound", "let k: i64 = 4\nk += 5", "k", "whole"),
    ("small-array-elem-compound", "let a: [4]i64 = [1, 2, 3, 4]\na[0] += 9", "a", "assign"),
    ("large-array-field-elem-compound", "let b: Big = big_new()\nb.data[7] += 3", "b", "assign"),
    ("large-nested-field-compound", "let b: Big = big_new()\nb.pt.x += 3", "b", "assign"),
    ("borrow-in-call-arg", "let p = Pt { x: 1, y: 2 }\nlet n = pt_x(@&p)", "p", "borrow"),
    # An expression arm is checked by emit_match_arm_body, not emit_stmt.
    ("borrow-in-match-expr-arm",
     "let p = Pt { x: 1, y: 2 }\nlet o: Option<i64> = Some(3)\n"
     "let n = match o\n    Some(v) => pt_x(@&p)\n    None => 0", "p", "borrow"),
]

EXTRA_ACCEPTED = [
    ("var-whole-binding", "var k: i64 = 4\nk = 5\nk += 1"),
    ("var-shadows-scalar-let", "let k: i64 = 4\nvar k: i64 = 5\nk = 6\nlet q: *i64 = @&k"),
    ("let-ptr-deref", "var k: i64 = 4\nlet p: *i64 = @&k\n*p = 5"),
    ("let-ptr-compound-field", "var v = Pt { x: 1, y: 2 }\nlet p: *Pt = @&v\np.x += 3"),
    ("loop-var-after-let", "let i: i64 = 0\nvar s: i64 = 0\nfor i in 0..3\n    s += i"),
]


@pytest.fixture(scope="session")
def compilers(ritz1_bin):
    """{name: path} for ritz1 and ritz1_selfhosted.

    Only conftest.py builds (test_ritz1_session_build.py); the gate builds
    ritz1_selfhosted before pytest. Never skip (#1327).
    """
    assert SELFHOSTED_BIN.exists(), f"{SELFHOSTED_BIN} missing; run `make -C ritz1 bootstrap`"
    return {"ritz1": ritz1_bin, "ritz1_selfhosted": SELFHOSTED_BIN}


def _compile(binary, tmp_path, body):
    src = tmp_path / "prog.ritz"
    src.write_text(RULE.PRELUDE + "fn main() -> i32\n" + RULE._indent(body) + "    0\n")
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    r = subprocess.run([str(binary), str(src), "-o", str(tmp_path / "prog.ll")],
                       cwd=tmp_path, capture_output=True, text=True, env=env, timeout=300)
    return r, r.stdout + r.stderr


def _want(name, kind):
    if kind == "assign":
        return f"cannot assign through `let` binding `{name}`; declare it `var`"
    if kind == "whole":
        return f"cannot assign to `let` binding `{name}`; declare it `var`"
    return f"cannot borrow `let` binding `{name}` as mutable; declare it `var`"


REJECTED = list(RULE.REJECTED) + EXTRA_REJECTED
ACCEPTED = list(RULE.ACCEPTED) + EXTRA_ACCEPTED


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("body,name,kind", [r[1:] for r in REJECTED],
                         ids=[r[0] for r in REJECTED])
def test_ritz1_rejects_mutating_a_let(compilers, tmp_path, compiler, body, name, kind):
    r, out = _compile(compilers[compiler], tmp_path, body)
    assert r.returncode != 0, f"{compiler} compiled a mutation of `let {name}`:\n{body}"
    assert _want(name, kind) in out, out[-2000:]


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("body", [a[1] for a in ACCEPTED], ids=[a[0] for a in ACCEPTED])
def test_ritz1_accepts_non_let_mutation(compilers, tmp_path, compiler, body):
    """The load-bearing controls: without them, rejecting everything passes."""
    r, out = _compile(compilers[compiler], tmp_path, body)
    assert r.returncode == 0, f"{compiler} rejected:\n{body}\n{out[-2000:]}"
    assert "`let` binding" not in out


@pytest.mark.integration
def test_ritz1_let_diagnostic_is_located(compilers, tmp_path):
    """file:line:col points at the offending statement (line 2 of main's body)."""
    r, out = _compile(compilers["ritz1"], tmp_path, "let k: i64 = 4\nk = 5")
    line = RULE.PRELUDE.count("\n") + 3
    assert f"prog.ritz:{line}:" in out, out[-2000:]
