"""AGAST #1595: catch artifact-existence skips locally, not only on a cold CI tree.

main.yml's `ritz0 unit tests` step (AGAST #1327) fails the bootstrap job when
pytest's `-rs` report has a skip reason like "not built" or "does not exist".
That step runs before the bootstrap chain builds ritz1, so CI always sees a
cold tree. A developer's tree is usually warm. A skip such as

    if not (RITZ_DIR / "ritz1" / "build" / "ritz1").exists():
        pytest.skip("ritz1 binary not built")

never fires locally, passes `make ci-local`, and then turns `main` red. That
is exactly how #1538 broke CI at 3876096.

So this module applies the guard's own regex statically, to every skip reason
literal in this directory, and the verdict no longer depends on what happens
to be built. The regex is read from main.yml rather than copied, so it stays
in sync with whatever CI enforces.
"""

import ast
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MAIN_YML = HERE.parents[2] / ".github" / "workflows" / "main.yml"

# The guard line in main.yml looks like:
#   if grep -iE "SKIPPED.*(not built|...)" pytest-report.txt; then
_GUARD_LINE = re.compile(r'grep -iE "(SKIPPED[^"]*)" pytest-report\.txt')


def _ci_guard_regex() -> re.Pattern:
    text = MAIN_YML.read_text()
    found = _GUARD_LINE.findall(text)
    assert len(found) == 1, (
        f"expected exactly one artifact-skip guard in {MAIN_YML}, found {found!r}; "
        "if the guard moved, update _GUARD_LINE here rather than deleting this test"
    )
    return re.compile(found[0], re.IGNORECASE)


def _string_parts(node: ast.AST) -> list[str]:
    """Literal text in a str constant or f-string. Interpolated parts are dropped."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return ["".join(
            v.value for v in node.values
            if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )]
    return []


def _skip_reasons(source: str) -> list[tuple[int, str]]:
    """(line, reason) for every pytest.skip(...) / skipif(..., reason=...) call."""
    reasons = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "skip":
            candidates = list(node.args[:1]) + [k.value for k in node.keywords if k.arg in ("reason", "msg")]
        elif name == "skipif":
            candidates = [k.value for k in node.keywords if k.arg == "reason"]
        else:
            continue
        for cand in candidates:
            reasons.extend((node.lineno, s) for s in _string_parts(cand))
    return reasons


# AGAST #1333: the #1327 word list matched 0 of the 12 skip reasons then in
# the tree; the only lines it fired on were the two #1327 itself deleted.
# These are pytest `-rs` lines, verbatim in shape, each a skip on a missing
# file or artifact. A tracked file that is absent means a broken checkout, so
# the test should fail, not skip.
ARTIFACT_SKIPS = [
    "SKIPPED [1] test_build.py:1158: ritz1 binary not built",
    "SKIPPED [1] test_skipfmt.py:9: ritz1 not found",
    "SKIPPED [1] test_metadata.py:603: No .ritz-cache directory found",
    "SKIPPED [1] test_metadata.py:607: No .ritz-meta files found in cache",
    "SKIPPED [2] test_x.py:5: sample program missing",
    "SKIPPED [1] test_x.py:5: Missing fixture file",
    "SKIPPED [1] test_x.py:5: /tmp/x: No such file or directory",
]

# Skips that are about the machine, not the checkout. These stay legitimate,
# and a guard that fires on them turns CI red for no defect.
ENVIRONMENT_SKIPS = [
    "SKIPPED [1] test_x.py:1: no `opt` on PATH",
    "SKIPPED [3] test_build.py:827: no `opt`/`llvm-as` on PATH",
    "SKIPPED [1] test_build.py:1289: clang not on PATH",
    "SKIPPED [1] test_o2_libc_names.py:70: clang not on PATH",
    "SKIPPED [1] test_ritz1_fn_cache_uninit.py:64: valgrind not installed",
    "SKIPPED [1] test_indium_iac.py:97: terraform not installed",
    "SKIPPED [1] test_indium_mkuefi.py:41: mkfs.vfat / mtools not installed",
    "SKIPPED [2] test_crypto_intrinsics.py:44: CPU doesn't support AES-NI",
    "SKIPPED [1] test_ritz1_aesni_intrinsics.py:134: CPU lacks AES-NI",
    "SKIPPED [2] test_ritzunit_core.py:113: hard RLIMIT_CORE is 0",
    # The guard reads only the reason. A file name that contains a guard
    # word must not trip it.
    "SKIPPED [1] test_missing_found_no_such_file.py:3: clang not on PATH",
]


@pytest.mark.unit
@pytest.mark.parametrize("line", ARTIFACT_SKIPS)
def test_guard_fires_on_artifact_skip(line):
    """A planted missing-artifact skip must turn the CI step red. Otherwise the scan below proves nothing."""
    assert _ci_guard_regex().search(line), f"CI guard misses: {line}"


@pytest.mark.unit
@pytest.mark.parametrize("line", ENVIRONMENT_SKIPS)
def test_guard_spares_environment_skip(line):
    assert not _ci_guard_regex().search(line), f"CI guard would fail on a legitimate skip: {line}"


@pytest.mark.unit
def test_scanner_finds_skip_reasons():
    """The AST scan must pick up every shape the guard can match."""
    src = (
        "import pytest\n"
        "pytest.skip('ritz1 binary not built')\n"
        "pytest.skip(reason=f'{x} does not exist')\n"
        "m = pytest.mark.skipif(True, reason='sample not present')\n"
    )
    assert [r for _, r in _skip_reasons(src)] == [
        "ritz1 binary not built", " does not exist", "sample not present",
    ]


@pytest.mark.unit
def test_no_skip_reason_trips_the_ci_artifact_guard():
    guard = _ci_guard_regex()
    offenders = []
    for path in sorted(HERE.glob("*.py")):
        if path.name == Path(__file__).name:
            continue
        for line, reason in _skip_reasons(path.read_text()):
            if guard.search(f"SKIPPED [1] {path.name}:{line}: {reason}"):
                offenders.append(f"{path.name}:{line}: {reason!r}")
    assert not offenders, (
        "these skips would fail CI's #1327 guard on a cold tree. Build the "
        "artifact in the test instead of skipping:\n  " + "\n  ".join(offenders)
    )
