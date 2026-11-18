"""Tests for tools/known_failures.py: the one known-failures schema (AGAST #1834).

Every gate that may excuse a failure reads its excuses from
known-failures/<agast>.toml through one parser (load) and decides through one
function (outcome).  Before #1834 there were six lists in four formats and the
hard / known / xpass rule was written three times; the "every entry cites an
AGAST id" rule was enforced in three separate tests.  It is enforced once now,
by the parser, and pinned here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import known_failures as kf  # noqa: E402

WORKSPACE = TOOLS.parents[2]
CLI = TOOLS / "known_failures.py"


def write(d: Path, name: str, text: str) -> Path:
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(text)
    return p


def entry(gate="build", compiler="any", unit="lexis", reason="why", agast=7) -> str:
    return (f'[[entry]]\ngate = "{gate}"\ncompiler = "{compiler}"\n'
            f'unit = "{unit}"\nreason = "{reason}"\nagast = {agast}\n')


# ---------------------------------------------------------------------------
# The schema: one parser, and the AGAST-id rule lives in it.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_reads_every_ticket_file(tmp_path):
    write(tmp_path, "7.toml", entry() + entry(gate="matrix", compiler="ritz1", unit="t::f"))
    write(tmp_path, "9.toml", entry(gate="doc", compiler="ritz1",
                                    unit="LANGUAGE_SPEC.md 0123456789ab", agast=9))
    got = kf.load(tmp_path)
    assert [(e.gate, e.compiler, e.unit, e.agast) for e in got] == [
        ("build", "any", "lexis", 7),
        ("matrix", "ritz1", "t::f", 7),
        ("doc", "ritz1", "LANGUAGE_SPEC.md 0123456789ab", 9),
    ]
    assert got[0].cite == "AGAST #7: why"
    assert got[0].path == tmp_path / "7.toml"


@pytest.mark.unit
def test_an_empty_or_missing_directory_has_no_entries(tmp_path):
    assert kf.load(tmp_path / "nope") == []
    assert kf.load(tmp_path) == []


@pytest.mark.unit
@pytest.mark.parametrize("name, text, needle", [
    # The AGAST-id rule, formerly in test_rz_cli.py, test_run_regression_
    # matrix_gate.py and test-regression-xpass.sh: no entry without a ticket.
    ("7.toml", entry().replace("agast = 7\n", ""), "agast"),
    ("7.toml", entry().replace("agast = 7", 'agast = "#7"'), "agast"),
    ("7.toml", entry().replace("agast = 7", "agast = 0"), "agast"),
    ("lexis.toml", entry(), "name the file for its AGAST ticket"),
    ("8.toml", entry(), "agast = 7 but the file is 8.toml"),
    # The other fields.
    ("7.toml", entry(reason=""), "reason"),
    ("7.toml", entry(unit=""), "unit"),
    ("7.toml", entry() + 'extra = 1\n', "extra"),
    ("7.toml", 'entry = 1\n', "[[entry]]"),
    ("7.toml", "[[entry]\n", "7.toml"),  # not TOML at all
    ("7.toml", entry(gate="nightly"), "nightly"),
    ("7.toml", entry(gate="matrix", compiler="ritz9"), "ritz9"),
    ("7.toml", entry(gate="build", compiler="ritz1"), "ritz1"),
    ("7.toml", entry(gate="doc", compiler="ritz1", unit="LANGUAGE_SPEC.md 12"), "12-hex"),
    ("7.toml", entry(gate="matrix", compiler="ritz1", unit="a::b::c"), "a::b::c"),
    ("7.toml", entry() + entry(), "listed twice"),
])
def test_load_refuses_a_malformed_entry_naming_its_file(tmp_path, name, text, needle):
    write(tmp_path, name, text)
    with pytest.raises(kf.KnownFailuresError) as e:
        kf.load(tmp_path)
    assert needle in str(e.value)
    assert name in str(e.value)


@pytest.mark.unit
def test_a_key_listed_in_two_files_is_refused(tmp_path):
    write(tmp_path, "7.toml", entry())
    write(tmp_path, "8.toml", entry(agast=8))
    with pytest.raises(kf.KnownFailuresError, match="listed twice"):
        kf.load(tmp_path)


@pytest.mark.unit
@pytest.mark.parametrize("gate", ["stage5", "test"])
def test_the_gates_that_must_never_be_excused_have_no_gate_name(tmp_path, gate):
    """Stage 5 compares accept sets with no allowlist (regression.sh), and the
    `rz test --all` sweep has no test-side excuse (a behavioural failure is
    never excusable; the build list feeds it).  Neither exists as a gate, so
    no entry can be written for one, and the refusal says why."""
    write(tmp_path, "7.toml", entry(gate=gate))
    with pytest.raises(kf.KnownFailuresError, match="never excused"):
        kf.load(tmp_path)


@pytest.mark.unit
def test_every_checked_in_entry_parses():
    """The real data, through the same parser every gate uses.  This is the
    single home of the "every entry cites an AGAST id" check (#1834)."""
    entries = kf.load()
    assert kf.DEFAULT_DIR == WORKSPACE / "known-failures"
    for e in entries:
        assert e.path.name == f"{e.agast}.toml"


@pytest.mark.unit
def test_every_checked_in_entry_names_something_that_exists():
    """An entry for a unit that is gone is dead weight that reads as debt."""
    ritz = WORKSPACE / "projects" / "ritz"
    for e in kf.load():
        if e.gate == "build":
            assert (WORKSPACE / "projects" / e.unit / "ritz.toml").is_file(), e
        elif e.gate == "matrix":
            assert (ritz / "ritz0" / "test" / f"{e.unit.partition('::')[0]}.ritz").is_file(), e
        elif e.gate == "examples":
            assert (ritz / "examples" / e.unit).is_file(), e
        elif e.gate == "doc":
            assert (ritz / "docs" / e.unit.split()[0]).is_file(), e
        elif e.gate == "regression":
            keys = {str(p.relative_to(ritz / "examples")).replace("/", "_")
                    for p in (ritz / "examples").glob("**/") if "build" not in p.parts}
            assert e.unit in keys, e


@pytest.mark.unit
def test_known_is_per_gate_and_per_compiler(tmp_path):
    write(tmp_path, "7.toml",
          entry(gate="matrix", compiler="ritz1", unit="t")
          + entry(gate="matrix", compiler="ritz0", unit="u", reason="other")
          + entry(gate="doc", compiler="ritz1", unit="A.md 0123456789ab"))
    es = kf.load(tmp_path)
    assert kf.known("matrix", "ritz1", es) == {"t": "AGAST #7: why"}
    assert kf.known("matrix", "ritz1_selfhosted", es) == {}
    assert kf.known("matrix", "ritz0", es) == {"u": "AGAST #7: other"}
    assert kf.known("build", "any", es) == {}


@pytest.mark.unit
def test_build_entries_apply_whatever_compiler_rz_runs(tmp_path):
    write(tmp_path, "7.toml", entry())
    es = kf.load(tmp_path)
    assert kf.known("build", "any", es) == {"lexis": "AGAST #7: why"}
    assert kf.known("build", "ritz1", es) == {"lexis": "AGAST #7: why"}


@pytest.mark.unit
def test_regression_ritz1_entries_cover_ritz1_selfhosted_and_cannot_be_split(tmp_path):
    """regression.sh's ritz1 list is shared with ritz1_selfhosted; that is
    safe only because Stage 5 compares the two accept sets with no list at
    all.  So a ritz1_selfhosted-only regression entry cannot be written."""
    write(tmp_path, "7.toml", entry(gate="regression", compiler="ritz1", unit="tier1_x"))
    es = kf.load(tmp_path)
    assert kf.known("regression", "ritz1_selfhosted", es) == {"tier1_x": "AGAST #7: why"}
    assert kf.known("regression", "ritz0", es) == {}
    write(tmp_path, "8.toml", entry(gate="regression", compiler="ritz1_selfhosted",
                                    unit="tier1_y", agast=8))
    with pytest.raises(kf.KnownFailuresError, match="ritz1_selfhosted"):
        kf.load(tmp_path)


# ---------------------------------------------------------------------------
# The outcome: one function.  Formerly rz gate_outcome, the matrix's
# matrix_outcome and regression.sh's two inline blocks.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_outcome_all_pass_is_green():
    o = kf.outcome({}, {"a": "pass", "b": "pass"})
    assert (o.hard, o.known, o.xpass, o.ok) == ([], {}, [], True)


@pytest.mark.unit
def test_outcome_unlisted_failure_is_hard():
    o = kf.outcome({}, {"a": "pass", "b": "fail"})
    assert (o.hard, o.known, o.xpass, o.ok) == (["b"], {}, [], False)


@pytest.mark.unit
def test_outcome_listed_failure_is_known_and_advisory():
    o = kf.outcome({"b": "AGAST #1: x"}, {"a": "pass", "b": "fail"})
    assert (o.hard, o.known, o.xpass, o.ok) == ([], {"b": "b"}, [], True)


@pytest.mark.unit
def test_outcome_listed_unit_that_passes_is_xpass_and_fails():
    """Strict xpass: an excuse cannot outlive its failure."""
    o = kf.outcome({"b": "AGAST #1: x"}, {"a": "pass", "b": "pass"})
    assert (o.hard, o.known, o.xpass, o.ok) == ([], {}, ["b"], False)


@pytest.mark.unit
def test_outcome_listed_unit_that_did_not_run_is_not_xpass():
    """A filtered sweep (`--tests`, `rz build a`) must not turn every
    unselected entry into an xpass."""
    o = kf.outcome({"zzz": "AGAST #1: x"}, {"a": "pass"})
    assert o.ok and o.xpass == []


@pytest.mark.unit
def test_outcome_orders_follow_the_inputs():
    """rz prints PKG lines in this order, so the order is the verdict's."""
    o = kf.outcome({"c": "", "a": "", "z": ""},
                   {"d": "fail", "c": "fail", "b": "fail", "a": "pass"})
    assert o.hard == ["d", "b"]
    assert list(o.known) == ["c"]
    assert o.xpass == ["a"]


def _matrix(known, results):
    return kf.outcome(known, results, scope=kf.matrix_scope, covers=kf.matrix_covers)


@pytest.mark.unit
def test_outcome_file_key_excuses_only_build_failures_of_its_fns():
    r = {"f::a": "compile-fail", "f::b": "compile-fail", "g::a": "compile-fail"}
    o = _matrix({"f": ""}, r)
    assert o.hard == ["g::a"] and o.known == {"f::a": "f", "f::b": "f"} and o.xpass == []
    o = _matrix({"f": ""}, {"f::a": "run-fail"})
    assert o.hard == ["f::a"] and o.xpass == ["f"]


@pytest.mark.unit
def test_outcome_fn_key_excuses_any_failure_of_that_fn_and_goes_stale_alone():
    o = _matrix({"f::b": ""}, {"f::a": "pass", "f::b": "run-fail"})
    assert o.ok and o.known == {"f::b": "f::b"}
    o = _matrix({"f::b": ""}, {"f::a": "run-fail", "f::b": "pass"})
    assert o.hard == ["f::a"] and o.xpass == ["f::b"]


@pytest.mark.unit
def test_outcome_fn_key_wins_over_file_key():
    o = _matrix({"f": "", "f::a": ""}, {"f::a": "compile-fail", "f::b": "compile-fail"})
    assert o.known == {"f::a": "f::a", "f::b": "f"} and o.ok


@pytest.mark.unit
def test_outcome_file_key_with_all_fns_built_is_xpass():
    o = _matrix({"f": ""}, {"f::a": "pass", "f::b": "pass"})
    assert o.xpass == ["f"]


# ---------------------------------------------------------------------------
# The CLI: what regression.sh (and anything else in shell) calls.
# ---------------------------------------------------------------------------


def cli(*args, kf_dir: Path | None = None):
    env = dict(os.environ)
    if kf_dir is not None:
        env["RITZ_KNOWN_FAILURES"] = str(kf_dir)
    return subprocess.run([sys.executable, str(CLI), *args], env=env,
                          capture_output=True, text=True, check=False)


@pytest.fixture
def regression_dir(tmp_path):
    write(tmp_path, "7.toml", entry(gate="regression", compiler="ritz1", unit="tier1_x"))
    return tmp_path


@pytest.mark.integration
@pytest.mark.parametrize("compiler, unit, status, want", [
    ("ritz1", "tier1_y", "pass", "pass"),
    ("ritz1", "tier1_y", "fail", "hard"),
    ("ritz1", "tier1_x", "fail", "known"),
    ("ritz1_selfhosted", "tier1_x", "fail", "known"),
    ("ritz0", "tier1_x", "fail", "hard"),
    ("ritz1", "tier1_x", "pass", "xpass"),  # a synthetic xpass
])
def test_cli_verdict(regression_dir, compiler, unit, status, want):
    r = cli("verdict", "--gate", "regression", "--compiler", compiler, unit, status,
            kf_dir=regression_dir)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split("\t")[0].strip() == want


@pytest.mark.integration
def test_cli_verdict_names_ticket_and_file(regression_dir):
    known = cli("verdict", "--gate", "regression", "--compiler", "ritz1",
                "tier1_x", "fail", kf_dir=regression_dir).stdout
    assert "AGAST #7: why" in known
    xpass = cli("verdict", "--gate", "regression", "--compiler", "ritz1",
                "tier1_x", "pass", kf_dir=regression_dir).stdout
    assert "AGAST #7: why" in xpass and "7.toml" in xpass


@pytest.mark.integration
def test_cli_list_and_check(regression_dir):
    r = cli("list", "--gate", "regression", "--compiler", "ritz1_selfhosted",
            kf_dir=regression_dir)
    assert r.stdout == "tier1_x\tAGAST #7: why\n"
    assert cli("check", kf_dir=regression_dir).returncode == 0


@pytest.mark.integration
def test_cli_fails_closed_on_a_malformed_list(tmp_path):
    """Exit 2 and no verdict: a caller that reads stdout sees no "known"."""
    write(tmp_path, "7.toml", entry(agast=8))
    for args in (["verdict", "--gate", "build", "--compiler", "any", "lexis", "fail"],
                 ["list", "--gate", "build", "--compiler", "any"], ["check"]):
        r = cli(*args, kf_dir=tmp_path)
        assert r.returncode == 2 and r.stdout == "", args
        assert "7.toml" in r.stderr


@pytest.mark.integration
def test_cli_refuses_an_unknown_gate_or_compiler(regression_dir):
    assert cli("list", "--gate", "nope", "--compiler", "ritz1",
               kf_dir=regression_dir).returncode == 2
    assert cli("list", "--gate", "regression", "--compiler", "ritz7",
               kf_dir=regression_dir).returncode == 2


# ---------------------------------------------------------------------------
# One file per ticket (AGAST #3963, carried over from doc_known_failures/).
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_deleting_two_tickets_files_cherry_picks_in_either_order(tmp_path):
    """Two fixes, each deleting its own ticket's file, land in either order
    without a conflict: why the list is a directory and not one file."""

    def git(*args: str) -> str:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                               "-c", "commit.gpgsign=false", *args], cwd=tmp_path / "repo",
                              capture_output=True, text=True, check=True).stdout.strip()

    d = tmp_path / "repo" / "kf"
    write(d.parent, ".keep", "")
    write(d, "7.toml", entry(unit="a"))
    write(d, "8.toml", entry(unit="b", agast=8))
    write(d, "9.toml", entry(unit="c", agast=9))
    git("init", "-q", "-b", "base")
    git("add", "-A")
    git("commit", "-qm", "base")
    fixes = []
    for n in ("7", "8"):
        git("checkout", "-q", "-b", f"fix-{n}", "base")
        git("rm", "-q", f"kf/{n}.toml")
        git("commit", "-qm", f"fix {n}")
        fixes.append(git("rev-parse", "HEAD"))
    for order in (fixes, fixes[::-1]):
        git("checkout", "-q", "-B", "train", "base")
        for sha in order:
            git("cherry-pick", sha)  # check=True: a conflict raises
        assert [e.unit for e in kf.load(d)] == ["c"]


# ---------------------------------------------------------------------------
# The migration is complete: no gate keeps a private list.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_gate_keeps_a_private_list():
    ritz = WORKSPACE / "projects" / "ritz"
    import tomllib
    rz_toml = tomllib.loads((WORKSPACE / "rz.toml").read_text())
    assert "known_failing" not in rz_toml.get("ci", {})
    assert not list((ritz / "scripts").glob("regression-known-failures*.txt"))
    assert not (ritz / "tools" / "doc_known_failures").exists()
    for f, name in [("tools/run_regression_matrix.py", "EXPECTED_FAILURES ="),
                    ("tools/example_tests.py", "KNOWN_FAILING:"),
                    ("tools/check_doc_examples.py", "KNOWN_FAILURES:")]:
        assert name not in (ritz / f).read_text(), f
