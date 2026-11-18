"""Tests for the matrix gate's exit code (AGAST #1372).

`make matrix-full` is the compiler gate this repo cites in almost every commit
message: "matrix-full 53/53 x 3". It could not fail. run_regression_matrix.py's
main() ended in an unconditional `return 0`, so the process exited 0 no matter
how many cells were red. The Makefile target just runs the script, and CI's
"Bootstrap chain + regression matrix" step just runs the target, so nothing
between the failure and the green check mark ever looked at a status.

It was found by making it fail: #1369 turned ritz1's silent
`; ERROR ... add i64 0, 0` substitution into a hard compile error, which took
test_issue_float_coercion from pass to compile-fail under ritz1 and
ritz1_selfhosted. The summary printed

    ritz0                53/53
    ritz1                52/53
    ritz1_selfhosted     52/53

and the command exited 0.

The classification is tools/known_failures.py's outcome(), the one copy of
the rule every gate uses (AGAST #1834); these tests pin the matrix's wiring
of it (CPU skips, file vs file::fn keys, per-compiler lists, the exit code):

  hard  — failed and NOT excused. Fails the gate.
  known — failed and listed in known-failures/<agast>.toml. Advisory, printed
          with its AGAST reference so it stays visible.
  xpass — listed but PASSED. Also fails the gate.

The xpass half is the part that keeps the list from rotting. scripts/regression.sh
carried the same check for years as a warn() that changed nothing, and two
entries sat on its allowlist blaming the async framework for what was really a
syntax migration (#1365). A list that cannot go red is a list nobody edits.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

MATRIX = Path(__file__).resolve().parent / "run_regression_matrix.py"


def _load():
    spec = importlib.util.spec_from_file_location("_matrix", MATRIX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


matrix = _load()
kf = sys.modules["known_failures"]


def _results(**kw):
    """Build a results dict: name -> (status, code, info)."""
    return {name: (status, 0 if status == "pass" else 1, "") for name, status in kw.items()}


def _classify(results, known):
    o = matrix.classify(results, known)
    return o.hard, sorted(o.known), o.xpass


def _entry(compiler, unit, agast=1370):
    return kf.Entry("matrix", compiler, unit, "why", agast, Path(f"{agast}.toml"))


@pytest.mark.unit
def test_all_passing_is_green():
    assert _classify(_results(a="pass", b="pass"), []) == ([], [], [])


@pytest.mark.unit
def test_an_unexpected_failure_is_hard():
    """The case that was silently exiting 0."""
    assert _classify(_results(a="pass", b="compile-fail"), []) == (["b"], [], [])


@pytest.mark.unit
def test_an_expected_failure_is_advisory_not_hard():
    assert _classify(_results(a="pass", b="compile-fail"), ["b"]) == ([], ["b"], [])


@pytest.mark.unit
def test_expected_failure_is_per_compiler():
    """An entry for ritz1 must not excuse ritz1_selfhosted.

    ritz1 and its self-compiled twin disagreeing is a self-hosting bug, and
    must go red rather than be recorded. Keying the excuse by (compiler, unit)
    keeps that true here: excusing one does not excuse the other.
    """
    outcomes = matrix.classify_all(
        {"ritz1": _results(b="compile-fail"), "ritz1_selfhosted": _results(b="compile-fail")},
        [_entry("ritz1", "b")])
    assert outcomes["ritz1"].hard == []
    assert outcomes["ritz1_selfhosted"].hard == ["b"], "a ritz1 excuse leaked into ritz1_selfhosted"


@pytest.mark.unit
def test_an_expected_failure_that_passes_is_xpass():
    """Strict-xpass: the entry must be deleted, and until it is, the gate is red."""
    assert _classify(_results(b="pass"), ["b"]) == ([], [], ["b"])


@pytest.mark.unit
def test_xpass_for_a_test_that_did_not_run_is_not_reported():
    """Filtering with --tests must not turn every unselected entry into an xpass."""
    assert _classify(_results(a="pass"), ["not_selected"]) == ([], [], [])


@pytest.mark.unit
def test_exit_code_is_nonzero_for_hard_and_xpass_only():
    O = kf.Outcome
    assert matrix.matrix_exit_code({"ritz1": O([], {}, [])}) == 0
    assert matrix.matrix_exit_code({"ritz1": O(["b"], {}, [])}) != 0
    assert matrix.matrix_exit_code({"ritz1": O([], {"b": "b"}, [])}) == 0, (
        "a known failure is advisory and must not fail the gate"
    )
    assert matrix.matrix_exit_code({"ritz1": O([], {}, ["b"])}) != 0, (
        "an expected failure that starts passing must fail the gate"
    )
    assert matrix.matrix_exit_code(
        {"ritz0": O([], {}, []), "ritz1": O(["b"], {}, [])}
    ) != 0, "a failure in any compiler must fail the gate"


@pytest.mark.unit
def test_a_synthetic_xpass_in_the_checked_in_format_fails_the_gate(tmp_path, monkeypatch):
    """End to end through the real loader: an entry in a known-failures dir
    (RITZ_KNOWN_FAILURES) for a cell that passes makes the matrix exit 1, and
    the same cell failing is advisory (exit 0)."""
    (tmp_path / "9999.toml").write_text(
        '[[entry]]\ngate = "matrix"\ncompiler = "ritz1"\nunit = "f"\n'
        'reason = "synthetic"\nagast = 9999\n')
    monkeypatch.setenv("RITZ_KNOWN_FAILURES", str(tmp_path))
    passing = matrix.classify_all({"ritz1": _results(**{"f::a": "pass"})})
    assert passing["ritz1"].xpass == ["f"]
    assert matrix.matrix_exit_code(passing) == 1
    failing = matrix.classify_all({"ritz1": _results(**{"f::a": "link-fail"})})
    assert failing["ritz1"].known == {"f::a": "f"}
    assert matrix.matrix_exit_code(failing) == 0


@pytest.mark.unit
def test_every_fn_level_matrix_entry_names_a_real_unit():
    """known_failures checks an entry's file exists; a `file::fn` key must also
    be a unit the matrix runs, or it excuses nothing while looking diligent."""
    for e in kf.load():
        if e.gate != "matrix" or "::" not in e.unit:
            continue
        file_name = e.unit.partition("::")[0]
        src = (matrix.TEST_DIR / f"{file_name}.ritz").read_text()
        units = matrix.units_for(file_name, src)
        assert e.unit in units, f"{e.unit!r} is excused but is not a unit of {file_name}: {units}"


# ---------------------------------------------------------------------------
# AGAST #1371 — the matrix used to call only fns[0], the FIRST [[test]] fn in
# each file, out of a hardcoded list of 53 files: 53 of 560 test fns executed.
# Everything below pins the replacement: every fn runs, files are discovered,
# and a floor fails the gate if what ran is less than what is on disk.
# ---------------------------------------------------------------------------

THREE_FNS = """\
import ritzlib.sys

[[test]]
fn test_a() -> i32
    0

fn helper() -> i32
    1

[[test]]
fn test_b() -> i64
    0

[[test]]

fn test_c()
    assert 1 == 1

fn main() -> i32
    test_a()
"""


# THREE_FNS with its main gone: the shape every corpus file must have, since
# a main beside [[test]] fns is stripped unseen (AGAST #4043).
THREE_FNS_NO_MAIN = THREE_FNS[:THREE_FNS.index("fn main(")]


@pytest.mark.unit
def test_find_test_fns_returns_every_fn_with_its_return_type():
    assert matrix.find_test_fns(THREE_FNS) == [
        ("test_a", "i32"), ("test_b", "i64"), ("test_c", None)
    ]


@pytest.mark.unit
def test_count_test_markers_is_independent_of_the_fn_parser():
    """The floor compares two counts; they must come from different code."""
    assert matrix.count_test_markers(THREE_FNS) == 3
    # A marker the fn parser cannot attach to a fn still counts, so the floor
    # sees the mismatch instead of the fn silently dropping out.
    broken = "[[test]]\npub fn test_x() -> i32\n    0\n"
    assert matrix.count_test_markers(broken) == 1
    assert matrix.find_test_fns(broken) == []


@pytest.mark.unit
def test_units_are_one_per_test_fn_not_one_per_file():
    assert matrix.units_for("t", THREE_FNS) == ["t::test_a", "t::test_b", "t::test_c"]


@pytest.mark.unit
def test_a_main_driven_file_with_no_test_fns_is_one_main_unit():
    src = "fn main() -> i32\n    0\n"
    assert matrix.units_for("t", src) == ["t::main"]


@pytest.mark.unit
def test_a_file_with_neither_tests_nor_main_has_no_units():
    assert matrix.units_for("t", "fn f() -> i32\n    0\n") == []


@pytest.mark.unit
def test_harness_dispatches_to_every_test_fn_not_just_the_first():
    """The #1371 bug was `fn main() -> i32 { fns[0]() }`."""
    h = matrix.build_harness(THREE_FNS, matrix.find_test_fns(THREE_FNS))
    for i, name in enumerate(["test_a", "test_b", "test_c"]):
        assert f"== {matrix.SELECTOR_BASE + i}" in h
        assert f"{name}()" in h.split("fn main(", 1)[1], f"{name} is never called"
    # The file's own main is replaced, not kept alongside ours.
    assert h.count("fn main(") == 1
    # An i32 that is a nonzero multiple of 256 must not exit 0.
    assert "ritz_matrix_rc(test_a())" in h
    assert "ritz_matrix_rc64(test_b())" in h


@pytest.mark.unit
def test_selector_round_trips_for_every_index():
    for i in range(matrix.MAX_FNS_PER_FILE):
        sel = matrix.selector_arg(i)
        assert len(sel) == 1 and ord(sel) == matrix.SELECTOR_BASE + i
    with pytest.raises(ValueError):
        matrix.selector_arg(matrix.MAX_FNS_PER_FILE)


@pytest.mark.unit
def test_discovery_covers_every_ritz_file_on_disk(tmp_path):
    for n in ["test_b", "test_a", "lib_only"]:
        (tmp_path / f"{n}.ritz").write_text("")
    (tmp_path / "notes.txt").write_text("")
    assert matrix.discover_test_files(tmp_path, not_tests={}) == ["lib_only", "test_a", "test_b"]
    assert matrix.discover_test_files(tmp_path, not_tests={"lib_only": "x"}) == ["test_a", "test_b"]


@pytest.mark.unit
def test_discovery_is_not_a_hardcoded_list():
    on_disk = sorted(p.stem for p in matrix.TEST_DIR.glob("*.ritz"))
    assert matrix.discover_test_files() == [n for n in on_disk if n not in matrix.NOT_TESTS]
    assert not hasattr(matrix, "TESTS"), "a hardcoded list is how 66 files went unrun"


@pytest.mark.unit
def test_not_tests_entries_really_have_nothing_to_run():
    """NOT_TESTS may only hold files with no [[test]] fn and no main; a file
    that grows either must leave the list so it starts running."""
    for name, reason in matrix.NOT_TESTS.items():
        path = matrix.TEST_DIR / f"{name}.ritz"
        assert path.is_file(), f"NOT_TESTS names missing file {name}"
        assert reason.strip(), f"NOT_TESTS[{name!r}] needs a reason"
        assert matrix.units_for(name, path.read_text()) == [], (
            f"{name} has runnable units; remove it from NOT_TESTS"
        )


@pytest.mark.unit
def test_fn_level_failure_is_hard_even_when_a_sibling_is_excused():
    results = _results(**{"f::a": "pass", "f::b": "bad-exit", "f::c": "bad-exit"})
    assert _classify(results, ["f::b"]) == (["f::c"], ["f::b"], [])


@pytest.mark.unit
def test_file_level_entry_excuses_build_failures_of_every_unit():
    results = _results(**{"f::a": "compile-fail", "f::b": "compile-fail"})
    o = matrix.classify(results, ["f"])
    assert o.hard == [] and o.known == {"f::a": "f", "f::b": "f"} and o.xpass == []


@pytest.mark.unit
def test_file_level_entry_does_not_excuse_runtime_failures():
    """Otherwise one file-level line becomes a bulk allowlist for every fn."""
    results = _results(**{"f::a": "pass", "f::b": "bad-exit"})
    hard, _known, xpass = _classify(results, ["f"])
    assert hard == ["f::b"]
    assert xpass == ["f"], "the file now builds, so its file-level entry is stale"


@pytest.mark.unit
def test_fn_level_entry_xpasses_when_that_fn_passes():
    results = _results(**{"f::a": "pass", "f::b": "pass"})
    _, _, xpass = _classify(results, ["f::b"])
    assert xpass == ["f::b"]


@pytest.mark.unit
def test_known_names_the_matching_entry():
    """The summary's ⚠ line cites the key that excused each unit: an exact
    fn key over the file key, and a file key only for build failures."""
    o = matrix.classify(_results(**{"f::a": "compile-fail", "g::b": "bad-exit",
                                    "g::c": "compile-fail"}), ["f", "g", "g::b"])
    assert o.known == {"f::a": "f", "g::b": "g::b", "g::c": "g"}
    assert _classify(_results(**{"f::a": "bad-exit"}), ["f"])[0] == ["f::a"]


@pytest.mark.unit
def test_floor_passes_when_every_marker_ran():
    srcs = {"t": THREE_FNS_NO_MAIN}
    results = {"ritz1": _results(**{"t::test_a": "pass", "t::test_b": "pass", "t::test_c": "pass"})}
    assert matrix.floor_violations(srcs, results) == []


@pytest.mark.unit
def test_floor_fails_when_a_unit_did_not_run():
    srcs = {"t": THREE_FNS_NO_MAIN}
    results = {"ritz1": _results(**{"t::test_a": "pass", "t::test_b": "pass"})}
    v = matrix.floor_violations(srcs, results)
    assert v and "t::test_c" in " ".join(v)


@pytest.mark.unit
def test_floor_fails_when_a_marker_has_no_parsed_fn():
    srcs = {"t": "[[test]]\npub fn test_x() -> i32\n    0\n"}
    v = matrix.floor_violations(srcs, {"ritz1": {}})
    assert v and "t" in v[0] and "1" in v[0]


@pytest.mark.unit
def test_floor_fails_when_a_file_has_test_fns_and_a_main():
    """AGAST #4043: build_harness strips main, and so does `ritz0 --test`, so
    a main beside [[test]] fns is compiled by no gate. test_level21/22/23 hid
    a whole-file compile error there until #3610. Every unit ran here; the
    main alone must fail the floor."""
    results = {"ritz1": _results(**{"t::test_a": "pass", "t::test_b": "pass", "t::test_c": "pass"})}
    v = matrix.floor_violations({"t": THREE_FNS}, results)
    assert len(v) == 1 and v[0].startswith("t:") and "main" in v[0], v


@pytest.mark.unit
def test_floor_accepts_a_main_driven_file():
    """A file with no [[test]] fn runs its main whole: that main is compiled."""
    src = "fn main() -> i32\n    0\n"
    assert matrix.floor_violations({"t": src}, {"ritz1": _results(**{"t::main": "pass"})}) == []


@pytest.mark.unit
def test_floor_on_the_real_corpus_parses_every_marker():
    """Every [[test]] line on disk must become a unit, today."""
    srcs = {n: (matrix.TEST_DIR / f"{n}.ritz").read_text() for n in matrix.discover_test_files()}
    expected_units = {u for n, s in srcs.items() for u in matrix.units_for(n, s)}
    results = {"ritz1": _results(**{u: "pass" for u in expected_units})}
    assert matrix.floor_violations(srcs, results) == []
    markers = sum(matrix.count_test_markers(s) for s in srcs.values())
    assert markers >= 560, f"only {markers} [[test]] markers found; corpus shrank?"


@pytest.mark.unit
def test_files_with_nothing_to_run_are_hard_failures():
    """A discovered file with no units (and not in NOT_TESTS) is reported, not skipped."""
    v = matrix.floor_violations({"t": "fn f() -> i32\n    0\n"}, {"ritz1": {}})
    assert v and "t" in v[0]


@pytest.mark.unit
def test_a_cpu_skip_is_neither_pass_nor_failure_nor_xpass():
    """A host without SHA-NI cannot run test_shani; that must not read as green
    (pass), red (hard), or make a file-level entry look stale (xpass)."""
    results = _results(**{"f::a": "skip-cpu", "f::b": "skip-cpu"})
    assert _classify(results, ["f"]) == ([], [], [])
    assert _classify(results, []) == ([], [], [])


@pytest.mark.unit
def test_cpu_skip_reason_only_when_a_required_flag_is_missing():
    req = {"test_shani": ["sha_ni"]}
    assert matrix.cpu_skip_reason("test_shani", {"aes"}, req) is not None
    assert matrix.cpu_skip_reason("test_shani", {"sha_ni"}, req) is None
    assert matrix.cpu_skip_reason("test_other", set(), req) is None


@pytest.mark.unit
def test_requires_cpu_names_real_files():
    discovered = set(matrix.discover_test_files())
    for name, flags in matrix.REQUIRES_CPU.items():
        assert name in discovered, f"REQUIRES_CPU names unknown file {name}"
        assert flags, f"REQUIRES_CPU[{name!r}] is empty"


class _ReachedBuild(Exception):
    pass


class _FlagsOnlyDeps:
    """A Deps whose host CPU flags are forced; reaching the build raises."""

    def __init__(self, flags):
        self.cpu_flags = set(flags)

    def closure(self, src_path):
        raise _ReachedBuild(src_path)


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(matrix.REQUIRES_CPU))
def test_run_file_skips_every_unit_when_a_flag_is_absent(tmp_path, name):
    """AGAST #1921: run_file is what the CI ritz0/ritz1 cells call. With the
    feature forced absent, nothing is compiled or run and every unit says so."""
    out = matrix.run_file(name, "ritz0", "/nonexistent", _FlagsOnlyDeps(set()),
                          {}, tmp_path)
    assert out and {s for s, _, _ in out.values()} == {"skip-cpu"}, out
    assert all("host CPU lacks" in info for _, _, info in out.values())


@pytest.mark.unit
@pytest.mark.parametrize("name", sorted(matrix.REQUIRES_CPU))
def test_run_file_builds_when_every_flag_is_present(tmp_path, name):
    """The skip must not swallow a capable host: a SIGILL there is a failure."""
    deps = _FlagsOnlyDeps(matrix.REQUIRES_CPU[name])
    with pytest.raises(_ReachedBuild):
        matrix.run_file(name, "ritz0", "/nonexistent", deps, {}, tmp_path)


@pytest.mark.unit
def test_harness_lowers_and_runs_under_ritz0(tmp_path):
    """End to end on ritz0: every fn is selected, a failing fn's code is its own,
    and an i32 of 256 does not exit 0."""
    import os
    import subprocess
    src = (
        "[[test]]\nfn test_ok() -> i32\n    0\n\n"
        "[[test]]\nfn test_seven() -> i32\n    7\n\n"
        "[[test]]\nfn test_256() -> i32\n    256\n\n"
        "[[test]]\nfn test_wide() -> i64\n    4294967296\n\n"
        "[[test]]\nfn test_void()\n    let x: i32 = 1\n"
    )
    if not matrix.RUNTIME_O.is_file():
        # Gitignored build product; CI runs tools-unit before the bootstrap.
        subprocess.run(["make", "-C", str(matrix.RUNTIME_O.parent), matrix.RUNTIME_O.name],
                       check=True, capture_output=True)
    h = tmp_path / "h.ritz"
    h.write_text(matrix.build_harness(src, matrix.find_test_fns(src)))
    env = dict(os.environ, RITZ_PATH=str(matrix.RITZ_ROOT))
    ll, o, exe = tmp_path / "h.ll", tmp_path / "h.o", tmp_path / "h"
    r = matrix.compile_with_ritz0(h, ll, env)
    assert r.returncode == 0, r.stderr
    subprocess.run(["clang", "-c", "-O2", str(ll), "-o", str(o)], check=True, capture_output=True)
    subprocess.run(["ld", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2", "-lc", "-o", str(exe),
                    str(matrix.RUNTIME_O), str(o)], check=True, capture_output=True)
    codes = [matrix.run_exe([str(exe), matrix.selector_arg(i)]) for i in range(5)]
    assert [c[0] for c in codes] == ["pass", "bad-exit", "bad-exit", "bad-exit", "pass"], codes
    assert codes[1][1] == 7
    assert codes[2][1] == 255 and codes[3][1] == 255


def test_cell_link_cmd_links_no_libc_ahead_of_ritzlib(tmp_path):
    """AGAST #1983: a `-lc` before the ritzlib archive made glibc's malloc,
    realloc and free win, so no cell ever ran ritzlib.memory."""
    cmd = matrix.cell_link_cmd(tmp_path / "e", tmp_path / "t.o", ["dep.o"], tmp_path / "b.a")
    assert not [a for a in cmd if a.startswith("-l")], cmd
    assert cmd[-1] == str(tmp_path / "b.a")
    assert cmd.index(str(tmp_path / "t.o")) < cmd.index("dep.o") < cmd.index(str(tmp_path / "b.a"))
