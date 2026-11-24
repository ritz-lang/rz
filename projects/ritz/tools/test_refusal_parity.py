"""tools/refusal_parity.py and ritz0/harness/refusal_capture.py (AGAST #4669).

The compilers are faked (monkeypatched compile_ritz0 / compile_ritz1), so
these pin the judging and the known-failures rule, not ritz1's answers; the
real replay runs inside main.yml's "ritz0 unit tests" step.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parent / "ritz0" / "harness"))
import refusal_capture as rc  # noqa: E402
import refusal_parity as rp  # noqa: E402

pytestmark = pytest.mark.unit

ONLY = "tests/test_attrs.py"           # never names the second compiler
BOTH = "tests/test_reject_parity.py"   # runs it


def V(rc_, out=""):
    return rp.Verdict(rc_, out)


# --- judge ---------------------------------------------------------------

@pytest.mark.parametrize("v1, bad", [
    (V(1, "unit.ritz:3:5: error: x"), None),
    (V(1, "/elsewhere/unit.ritz:3:9: other wording"), None),   # line, not col or words
    (V(0, ""), "ACCEPTED"),
    (V(1, "unit.ritz:4:5: error: x"), "refused at unit.ritz:4"),
    (V(1, "lib.ritz:3:5: error: x"), "refused at lib.ritz:3"),
    (V(1, "error: x"), "no located diagnostic"),
    (V(1, "unit.ritz:2:1: error: first\nunit.ritz:3:5: error: x"), None),  # also reports it
    (V(-11, ""), "crashed"),
    (V(None, "ritz1 timed out"), "crashed"),
])
def test_judge(v1, bad):
    why = rp.judge(V(1, "unit.ritz:3:5: error: x"), v1)
    assert (why is None) if bad is None else (bad in why), why


def test_judge_unlocated_ritz0_needs_only_the_verdict():
    assert rp.judge(V(1, "error: no main"), V(1, "anything")) is None
    assert "ACCEPTED" in rp.judge(V(1, "error: no main"), V(0, ""))


# --- the replay end to end, with fake compilers ---------------------------

def _capture(tmp_path: Path, programs: dict[str, list[str]], ran=(), marker=True) -> Path:
    """A capture dir: {test: [source text, ...]} as in-process records."""
    d = tmp_path / "cap"
    (d / "src" / "inproc").mkdir(parents=True)
    if marker:
        (d / rp.MARKER).touch()
    lines = []
    for i, (test, srcs) in enumerate(programs.items()):
        for j, text in enumerate(srcs):
            p = d / "src" / "inproc" / f"{i}_{j}.ritz"
            p.write_text(text)
            lines.append({"kind": "inproc", "test": test,
                          "source": str(p.relative_to(d))})
    lines += [{"kind": "ran", "test": t} for t in ran]
    (d / "records-1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in lines))
    return d


def _fake(monkeypatch, tmp_path):
    """Sources are `<ritz0 verdict> <ritz1 verdict>`: `ok`, or `L` for a
    refusal at unit.ritz:L, or `crash`."""
    def verdict(word):
        if word == "ok":
            return V(0, "")
        if word == "crash":
            return V(-11, "")
        return V(1, f"unit.ritz:{word}:1: error: refused\n")

    monkeypatch.setattr(rp, "compile_ritz0",
                        lambda prog, out: verdict(prog.path.read_text().split()[0]))
    monkeypatch.setattr(rp, "compile_ritz1",
                        lambda r1, prog, out: verdict(prog.path.read_text().split()[1]))
    ritz1 = tmp_path / "ritz1"
    ritz1.write_text("")
    kf = tmp_path / "kf"
    kf.mkdir()
    monkeypatch.setenv("RITZ_KNOWN_FAILURES", str(kf))
    return ritz1, kf


def _excuse(kf: Path, test: str, agast=4657):
    (kf / f"{agast}.toml").write_text(
        f'[[entry]]\ngate = "refusal"\ncompiler = "ritz1"\nunit = "{test}"\n'
        f'reason = "ritz1 accepts it"\nagast = {agast}\n')


def _run(cap, ritz1, capsys):
    rc_ = rp.main(["replay", str(cap), "--ritz1", str(ritz1), "-j", "2"])
    return rc_, capsys.readouterr().out


def test_agreement_is_green(tmp_path, monkeypatch, capsys):
    ritz1, _ = _fake(monkeypatch, tmp_path)
    cap = _capture(tmp_path, {f"{ONLY}::test_a": ["3 3", "ok ok", "ok 5"]})
    rc_, out = _run(cap, ritz1, capsys)
    assert rc_ == 0, out
    # ritz0 accepting is not judged, even where ritz1 refuses (not goal 3).
    assert "ritz0 refused 1" in out and "ritz1 disagreed on 0" in out


@pytest.mark.parametrize("src, why", [
    ("3 ok", "ACCEPTED"),
    ("3 4", "refused at unit.ritz:4, ritz0 at unit.ritz:3"),
    ("3 crash", "crashed"),
])
def test_a_disagreement_no_entry_excuses_is_red(tmp_path, monkeypatch, capsys, src, why):
    ritz1, _ = _fake(monkeypatch, tmp_path)
    cap = _capture(tmp_path, {f"{ONLY}::test_a": ["3 3", src]})
    rc_, out = _run(cap, ritz1, capsys)
    assert rc_ == 1, out
    assert f"FAIL   {ONLY}::test_a" in out and why in out


def test_an_entry_excuses_its_test_only(tmp_path, monkeypatch, capsys):
    ritz1, kf = _fake(monkeypatch, tmp_path)
    _excuse(kf, f"{ONLY}::test_a")
    cap = _capture(tmp_path, {f"{ONLY}::test_a": ["3 ok"]})
    rc_, out = _run(cap, ritz1, capsys)
    assert rc_ == 0, out
    assert f"KNOWN  {ONLY}::test_a  (AGAST #4657" in out
    cap2 = _capture(tmp_path / "2", {f"{ONLY}::test_b": ["3 ok"]})
    assert _run(cap2, ritz1, capsys)[0] == 1


def test_an_entry_that_now_passes_is_red(tmp_path, monkeypatch, capsys):
    """Strict xpass: the list only shrinks."""
    ritz1, kf = _fake(monkeypatch, tmp_path)
    _excuse(kf, f"{ONLY}::test_a")
    cap = _capture(tmp_path, {f"{ONLY}::test_a": ["3 3"]})
    rc_, out = _run(cap, ritz1, capsys)
    assert rc_ == 1 and f"XPASS  {ONLY}::test_a" in out, out


def test_an_entry_for_a_test_that_ran_and_captured_nothing_is_red(tmp_path, monkeypatch, capsys):
    ritz1, kf = _fake(monkeypatch, tmp_path)
    _excuse(kf, f"{ONLY}::test_a")
    cap = _capture(tmp_path, {}, ran=[f"{ONLY}::test_a"])
    assert _run(cap, ritz1, capsys)[0] == 1


def test_an_entry_for_a_test_that_did_not_run_is_neither(tmp_path, monkeypatch, capsys):
    """The likely-first pre-pass judges a few files; the rest run later."""
    ritz1, kf = _fake(monkeypatch, tmp_path)
    _excuse(kf, f"{ONLY}::test_a")
    cap = _capture(tmp_path, {f"{ONLY}::test_b": ["3 3"]})
    assert _run(cap, ritz1, capsys)[0] == 0


def test_no_marker_is_red_never_a_silent_green(tmp_path, monkeypatch, capsys):
    ritz1, _ = _fake(monkeypatch, tmp_path)
    cap = _capture(tmp_path, {}, marker=False)
    rc_, out = _run(cap, ritz1, capsys)
    assert rc_ == 1 and "did not capture" in out


def test_a_bad_list_is_exit_2(tmp_path, monkeypatch, capsys):
    ritz1, kf = _fake(monkeypatch, tmp_path)
    (kf / "4657.toml").write_text(
        '[[entry]]\ngate = "refusal"\ncompiler = "ritz0"\nunit = "x"\n'
        'reason = "r"\nagast = 4657\n')
    assert _run(_capture(tmp_path, {}), ritz1, capsys)[0] == 2


# --- the capture side ------------------------------------------------------

def test_ritz0_only_reads_the_test_file():
    assert rc.ritz0_only(f"{ONLY}::test_x")
    assert not rc.ritz0_only(f"{BOTH}::test_x")
    assert not rc.ritz0_only("tests/test_no_such_file.py::t")


def _records(d: Path) -> list[dict]:
    return [json.loads(l) for f in d.glob("records-*.jsonl")
            for l in f.read_text().splitlines()]


def test_capture_is_off_without_the_env(tmp_path, monkeypatch):
    monkeypatch.delenv(rc.ENV, raising=False)
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{ONLY}::t (call)")
    rc.on_lex("fn f() -> i32\n    0\n", "<test>")
    assert not list(tmp_path.iterdir())


def test_capture_records_a_refusal_and_an_inproc_source(tmp_path, monkeypatch):
    d = tmp_path / "cap"
    monkeypatch.setenv(rc.ENV, str(d))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{ONLY}::test_x[a] (call)")
    prog = tmp_path / "t" / "unit.ritz"
    prog.parent.mkdir()
    prog.write_text("fn main() -> i32\n    x\n")
    rc.on_cli(["unit.ritz", "-o", "unit.ll"], str(prog.parent),
              {"RITZ_PATH": str(rc.RITZ_ROOT)}, 1, b"unit.ritz:2:5: error\n")
    rc.on_cli(["unit.ritz", "-o", "unit.ll"], str(prog.parent), {}, 0, b"")  # accepted
    rc.on_lex("fn g() -> i32\n    1\n", "<test>")
    rc.on_lex("fn g() -> i32\n    1\n", "<test>")    # once per test
    rc.on_lex("fn h() -> i32\n    1\n", "h.ritz")    # a CLI file: not in-process
    recs = _records(d)
    assert [r["kind"] for r in recs] == ["cli", "inproc"], recs
    cli, inproc = recs
    assert cli["test"] == f"{ONLY}::test_x[a]" and cli["ritz_path"] == ["@RITZ_ROOT"]
    assert (d / cli["dir"] / "unit.ritz").read_text() == prog.read_text()
    assert (d / inproc["source"]).read_text().startswith("fn g()")
    # ...and the replay reads it back.
    cap = rp.load_capture(d)
    assert len(cap.programs[f"{ONLY}::test_x[a]"]) == 2


def test_capture_ignores_a_test_that_runs_ritz1(tmp_path, monkeypatch):
    d = tmp_path / "cap"
    monkeypatch.setenv(rc.ENV, str(d))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{BOTH}::t (call)")
    rc.on_lex("fn g() -> i32\n    1\n", "<test>")
    rc.on_test_ran(f"{BOTH}::t")
    assert _records(d) == []


def test_main_yml_step_captures_and_replays():
    """The wiring: the step sets the env for pytest and replays the dir."""
    yml = (TOOLS.parent.parent.parent / ".github" / "workflows" / "main.yml").read_text()
    step = yml.split("- name: ritz0 unit tests", 1)[1].split("\n      - name:", 1)[0]
    assert "RITZ_REFUSAL_CAPTURE=" in step
    assert "tools/refusal_parity.py replay" in step


def test_make_unit_does_not_capture():
    """`make unit` pays nothing: no capture there (AGAST #4669 cost limit)."""
    mk = (TOOLS.parent / "Makefile").read_text()
    unit = mk.split("\nunit:", 1)[1].split("\n\n", 1)[0]
    assert "RITZ_REFUSAL_CAPTURE" not in unit


@pytest.mark.integration
def test_run_ritz0_captures_a_real_refusal(tmp_path, monkeypatch):
    """The hook in ritz0_inproc.run_ritz0, through a real forked ritz0."""
    import ritz0_inproc
    d = tmp_path / "cap"
    monkeypatch.setenv(rc.ENV, str(d))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", f"{ONLY}::test_planted (call)")
    work = tmp_path / "w"
    work.mkdir()
    (work / "unit.ritz").write_text("fn main() -> i32\n    let x: i32 = nope\n    x\n")
    cp = ritz0_inproc.run_ritz0(["unit.ritz", "-o", "unit.ll"], cwd=work,
                                env=dict(os.environ), timeout=120)
    assert cp.returncode != 0, cp.stderr
    [rec] = _records(d)
    assert rec["kind"] == "cli" and rec["test"] == f"{ONLY}::test_planted"
    assert (d / rec["dir"] / "unit.ritz").is_file()


def test_a_refusal_ritz0_does_not_repeat_is_not_judged(tmp_path, monkeypatch, capsys):
    """A forkserver status read can fail (exit 255 after "Compiled"): a
    refusal counts only if a second ritz0 compile refuses too."""
    ritz1, _ = _fake(monkeypatch, tmp_path)
    calls = []

    def flaky(prog, out):
        calls.append(prog.path.name)
        return V(255, "Compiled x.ritz -> x.ll\n") if len(calls) == 1 else V(0, "")

    monkeypatch.setattr(rp, "compile_ritz0", flaky)
    cap = _capture(tmp_path, {f"{ONLY}::test_a": ["3 ok"]})
    rc_, out = _run(cap, ritz1, capsys)
    assert rc_ == 0 and len(calls) == 2, out
    assert "ritz0 refused 0" in out and "1 not repeated" in out
