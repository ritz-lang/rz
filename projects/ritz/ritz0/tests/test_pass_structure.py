"""ritz0's driver is an explicit pass list, and the move checker walks the AST
through per-node-kind dispatch tables (LARB review/5 ritz0 N2, AGAST #3449).

Both used to be one function each: `compile_file` reached 194 SLOC / CC 55
and `MoveChecker._check_expr` 220 SLOC / CC 106 / depth 11, so every new rule
went into the middle of a long if/elif chain.  These tests hold the shape and
the ticket's thresholds, measured with the same tool LARB reviews with
(projects/larb/tools/ritz-metrics), so the next growth spurt shows up in the
gate instead of in the next review.

No compiles here: each case reads source or a table, in milliseconds.
"""

import functools
import importlib.util
import sys
from pathlib import Path

import pytest

import move_checker
import ritz0
import ritz_ast as rast
from move_walk import MoveWalk

HERE = Path(__file__).resolve().parents[1]
METRICS_PY = HERE.parents[1] / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"


@functools.cache
def _metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_for_ritz0", METRICS_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


def _functions(name: str):
    path = HERE / name
    return _metrics().extract_functions(path, path.read_text().splitlines(), "py")


def _file_sloc(name: str) -> int:
    m = _metrics()
    return sum(1 for ln in (HERE / name).read_text().splitlines() if m.is_code(ln))


# --- compile_file: parse -> resolve -> check[] -> monomorph -> emit ---------

def test_compile_file_runs_the_pass_list_in_order():
    """The order is the old compile_file's, statement for statement: a pass
    that moved would change which error a broken program reports first.
    _lower_main (AGAST #200) is new: the entry adapter must exist before
    _resolve so it is checked and emitted like any fn.  _monomorph and
    _check_instances (AGAST #3523) ran first thing inside _emit.
    _rewrite_named_variants (AGAST #4187) is new: a named variant literal
    must be a call before _check_type_names takes its name for a type.
    The typing pass's errors (_check_types) are reported after _emit,
    before _write writes the .ll, so the emitter's words win where both
    refuse (AGAST #4260)."""
    assert [p.__name__ for p in ritz0.PASSES] == [
        "_parse", "_lower_main", "_resolve", "_check_impl_targets", "_rewrite_enum_from",
        "_rewrite_named_variants", "_eval_array_sizes", "_check_type_names", "_check_binders", "_check_reachable",
        "_check_names", "_infer_struct_lit_args", "_type",
        "_check_no_effect", "_check_ownership", "_monomorph", "_check_instances", "_emit",
        "_check_types", "_write",
    ]


def test_compile_file_stops_at_the_first_failing_pass(tmp_path, monkeypatch):
    """A pass returning False ends the compile: nothing after it runs and no
    output is written."""
    ran = []

    def failing(ctx):
        ran.append("fail")
        return False

    def after(ctx):
        ran.append("after")
        return True

    monkeypatch.setattr(ritz0, "PASSES", (failing, after))
    src = tmp_path / "a.ritz"
    src.write_text("fn main() -> i32\n    0\n")
    out = tmp_path / "a.ll"
    assert ritz0.compile_file(str(src), str(out)) is False
    assert ran == ["fail"]
    assert not out.exists()


def test_compile_file_is_within_the_n2_thresholds():
    (fn,) = [f for f in _functions("ritz0.py") if f.name == "compile_file"]
    assert fn.sloc <= 60 and fn.complexity <= 15, fn


# --- the move checker: per-kind dispatch ------------------------------------

@pytest.mark.parametrize("name", ["move_checker.py", "move_walk.py", "move_state.py"])
def test_move_checker_functions_are_within_the_n2_thresholds(name):
    over = [(f.name, f.line, f.sloc, f.complexity, f.max_depth)
            for f in _functions(name)
            if f.sloc > 100 or f.complexity > 30 or f.max_depth >= 6]
    assert over == [], over


@pytest.mark.parametrize("name", [
    "move_checker.py",
    # 1,868 and 2,314 SLOC before AGAST #3522 moved inference and rewriting
    # into monomorph_infer / monomorph_rewrite / monomorph_core, and slot
    # typing, reference rules and type queries into type_slots / type_refs /
    # type_queries.
    "monomorph.py",
    "type_checker.py",
])
def test_file_is_under_1500_sloc(name):
    assert _file_sloc(name) < 1500


def _node_kinds(base):
    return {c for c in vars(rast).values()
            if isinstance(c, type) and issubclass(c, base) and c is not base}


def test_every_dispatched_kind_is_a_direct_ast_kind():
    """Dispatch is on `type(node)`, which matches the old isinstance chains
    only while no listed kind has a subclass.  A new subclass of one would
    silently fall through to "no ownership effect"."""
    for table, base in ((MoveWalk.EXPR_CHECKS, rast.Expr),
                        (MoveWalk.STMT_CHECKS, rast.Stmt),
                        (move_checker.MoveChecker.EXPR_TYPES, rast.Expr)):
        kinds = _node_kinds(base)
        for kind in table:
            assert kind in kinds, kind
            assert not [c for c in kinds if c is not kind and issubclass(c, kind)], kind
