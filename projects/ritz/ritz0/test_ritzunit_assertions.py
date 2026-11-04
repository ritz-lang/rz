"""AGAST #2127: ritzunit.assertions is [[test_helper]] fns over `assert`.

#1869 gave `assert a OP b` both operands in its diagnostic and let a
`[[test_helper]]` fn assert, reporting the calling test's line (LANGUAGE_SPEC
§17.1, §19.2). That made ritzunit's per-type integer helpers (assert_eq_i32,
assert_lt_i32, ...) redundant, and their `return 1 on failure` contract was
the hazard #2137 patched with [[must_use]]: a bare call could never fail.

ritzunit.assertions now keeps only what `assert` cannot say on its own, the
string checks, and each one is a void `[[test_helper]]` that asserts:

  * a failure exits the test (status 1), so a bare call is the normal use;
  * the diagnostic's first line is the calling test's file:line, with both
    strings printed above it and `in helper ...` naming the helper;
  * junit still records the failure as "Test assertion failed".

Integer, bool and null checks are plain `assert`: `assert n == 3`,
`assert ok`, `assert p != null` print both operands (pointers in hex).
"""

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

RITZ0_DIR = Path(__file__).parent.resolve()
RITZ_DIR = RITZ0_DIR.parent
sys.path.insert(0, str(RITZ0_DIR))

import test_runner  # noqa: E402

RITZUNIT_DIR = RITZ_DIR.parent / "ritzunit"
ASSERTIONS = RITZUNIT_DIR / "src" / "assertions.ritz"

# The whole public surface: the string checks `assert` cannot express.
STRING_HELPERS = [
    "assert_str_eq", "assert_starts_with", "assert_contains",
    "assert_str_eq_sv", "assert_starts_with_sv", "assert_contains_sv",
]

# Replaced by `assert a OP b` / `assert cond` / `assert p == null`.
REMOVED = [
    "assert_eq_i32", "assert_eq_i64", "assert_ne_i32", "assert_ne_i64",
    "assert_lt_i32", "assert_le_i32", "assert_gt_i32", "assert_ge_i32",
    "assert_true", "assert_false", "assert_null", "assert_not_null",
]


@pytest.fixture
def package(tmp_path, monkeypatch):
    """A package whose test/test_case.ritz may `import ritzunit.assertions`."""
    monkeypatch.setenv("RITZ_PATH", str(RITZ_DIR))
    (tmp_path / "ritz.toml").write_text(textwrap.dedent(f"""\
        [package]
        name = "assertions_case"
        version = "0.1.0"
        sources = ["src"]

        [dependencies]
        ritzlib = {{ path = "{RITZ_DIR / 'ritzlib'}", sources = ["."] }}
        ritzunit = {{ path = "{RITZUNIT_DIR}" }}
        """))
    (tmp_path / "test").mkdir()
    (tmp_path / "src").mkdir()

    def write(source: str) -> Path:
        test_file = tmp_path / "test" / "test_case.ritz"
        test_file.write_text(textwrap.dedent(source))
        return test_file

    return write


def _build(test_file: Path, tmp_path: Path, compiler: str = "ritz0") -> str:
    scratch = tmp_path / "scratch"
    scratch.mkdir(exist_ok=True)
    exe, error = test_runner.build_test_binary(str(test_file), str(scratch), compiler)
    assert error is None, error
    return exe


def _report(exe: str, *args: str) -> dict:
    proc = subprocess.run([exe, "--json", *args], capture_output=True, timeout=120)
    return json.loads(proc.stdout)


def _results(exe: str) -> dict:
    """{test name: (status, output)} from one --json run."""
    return {t["name"]: (t["status"], t.get("output", ""))
            for t in _report(exe)["tests"]}


# --- the module's public surface ---------------------------------------------

def _pub_fns():
    """[(name, attribute line above it)] for every `pub fn` in assertions.ritz."""
    lines = ASSERTIONS.read_text().splitlines()
    out = []
    for i, line in enumerate(lines):
        m = re.match(r"pub fn (\w+)\(", line)
        if m:
            out.append((m.group(1), lines[i - 1].strip()))
    return out


@pytest.mark.unit
def test_only_the_string_helpers_are_exported():
    assert sorted(n for n, _ in _pub_fns()) == sorted(STRING_HELPERS)


@pytest.mark.unit
def test_every_helper_is_a_void_test_helper():
    lines = ASSERTIONS.read_text()
    for name, attr in _pub_fns():
        assert attr == "[[test_helper]]", f"{name} is not [[test_helper]]"
        # Void: a failure exits the test, there is no result to drop.
        sig = re.search(rf"pub fn {name}\([^)]*\)(.*)$", lines, re.M).group(1)
        assert "->" not in sig, f"{name} returns a value: {sig.strip()}"
    assert "[[must_use]]" not in lines


@pytest.mark.unit
@pytest.mark.parametrize("name", REMOVED)
def test_redundant_helpers_are_gone(name):
    assert not re.search(rf"\bfn {name}\(", ASSERTIONS.read_text())


# --- runtime behaviour --------------------------------------------------------

PASSING = """\
import ritzlib.strview
import ritzunit.assertions

[[test]]
fn cstr_helpers_hold() -> i32
    assert_str_eq(c"abc", c"abc")
    assert_str_eq(c"", c"")
    assert_starts_with(c"hello world", c"hello")
    assert_starts_with(c"hello", c"")
    assert_contains(c"hello world", c"o w")
    assert_contains(c"hello", c"hello")
    0

[[test]]
fn view_helpers_hold() -> i32
    var a: StrView = strview_from_cstr(c"needle in haystack")
    var b: StrView = strview_from_cstr(c"needle in haystack")
    var pre: StrView = strview_from_cstr(c"needle")
    var mid: StrView = strview_from_cstr(c"in hay")
    assert_str_eq_sv(@a, @b)
    assert_starts_with_sv(@a, @pre)
    assert_contains_sv(@a, @mid)
    0
"""


@pytest.mark.integration
def test_helpers_pass_when_they_hold(package, tmp_path):
    results = _results(_build(package(PASSING), tmp_path))
    assert results == {"cstr_helpers_hold": ("pass", ""),
                       "view_helpers_hold": ("pass", "")}, results


# helper -> (a failing call, text the diagnostic must show).
FAILING = {
    "assert_str_eq": ('assert_str_eq(c"abc", c"abd")',
                      ['expected: "abd"', 'actual:   "abc"']),
    "assert_starts_with": ('assert_starts_with(c"hello", c"help")',
                           ['string: "hello"', 'prefix: "help"']),
    "assert_contains": ('assert_contains(c"hello", c"xyz")',
                        ['haystack: "hello"', 'needle:   "xyz"']),
    "assert_str_eq_sv": ("assert_str_eq_sv(@a, @b)",
                         ['expected: "abd"', 'actual:   "abc"']),
    "assert_starts_with_sv": ("assert_starts_with_sv(@a, @b)",
                              ['string: "abc"', 'prefix: "abd"']),
    "assert_contains_sv": ("assert_contains_sv(@a, @b)",
                           ['haystack: "abc"', 'needle:   "abd"']),
}

CSTR_SOURCE = """\
import ritzlib.strview
import ritzunit.assertions

[[test]]
fn fails() -> i32
    {call}
    0
"""

VIEW_SOURCE = """\
import ritzlib.strview
import ritzunit.assertions

[[test]]
fn fails() -> i32
    var a: StrView = strview_from_cstr(c"abc")
    var b: StrView = strview_from_cstr(c"abd")
    {call}
    0
"""


def _failing_source(call: str) -> str:
    view = call.endswith("(@a, @b)")
    return (VIEW_SOURCE if view else CSTR_SOURCE).format(call=call)


def _failing_line(call: str) -> int:
    """The line `{call}` lands on: the test's line the diagnostic must name."""
    return 8 if call.endswith("(@a, @b)") else 6


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
@pytest.mark.parametrize("helper", list(FAILING))
def test_a_failure_fails_the_test_at_the_callers_line(package, tmp_path,
                                                      request, compiler, helper):
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    call, shown = FAILING[helper]
    exe = _build(package(_failing_source(call)), tmp_path, compiler)
    status, output = _results(exe)["fails"]
    assert status == "fail", output
    line = _failing_line(call)
    assert f"test_case.ritz:{line}: assertion failed: {helper.removesuffix('_sv')}" \
        in output, output
    assert "in helper assert_" in output, output
    for text in shown:
        assert text in output, output


@pytest.mark.integration
def test_junit_reports_a_helper_failure_as_an_assertion(package, tmp_path):
    exe = _build(package(_failing_source(FAILING["assert_contains"][0])), tmp_path)
    proc = subprocess.run([exe, "--junit"], capture_output=True, timeout=120)
    assert proc.returncode == 1
    assert b'<failure message="exit code 1">Test assertion failed</failure>' \
        in proc.stdout, proc.stdout
