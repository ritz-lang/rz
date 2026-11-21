"""Tests for tools/ritz1_ratchet.py (AGAST #4433, milestone M1.3).

M1.3's acceptance -- no hand-written fn > 300 SLOC, acyclic module graph,
ptr_len_param_pair <= 40 -- used to be prose that only `make arch-report`
printed.  This ratchet turns each measured number into a one-way gate: a
metric may improve, but may not get worse than the committed baseline.

The ratchet reads ritz_metrics.py's --json (the same numbers arch-report
prints) and excludes generated modules **by name**, as the milestone says
"outside generated code"; a size heuristic would silently stop excluding
`parser_gen` the day ritzgen emits a smaller file.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from ritz1_ratchet import (
    DEFAULT_BASELINE,
    DEFAULT_GENERATED,
    compare,
    load_baseline,
    main,
    measure,
    summarise,
)

pytestmark = pytest.mark.unit


def _metrics(files=None, functions=None):
    """A ritz_metrics --json dict, trimmed to what the ratchet reads."""
    return {"files": files or [], "functions": functions or []}


def _file(name, sloc=10, smells=None):
    return {
        "file": f"src/{name}.ritz",
        "lines": sloc,
        "sloc": sloc,
        "functions": 1,
        "smells": smells or {},
    }


def _fn(name, sloc, file="hand"):
    return {
        "file": f"src/{file}.ritz",
        "name": name,
        "line": 1,
        "length": sloc,
        "sloc": sloc,
        "complexity": 1,
        "max_depth": 1,
        "smells": {},
    }


def _baseline(**over):
    base = {
        "generated_modules": list(DEFAULT_GENERATED),
        "limits": {"fn_sloc": 300, "file_sloc": 3000},
        "scalars": {
            "hand_fns_over_sloc_limit": 1,
            "hand_files_over_sloc_limit": 1,
            "ptr_len_param_pair": 916,
            "i32_as_bool": 1689,
            "cstr_literal": 6763,
            "fixed_u8_buffer": 21,
            "cycle_sccs": 1,
            "cycle_modules": 16,
        },
        "long_fns": {"hand::big": 400},
        "large_files": {"hand": 4000},
        "cycle_module_names": ["a", "b"],
    }
    for k, v in over.items():
        # scalars are individual counters (merge); maps are replaced whole.
        if k == "scalars" and isinstance(v, dict):
            base[k].update(v)
        else:
            base[k] = v
    return base


# --------------------------------------------------------------------------
# Generated-module exclusion: explicit names, never a size heuristic.
# --------------------------------------------------------------------------


def test_generated_modules_are_excluded_from_long_fn_and_file_counts():
    data = _metrics(
        files=[_file("hand", sloc=100), _file("parser_gen", sloc=9000)],
        functions=[
            _fn("small", 100, "hand"),
            _fn("parse_primary_expr", 404, "parser_gen"),
        ],
    )
    m = summarise(data, cycle_sccs=0, cycle_module_names=[])
    assert m["scalars"]["hand_fns_over_sloc_limit"] == 0
    assert m["long_fns"] == {}
    assert m["scalars"]["hand_files_over_sloc_limit"] == 0
    assert m["large_files"] == {}


def test_a_large_non_generated_module_is_still_counted():
    """Exclusion is by name: a huge module not on the list is measured."""
    data = _metrics(
        files=[_file("bloated", sloc=8000)],
        functions=[_fn("big", 900, "bloated")],
    )
    m = summarise(data, cycle_sccs=0, cycle_module_names=[])
    assert m["scalars"]["hand_fns_over_sloc_limit"] == 1
    assert m["long_fns"] == {"bloated::big": 900}
    assert m["scalars"]["hand_files_over_sloc_limit"] == 1
    assert m["large_files"] == {"bloated": 8000}


def test_generated_name_match_is_exact_not_a_prefix():
    data = _metrics(functions=[_fn("big", 900, "parser_gen_extra")])
    m = summarise(data, cycle_sccs=0, cycle_module_names=[])
    assert m["long_fns"] == {"parser_gen_extra::big": 900}


def test_smell_totals_count_every_module_including_generated():
    """The ticket's ptr_len/i32/cstr baselines are whole-tree numbers."""
    data = _metrics(
        files=[
            _file(
                "hand",
                smells={
                    "ptr_len_param_pair": 5,
                    "i32_as_bool": 7,
                    "cstr_literal": 9,
                    "fixed_u8_buffer": 2,
                },
            ),
            _file(
                "parser_gen",
                smells={
                    "ptr_len_param_pair": 1,
                    "i32_as_bool": 1,
                    "cstr_literal": 3,
                    "fixed_u8_buffer": 0,
                },
            ),
        ]
    )
    m = summarise(data, cycle_sccs=1, cycle_module_names=["a", "b"])
    assert m["scalars"]["ptr_len_param_pair"] == 6
    assert m["scalars"]["i32_as_bool"] == 8
    assert m["scalars"]["cstr_literal"] == 12
    assert m["scalars"]["fixed_u8_buffer"] == 2
    assert m["scalars"]["cycle_sccs"] == 1
    assert m["scalars"]["cycle_modules"] == 2


# --------------------------------------------------------------------------
# Ratchet semantics.
# --------------------------------------------------------------------------


def test_at_baseline_has_no_findings():
    m = _baseline()
    assert compare(m, m) == []


def test_worse_scalar_regresses_and_names_metric_baseline_measured():
    m = _baseline(scalars={"ptr_len_param_pair": 917})
    findings = compare(m, _baseline())
    assert [f.kind for f in findings] == ["regression"]
    msg = findings[0].detail
    assert "ptr_len_param_pair" in msg
    assert "916" in msg and "917" in msg


def test_better_scalar_passes_and_reports_the_improvement():
    m = _baseline(scalars={"ptr_len_param_pair": 900})
    findings = compare(m, _baseline())
    assert [f.kind for f in findings] == ["improvement"]
    msg = findings[0].detail
    assert "ptr_len_param_pair" in msg
    assert "916" in msg and "900" in msg
    assert "--update" in msg


def test_long_fn_growing_regresses_names_the_fn():
    m = _baseline(long_fns={"hand::big": 420})
    findings = compare(m, _baseline())
    regs = [f for f in findings if f.kind == "regression"]
    assert len(regs) == 1
    assert "hand::big" in regs[0].detail
    assert "400" in regs[0].detail and "420" in regs[0].detail


def test_new_long_fn_regresses_even_if_the_count_is_unchanged():
    """One fn crosses 300 while another drops below: the new one must fail."""
    m = _baseline(long_fns={"hand::new": 301}, scalars={"hand_fns_over_sloc_limit": 1})
    findings = compare(m, _baseline())
    regs = [f for f in findings if f.kind == "regression"]
    assert any("hand::new" in f.detail for f in regs)


def test_long_fn_dropping_below_the_limit_is_an_improvement():
    m = _baseline(long_fns={}, scalars={"hand_fns_over_sloc_limit": 0})
    findings = compare(m, _baseline())
    kinds = {f.kind for f in findings}
    assert kinds == {"improvement"}
    assert any("hand::big" in f.detail for f in findings)


def test_large_file_growing_regresses_names_the_file():
    m = _baseline(large_files={"hand": 4500})
    findings = compare(m, _baseline())
    regs = [f for f in findings if f.kind == "regression"]
    assert any("hand" in f.detail and "4500" in f.detail for f in regs)


def test_cycle_module_joining_regresses():
    """A module that was outside the cycle may not join it."""
    m = _baseline(cycle_module_names=["a", "b", "c"], scalars={"cycle_modules": 17})
    findings = compare(m, _baseline())
    regs = [f for f in findings if f.kind == "regression"]
    assert any("c" in f.detail and "cycle" in f.detail.lower() for f in regs)


def test_cycle_splitting_into_more_sccs_regresses():
    m = _baseline(scalars={"cycle_sccs": 2})
    findings = compare(m, _baseline())
    assert any(f.kind == "regression" and "cycle" in f.detail.lower() for f in findings)


def test_cycle_shrinking_is_an_improvement():
    m = _baseline(
        cycle_module_names=["a"], scalars={"cycle_modules": 1, "cycle_sccs": 1}
    )
    findings = compare(m, _baseline())
    assert {f.kind for f in findings} == {"improvement"}


# --------------------------------------------------------------------------
# CLI: default is read-only; --update is the explicit refresh.
# --------------------------------------------------------------------------


def _write_baseline(path, base):
    path.write_text(json.dumps(base, indent=1))


def test_main_exit_1_on_regression(tmp_path):
    base = _baseline()
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, base)
    measured = _baseline(scalars={"ptr_len_param_pair": 917})
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(measured))
    before = bpath.read_text()
    assert main(["--measured", str(mpath), "--baseline", str(bpath)]) == 1
    assert bpath.read_text() == before  # never rewritten by a failing run


def test_main_exit_0_on_improvement_without_touching_baseline(tmp_path):
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(_baseline(scalars={"ptr_len_param_pair": 900})))
    before = bpath.read_text()
    assert main(["--measured", str(mpath), "--baseline", str(bpath)]) == 0
    assert bpath.read_text() == before


def test_update_records_the_measured_values(tmp_path):
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    measured = _baseline(scalars={"ptr_len_param_pair": 900})
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(measured))
    assert main(["--measured", str(mpath), "--baseline", str(bpath), "--update"]) == 0
    assert load_baseline(bpath)["scalars"]["ptr_len_param_pair"] == 900


# --------------------------------------------------------------------------
# The committed baseline describes this tree, and this tree does not
# regress it.  This is the gate `make tools-unit` runs.
# --------------------------------------------------------------------------


def test_committed_baseline_matches_this_tree():
    assert DEFAULT_BASELINE.exists(), DEFAULT_BASELINE
    measured = measure()
    findings = compare(measured, load_baseline(DEFAULT_BASELINE))
    regressions = [f for f in findings if f.kind == "regression"]
    assert regressions == [], "\n".join(f.detail for f in regressions)
