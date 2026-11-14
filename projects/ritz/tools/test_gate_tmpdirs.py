"""Gate-run shell must not share /tmp names with a concurrent gate (AGAST #3178).

Up to two gates and six rooms share one host's /tmp.  ritz-task-3038's gate
exited 2 when the regression harness self-test's scratch dir vanished under
it (`test_scripts_ran.txt: No such file or directory`), while another room's
gate ran the same self-tests a few seconds ahead of it.  The re-run passed.  A
false gate failure costs a ~25-minute re-gate and can bounce a good commit.

The rule this file enforces, over everything the gate runs from a shell --
scripts/regression.sh, the scripts/test-regression-*.sh self-tests, every
example's test.sh, and the Makefile:

  * no literal /tmp path: a fixed name (`/tmp/ritz_ls_test`) is shared with
    every other gate running the same script, and a glob (`rm -f /tmp/*.ll`)
    deletes files other runs own.  Scratch comes from `mktemp -d`, which
    honours $TMPDIR and is unique.
  * no recursive rm of a glob: cleanup removes the one dir a run made, by name.
  * every self-test's scratch dir is a `mktemp -d` and its EXIT trap removes
    that dir -- the only place it is removed.

scripts/test-regression-tmpdirs.sh is the runtime half: two copies of the
self-tests run concurrently in one TMPDIR, beside another run's dir, and
both must pass without touching it.
"""

import re
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parent.parent
SCRIPTS = RITZ / "scripts"


def gate_shell_files():
    """Every file the gate executes as shell, ritz-relative."""
    files = [SCRIPTS / "regression.sh", RITZ / "Makefile"]
    files += sorted(SCRIPTS.glob("test-regression-*.sh"))
    files += sorted((RITZ / "examples").rglob("test.sh"))
    return [f for f in files if "/build/" not in str(f)]


def _code(line: str) -> str:
    """The line with a shell comment removed (`#` at start or after a blank)."""
    return re.split(r"(?:^|\s)#", line, maxsplit=1)[0]


# /tmp as a path component, not a suffix of something else ($SCRATCH/tmp).
TMP_PATH = re.compile(r"(?<![\w$}./-])/tmp(?![\w.-])")
# rm -r / -rf / -fr ... of an argument containing a glob star.
RM_GLOB = re.compile(r"\brm\s+(?:-\w*\s+)*-\w*r\w*\b[^;&|]*\*")


def tmp_violations(text: str):
    """[(line_no, line)] naming a literal /tmp path or rm -r'ing a glob."""
    return [
        (n, line.strip())
        for n, line in enumerate(text.splitlines(), 1)
        if TMP_PATH.search(_code(line)) or RM_GLOB.search(_code(line))
    ]


MKTEMP_VAR = re.compile(r"^\s*(\w+)=\$\(mktemp -d\b[^)]*\)", re.M)
TRAP_EXIT = re.compile(r"^\s*trap\s+(['\"]?)(.+?)\1\s+EXIT\s*$", re.M)


def scratch_owned_by_trap(text: str) -> bool:
    """True if the script's scratch is a `mktemp -d` whose EXIT trap removes it.

    The trap is either inline (`trap 'rm -rf "$X"' EXIT`) or names a function
    whose body does the removal.  The last EXIT trap is the one in force.
    """
    made = MKTEMP_VAR.findall(text)
    traps = TRAP_EXIT.findall(text)
    if not made or not traps:
        return False
    action = traps[-1][1]
    fn = re.search(rf"^{re.escape(action)}\(\)\s*\{{(.*?)^\}}", text, re.M | re.S)
    body = fn.group(1) if fn else action
    return any(re.search(rf'rm -rf "\${var}"', body) for var in made)


# --- the detectors are red-capable --------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("src", [
    "echo hi > /tmp/ritz_test_cat.txt",          # fixed shared name
    "mkdir -p /tmp/ritz_ls_test",                  # fixed shared dir
    "\t@rm -f /tmp/*.ll /tmp/*.o",                 # glob of other runs' files
    'rm -rf "$TMPDIR"/tmp.*',                      # glob cleanup, no literal
    "x=$(mktemp -d /tmp/foo.XXXXXX)",              # template pins /tmp
])
def test_detector_flags(src):
    assert tmp_violations(src) != []


@pytest.mark.unit
@pytest.mark.parametrize("src", [
    'T=$(mktemp -d); trap \'rm -rf "$T"\' EXIT',
    'grep -v x "$F" > "$SCRATCH/tmp" && mv "$SCRATCH/tmp" "$F"',
    "# a comment may say /tmp",
    'rm -rf "$sandbox"',
    "find . -name x -exec rm -rf {} +",
])
def test_detector_passes(src):
    assert tmp_violations(src) == []


@pytest.mark.unit
def test_trap_ownership_detector():
    inline = 'S=$(mktemp -d)\ntrap \'rm -rf "$S"\' EXIT\n'
    via_fn = 'S=$(mktemp -d)\ncleanup() {\n    pkill x\n    rm -rf "$S"\n}\ntrap cleanup EXIT\n'
    assert scratch_owned_by_trap(inline)
    assert scratch_owned_by_trap(via_fn)
    assert not scratch_owned_by_trap('S=/tmp/selftest\ntrap \'rm -rf "$S"\' EXIT\n')
    assert not scratch_owned_by_trap('S=$(mktemp -d)\ntrap \'rm -rf "$OTHER"\' EXIT\n')
    assert not scratch_owned_by_trap('S=$(mktemp -d)\n')


# --- the rule, over what the gate actually runs ------------------------------


@pytest.mark.unit
def test_gate_shell_names_no_tmp_path_and_globs_no_rm():
    offenders = {
        str(f.relative_to(RITZ)): hits
        for f in gate_shell_files()
        if (hits := tmp_violations(f.read_text()))
    }
    assert offenders == {}, (
        "gates share the host's /tmp: take scratch from `mktemp -d` and "
        f"remove it in your own EXIT trap (AGAST #3178): {offenders}"
    )


@pytest.mark.unit
def test_every_selftest_scratch_is_mktemp_removed_by_its_own_trap():
    selftests = sorted(SCRIPTS.glob("test-regression-*.sh"))
    assert len(selftests) >= 9, "the self-test glob has rotted"
    offenders = [f.name for f in selftests if not scratch_owned_by_trap(f.read_text())]
    assert offenders == []
