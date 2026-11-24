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
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from ritz1_ratchet import (
    DEFAULT_ACCEPT,
    DEFAULT_BASELINE,
    DEFAULT_GENERATED,
    acceptance_deltas,
    compare,
    effective_baseline,
    load_acceptances,
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


# The real tree's measurement, ~5 s: taken once and shared by the two tests
# that grade it, which one xdist group keeps on one worker (AGAST #4672: each
# measured it again, and they were the long pole of `make tools-ratchets`).
_TREE_GROUP = pytest.mark.xdist_group("ritz1_ratchet_tree")


@pytest.fixture(scope="module")
def tree_measured():
    return measure()


@_TREE_GROUP
def test_milestone_ptr_len_param_pair_target_is_met(tree_measured):
    """M1.3 (#1830) sets ptr_len_param_pair <= 40.  AGAST #4449 converted the
    ritz1 `(*u8, len)` parameter pairs to StrView, so the real tree must stay
    at or under that target — the ratchet's one-way baseline alone would only
    hold it at the old 923."""
    measured = tree_measured
    assert measured["scalars"]["ptr_len_param_pair"] <= 40


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
    assert "no record" in msg


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


def _empty_accept(tmp_path):
    """A private acceptance dir: this test's verdict must not move when a
    ticket in the repo's own tools/ratchet_accept raises the metric it
    measures (AGAST #4448: a room's acceptance is part of the default
    allowance, so the default dir is not a fixture an isolated test can use).
    """
    return str(tmp_path / "no-accept")


def test_main_exit_1_on_regression(tmp_path):
    base = _baseline()
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, base)
    measured = _baseline(scalars={"ptr_len_param_pair": 917})
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(measured))
    before = bpath.read_text()
    assert main(["--measured", str(mpath), "--baseline", str(bpath),
                 "--accept-dir", _empty_accept(tmp_path)]) == 1
    assert bpath.read_text() == before  # never rewritten by a failing run


def test_main_exit_0_on_improvement_without_touching_baseline(tmp_path):
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(_baseline(scalars={"ptr_len_param_pair": 900})))
    before = bpath.read_text()
    assert main(["--measured", str(mpath), "--baseline", str(bpath),
                 "--accept-dir", _empty_accept(tmp_path)]) == 0
    assert bpath.read_text() == before


# --------------------------------------------------------------------------
# One acceptance file per ticket (AGAST #4447): the shared blob is the base
# and is never rewritten by a room, so two rooms raising the same metric touch
# different files and cherry-pick in either order.  This is the repo's
# merge-magnet idiom from #3963 (known-failures/<ticket>.toml).
# --------------------------------------------------------------------------


def _accept(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return path


def test_update_accepts_a_raise_in_a_per_ticket_file(tmp_path):
    """--update is a deliberate acceptance, written per ticket; the shared
    base blob stays byte-identical so unrelated rooms never share a hunk."""
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    adir = tmp_path / "ratchet_accept"
    measured = _baseline(scalars={"ptr_len_param_pair": 917})
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(measured))
    before = bpath.read_text()

    rc = main(
        [
            "--measured",
            str(mpath),
            "--baseline",
            str(bpath),
            "--accept-dir",
            str(adir),
            "--ticket",
            "4447",
            "--update",
        ]
    )
    assert rc == 0
    assert bpath.read_text() == before  # the merge magnet is not touched
    files = sorted(p.name for p in adir.glob("*.json"))
    assert files == ["4447.json"]
    assert json.loads((adir / "4447.json").read_text())["scalars"] == {
        "ptr_len_param_pair": 1
    }


def test_update_records_a_raise_as_a_delta_not_the_absolute_value(tmp_path):
    """Deltas compose: two rooms raising the same metric add up, which is the
    superposition a merge train gates.  An absolute value would not."""
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    adir = tmp_path / "ratchet_accept"
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(_baseline(scalars={"ptr_len_param_pair": 924})))
    assert (
        main(
            [
                "--measured",
                str(mpath),
                "--baseline",
                str(bpath),
                "--accept-dir",
                str(adir),
                "--ticket",
                "4447",
                "--update",
            ]
        )
        == 0
    )
    assert json.loads((adir / "4447.json").read_text())["scalars"] == {
        "ptr_len_param_pair": 8
    }


def test_update_with_no_raise_writes_no_acceptance(tmp_path):
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    adir = tmp_path / "ratchet_accept"
    mpath = tmp_path / "measured.json"
    mpath.write_text(json.dumps(_baseline(scalars={"ptr_len_param_pair": 900})))
    assert (
        main(
            [
                "--measured",
                str(mpath),
                "--baseline",
                str(bpath),
                "--accept-dir",
                str(adir),
                "--ticket",
                "4447",
                "--update",
            ]
        )
        == 0
    )
    assert not adir.exists() or not list(adir.glob("*.json"))


def test_re_running_update_rewrites_this_tickets_file_not_a_second_one(tmp_path):
    """A room that re-runs --update after a rebase replaces its own delta."""
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    adir = tmp_path / "ratchet_accept"
    for measured, expected in ((917, 1), (922, 6)):
        mpath = tmp_path / f"measured-{measured}.json"
        mpath.write_text(
            json.dumps(_baseline(scalars={"ptr_len_param_pair": measured}))
        )
        assert (
            main(
                [
                    "--measured",
                    str(mpath),
                    "--baseline",
                    str(bpath),
                    "--accept-dir",
                    str(adir),
                    "--ticket",
                    "4447",
                    "--update",
                ]
            )
            == 0
        )
        (doc,) = [json.loads(p.read_text()) for p in adir.glob("*.json")]
        assert doc["scalars"] == {"ptr_len_param_pair": expected}
    assert [p.name for p in adir.glob("*.json")] == ["4447.json"]


def test_acceptance_raises_the_allowance_and_still_refuses_one_more(tmp_path):
    adir = tmp_path / "ratchet_accept"
    _accept(adir / "4447.json", {"scalars": {"ptr_len_param_pair": 1}})
    allowance = effective_baseline(_baseline(), load_acceptances(adir))
    assert allowance["scalars"]["ptr_len_param_pair"] == 917
    assert compare(_baseline(scalars={"ptr_len_param_pair": 917}), allowance) == []
    regs = [
        f
        for f in compare(_baseline(scalars={"ptr_len_param_pair": 918}), allowance)
        if f.kind == "regression"
    ]
    assert regs and "918" in regs[0].detail


def test_acceptances_for_the_same_metric_compose_additively():
    """The merged tree costs both features, so allowances add; taking the max
    would let the second room's feature cost escape the train's gate."""
    allowance = effective_baseline(
        _baseline(),
        [
            {"scalars": {"ptr_len_param_pair": 1}},
            {"scalars": {"ptr_len_param_pair": 5}},
        ],
    )
    assert allowance["scalars"]["ptr_len_param_pair"] == 922
    # Neither room rebased: the train tree carries base + both feature costs.
    assert compare(_baseline(scalars={"ptr_len_param_pair": 922}), allowance) == []


def test_acceptances_compose_for_long_fns_and_new_cycle_members():
    allowance = effective_baseline(
        _baseline(),
        [
            {"long_fns": {"hand::big": 20}, "cycle_module_names": ["c"]},
            {"long_fns": {"hand::big": 5}, "cycle_module_names": ["d"]},
        ],
    )
    assert allowance["long_fns"]["hand::big"] == 425
    assert allowance["cycle_module_names"] == ["a", "b", "c", "d"]


def test_acceptance_is_excluded_when_it_is_recomputed(tmp_path):
    """--update must measure against everything *except* its own stale file,
    or a re-run would see its own delta and accept nothing."""
    doc = _baseline(scalars={"ptr_len_param_pair": 917})
    own_path = tmp_path / "4447.json"
    own = {"scalars": {"ptr_len_param_pair": 1}, "_path": own_path}
    allowance = effective_baseline(_baseline(), [own], exclude=own_path)
    assert acceptance_deltas(doc, allowance)["scalars"] == {"ptr_len_param_pair": 1}


def test_malformed_acceptance_fails_closed(tmp_path):
    adir = tmp_path / "ratchet_accept"
    adir.mkdir()
    (adir / "4447.json").write_text("{not json")
    with pytest.raises(ValueError):
        load_acceptances(adir)
    (adir / "4447.json").write_text(json.dumps({"scalars": {"cstr_literal": -1}}))
    with pytest.raises(ValueError):
        load_acceptances(adir)
    (adir / "4447.json").write_text(json.dumps({"scalars": [1]}))
    with pytest.raises(TypeError):
        load_acceptances(adir)


def test_raising_one_function_is_refused_until_this_ticket_accepts_it(tmp_path):
    """Mutation-check the ratchet end to end: a grown function fails, the same
    ticket may accept that exact cost, and one more SLOC is refused again."""
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline())
    adir = tmp_path / "ratchet_accept"
    common = ["--baseline", str(bpath), "--accept-dir", str(adir), "--ticket", "4447"]

    def measured(n: int) -> Path:
        path = tmp_path / f"measured-{n}.json"
        path.write_text(json.dumps(_baseline(long_fns={"hand::big": n})))
        return path

    assert main(["--measured", str(measured(401)), *common]) == 1
    assert main(["--measured", str(measured(401)), *common, "--update"]) == 0
    assert main(["--measured", str(measured(401)), *common]) == 0
    assert main(["--measured", str(measured(402)), *common]) == 1


def test_old_format_baseline_update_is_still_honoured_as_the_base(tmp_path):
    """An in-flight room on the old tool rewrites the blob (trap 3).  The new
    loader reads it as the base, so its accepted cost is not lost."""
    bpath = tmp_path / "baseline.json"
    _write_baseline(bpath, _baseline(scalars={"ptr_len_param_pair": 917}))
    allowance = effective_baseline(load_baseline(bpath), [])
    assert allowance["scalars"]["ptr_len_param_pair"] == 917


@pytest.mark.integration
def test_two_tickets_raising_the_same_metric_cherry_pick_in_either_order(tmp_path):
    """The acceptance itself: two rooms, different bases, same raised metric,
    one train, neither rebasing.  Each writes only its own ticket's file."""

    def git(*args: str) -> str:
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=t",
                "-c",
                "user.email=t@t",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    repo = tmp_path / "repo"
    accept = repo / "tools" / "ratchet_accept"
    accept.mkdir(parents=True)
    _write_baseline(repo / "tools" / "baseline.json", _baseline())
    git("init", "-q", "-b", "base")
    git("add", "-A")
    git("commit", "-qm", "base")
    fixes = []
    for ticket, delta in (("4447", 18), ("4324", 68)):
        git("checkout", "-q", "-b", f"task-{ticket}", "base")
        _accept(accept / f"{ticket}.json", {"scalars": {"cstr_literal": delta}})
        git("add", "-A")
        git("commit", "-qm", f"task-{ticket}")
        fixes.append(git("rev-parse", "HEAD"))
    for order in (fixes, fixes[::-1]):
        git("checkout", "-q", "-B", "train", "base")
        for sha in order:
            git("cherry-pick", sha)  # check=True: a conflict raises, failing us
        allowance = effective_baseline(
            load_baseline(repo / "tools" / "baseline.json"),
            load_acceptances(accept),
        )
        # 6763 + 18 + 68: both feature costs, no rebase, no re-gate.
        assert allowance["scalars"]["cstr_literal"] == 6763 + 18 + 68


# --------------------------------------------------------------------------
# The committed baseline describes this tree, and this tree does not
# regress it.  This is the gate `make tools-unit` runs.
# --------------------------------------------------------------------------


@_TREE_GROUP
def test_committed_baseline_matches_this_tree(tree_measured):
    assert DEFAULT_BASELINE.exists(), DEFAULT_BASELINE
    allowance = effective_baseline(
        load_baseline(DEFAULT_BASELINE), load_acceptances(DEFAULT_ACCEPT)
    )
    measured = tree_measured
    findings = compare(measured, allowance)
    regressions = [f for f in findings if f.kind == "regression"]
    assert regressions == [], "\n".join(f.detail for f in regressions)
