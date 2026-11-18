"""The shape of docs/STANDARD.md, the one normative Ritz standard (AGAST #1344).

check_doc_examples.py compiles the standard's blocks; this holds the doc to
the promises its markers make, so an ADVISORY rule can't pass for an ENFORCED
one:

  ENFORCED  a tool refuses a violation: the rule shows the refusal in an
            ``expect-error`` block, or names the ``make`` target that fails.
  CHECKED   a compiled block proves the construct the rule asks for works.
  ADVISORY  human judgement. Where it can be counted, ``Report:`` names a
            tools/standard_report.py key, so the count is a command.

It also pins the consolidation: the old STYLE.md paths are pointers with no
code, and the Makefile's doc gate compiles STANDARD.md, not STYLE.md.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from standard_report import RULES

pytestmark = pytest.mark.unit

RITZ = Path(__file__).resolve().parent.parent
STANDARD = RITZ / "docs" / "STANDARD.md"
MAKEFILE = RITZ / "Makefile"
MARKERS = ("ENFORCED", "CHECKED", "ADVISORY")
RULE_RE = re.compile(r"^#### (S-[A-Z]+-\d+) \S")
STATUS_RE = re.compile(r"^\*\*Status: (\w+)\*\*")


def rules(text):
    """{rule id: lines of its section}, a section ending at the next heading."""
    out, cur = {}, None
    for line in text.split("\n"):
        if line.startswith("#"):
            m = RULE_RE.match(line)
            cur = m.group(1) if m else None
            if cur:
                assert cur not in out, f"{cur} is declared twice"
                out[cur] = []
            continue
        if cur:
            out[cur].append(line)
    return out


def fences(lines):
    """The info strings of the ```ritz fences in `lines`."""
    return [ln.strip()[3:] for ln in lines if ln.strip().startswith("```ritz")]


def compiled(info):
    return "expect-error" not in info and "no-compile" not in info


@pytest.fixture(scope="module")
def doc():
    return STANDARD.read_text()


@pytest.fixture(scope="module")
def sections(doc):
    return rules(doc)


def test_the_standard_has_rules(sections):
    assert len(sections) >= 20


def test_every_rule_has_exactly_one_marker_first(sections):
    for rid, lines in sections.items():
        body = [ln for ln in lines if ln.strip()]
        assert body, f"{rid} is empty"
        m = STATUS_RE.match(body[0])
        assert m and m.group(1) in MARKERS, f"{rid}: first line must be **Status: <{'|'.join(MARKERS)}>**"
        assert sum(bool(STATUS_RE.match(ln)) for ln in lines) == 1, f"{rid}: one status line"


def _status(lines):
    return next(STATUS_RE.match(ln).group(1) for ln in lines if STATUS_RE.match(ln))


def test_enforced_rules_show_the_refusal(sections):
    targets = set(re.findall(r"^([\w-]+):", MAKEFILE.read_text(), re.M))
    for rid, lines in sections.items():
        if _status(lines) != "ENFORCED":
            continue
        refused = any("expect-error" in f for f in fences(lines))
        named = [t for t in re.findall(r"Enforced by: `make ([\w-]+)`", "\n".join(lines))]
        assert refused or named, f"{rid}: ENFORCED needs an expect-error block or `Enforced by: \\`make <target>\\``"
        for t in named:
            assert t in targets, f"{rid}: no Makefile target {t!r}"


def test_checked_rules_compile_an_example(sections):
    for rid, lines in sections.items():
        if _status(lines) == "CHECKED":
            assert any(compiled(f) for f in fences(lines)), f"{rid}: CHECKED needs a compiled ```ritz block"


def test_report_keys_belong_to_their_rule(sections):
    seen = {}
    for rid, lines in sections.items():
        for key in re.findall(r"^Report: `([\w-]+)`", "\n".join(lines), re.M):
            assert key in RULES, f"{rid}: Report key {key!r} is not a standard_report.py rule"
            assert RULES[key][0] == rid, f"{key} counts {RULES[key][0]}, but is reported under {rid}"
            seen[key] = rid
    assert set(seen) == set(RULES), f"keys with no rule: {sorted(set(RULES) - set(seen))}"


def test_no_sketches(doc):
    """LARB R8: a rule doesn't run ahead of the compilers with a no-compile block."""
    assert not [f for f in fences(doc.split("\n")) if "no-compile" in f]


def test_the_doc_gate_compiles_the_standard():
    m = re.search(r"^DOC_EXAMPLE_DOCS := \\\n((?:\t.*\n)+)", MAKEFILE.read_text(), re.M)
    docs = m.group(1).replace("\\", " ").split()
    assert "docs/STANDARD.md" in docs
    assert "docs/STYLE.md" not in docs


@pytest.mark.parametrize("old", ["STYLE.md", "docs/STYLE.md"])
def test_old_paths_are_pointers(old):
    text = (RITZ / old).read_text()
    assert "STANDARD.md" in text
    assert "```ritz" not in text, f"{old} must not carry code: exactly one normative doc"
    assert len(text.split("\n")) < 40
