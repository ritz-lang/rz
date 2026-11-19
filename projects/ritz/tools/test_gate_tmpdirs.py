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
    The one exception is a unix socket dir (AGAST #4135): a socket path must
    fit sun_path's 107 bytes, and a gate's TMPDIR sits deep in its worktree,
    so `SOCK_DIR=$(mktemp -d /tmp/NAME.XXXXXXXX)` alone on its line, still
    unique, still removed by the script's EXIT trap.
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
REPO = RITZ.parent.parent

# Shell the gate does not run, but people and rooms do, by hand, on a host
# other rooms share -- so a fixed /tmp name collides just the same
# (AGAST #3183).  Each one that needs scratch takes a `mktemp -d` and removes
# it in its own EXIT trap; the ritz1 Makefile writes under $(BUILD_DIR).
SHARED_HOST_SCRATCH_SCRIPTS = [
    SCRIPTS / "prove-stage5-divergence.sh",
    REPO / "bench" / "run.sh",
    REPO / "projects" / "mausoleum" / "tools" / "concurrent_test.sh",
    REPO / "projects" / "harland" / "tools" / "test_boot.sh",
    REPO / "projects" / "nexus" / "test" / "e2e_large_page.sh",
]
SHARED_HOST_SHELL = SHARED_HOST_SCRATCH_SCRIPTS + [
    RITZ / "ritz1" / "Makefile",
    REPO / "projects" / "ritz-lsp" / "test.sh",
    REPO / "projects" / "nexus" / "deploy" / "scripts" / "deploy.sh",
]


def gate_shell_files():
    """Every shell file the gate executes, plus SHARED_HOST_SHELL."""
    files = [SCRIPTS / "regression.sh", RITZ / "Makefile"]
    files += sorted(SCRIPTS.glob("test-regression-*.sh"))
    files += sorted((RITZ / "examples").rglob("test.sh"))
    files += SHARED_HOST_SHELL
    return [f for f in files if "/build/" not in str(f)]


def _code(line: str) -> str:
    """The line with a shell comment removed (`#` at start or after a blank)."""
    return re.split(r"(?:^|\s)#", line, maxsplit=1)[0]


# /tmp as a path component, not a suffix of something else ($SCRATCH/tmp).
TMP_PATH = re.compile(r"(?<![\w$}./-])/tmp(?![\w.-])")
# rm -r / -rf / -fr ... of an argument containing a glob star.
RM_GLOB = re.compile(r"\brm\s+(?:-\w*\s+)*-\w*r\w*\b[^;&|]*\*")


# The socket-dir exception: a whole line, a *SOCK_DIR variable, a unique
# mktemp template under /tmp and nothing else (AGAST #4135).
SOCK_DIR_MKTEMP = re.compile(
    r'^\s*\w*SOCK_DIR=("?)\$\(mktemp -d /tmp/[\w.-]+\.X{8,}\)\1\s*$'
)


def tmp_violations(text: str):
    """[(line_no, line)] naming a literal /tmp path or rm -r'ing a glob."""
    return [
        (n, line.strip())
        for n, line in enumerate(text.splitlines(), 1)
        if (TMP_PATH.search(_code(line)) and not SOCK_DIR_MKTEMP.match(_code(line)))
        or RM_GLOB.search(_code(line))
    ]


MKTEMP_VAR = re.compile(r"^\s*(\w+)=\"?\$\(mktemp -d\b[^)]*\)", re.M)
TRAP_EXIT = re.compile(r"^\s*trap\s+(['\"]?)(.+?)\1\s+EXIT\s*$", re.M)


def scratch_owned_by_trap(text: str) -> bool:
    """True if the script's scratch is a `mktemp -d` whose EXIT trap removes it
    -- every such dir, when it takes more than one (a socket dir, #4135).

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
    return all(re.search(rf"rm -rf [^\n]*\"\${var}\"", body) for var in made)


# --- the detectors are red-capable --------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("src", [
    "echo hi > /tmp/ritz_test_cat.txt",          # fixed shared name
    "mkdir -p /tmp/ritz_ls_test",                  # fixed shared dir
    "\t@rm -f /tmp/*.ll /tmp/*.o",                 # glob of other runs' files
    'rm -rf "$TMPDIR"/tmp.*',                      # glob cleanup, no literal
    "x=$(mktemp -d /tmp/foo.XXXXXX)",              # template pins /tmp
    "x=$(mktemp -d /tmp/foo.XXXXXXXX)",            # ...even for a socket, unless SOCK_DIR
    "SOCK_DIR=/tmp/zeus_sock",                     # SOCK_DIR, but a fixed shared name
    "SOCK_DIR=$(mktemp -d /tmp/s.XXXXXXXX); rm -f /tmp/x",  # exception covers one mktemp only
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
    'SOCK_DIR="$(mktemp -d /tmp/rz_e2e_sock.XXXXXXXX)"',  # sun_path (#4135)
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
    # Every mktemp dir, quoted or not, must be removed (#4135).
    two = 'S="$(mktemp -d)"\nK=$(mktemp -d /tmp/k.XXXXXXXX)\n'
    assert scratch_owned_by_trap(two + 'trap \'rm -rf "$S" "$K"\' EXIT\n')
    assert not scratch_owned_by_trap(two + 'trap \'rm -rf "$S"\' EXIT\n')


# --- the rule, over what the gate actually runs ------------------------------


@pytest.mark.unit
def test_gate_shell_names_no_tmp_path_and_globs_no_rm():
    offenders = {
        str(f.relative_to(REPO)): hits
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


# $RANDOM is not a unique name: 15 bits, and bash reseeds it in every $(...)
# fork, so two calls can draw the same value.  test-regression-xpass.sh named
# each helper's result file "$SCRATCH/r.$RANDOM"; a repeat handed a later case
# an earlier case's .verdict, and "unlisted + compiles -> no verdict" read
# `fail` (AGAST #4234).  Unique names come from mktemp, or a counter.
RANDOM_NAME = re.compile(r"\$\{?RANDOM\b")


@pytest.mark.unit
@pytest.mark.parametrize("src, hit", [
    ('local out="$SCRATCH/r.$RANDOM" msg', True),
    ('out="$SCRATCH/r.${RANDOM}"', True),
    ('out=$(mktemp "$SCRATCH/r.XXXXXX")', False),
    ("# never name scratch with $RANDOM", False),
])
def test_random_name_detector(src, hit):
    assert bool(RANDOM_NAME.search(_code(src))) is hit


@pytest.mark.unit
def test_no_selftest_names_scratch_with_random():
    offenders = {
        f.name: [n for n, line in enumerate(f.read_text().splitlines(), 1)
                 if RANDOM_NAME.search(_code(line))]
        for f in sorted(SCRIPTS.glob("test-regression-*.sh"))
    }
    offenders = {k: v for k, v in offenders.items() if v}
    assert offenders == {}, (
        "$RANDOM repeats across $(...) forks; name scratch files with mktemp "
        f"(AGAST #4234): {offenders}"
    )


@pytest.mark.unit
def test_shared_host_scripts_exist():
    """A renamed script must not silently drop out of the rule."""
    missing = [str(f.relative_to(REPO)) for f in SHARED_HOST_SHELL if not f.is_file()]
    assert missing == []


@pytest.mark.unit
def test_shared_host_script_scratch_is_mktemp_removed_by_its_own_trap():
    offenders = [
        str(f.relative_to(REPO))
        for f in SHARED_HOST_SCRATCH_SCRIPTS
        if not scratch_owned_by_trap(f.read_text())
    ]
    assert offenders == [], (
        "a script run on a shared host takes scratch from `mktemp -d` and "
        f"removes it in its own EXIT trap (AGAST #3183): {offenders}"
    )


# --- example programs: no fixed /tmp file name (AGAST #4207) -----------------
#
# The gate runs every example binary in regression Stages 1, 3 and 4, and two
# gates may run on one host at once.  54_async_fs wrote, read and unlinked
# c"/tmp/ritz_async_test.txt": one run's unlink landed between another's write
# and read, and Stage 1 went red on commits that never touched it.  An example
# builds its scratch path at run time -- a /tmp (or $TMPDIR) prefix finished
# with the pid -- so a string literal may hold a prefix ("/tmp/ritz_x_") but
# never a complete file name.

# A string literal holding a complete /tmp file name: "/tmp/<name>" whose last
# character does not leave it open for a pid/suffix (`_`, `-` or `/`).
RITZ_FIXED_TMP = re.compile(r'"/tmp/[^"]*[^_/"-]"')


def ritz_fixed_tmp_names(text: str):
    """[(line_no, line)] whose code (not a `#` comment) names a fixed /tmp file."""
    return [
        (n, line.strip())
        for n, line in enumerate(text.splitlines(), 1)
        if not line.lstrip().startswith("#") and RITZ_FIXED_TMP.search(line)
    ]


@pytest.mark.unit
def test_ritz_fixed_tmp_detector():
    flagged = [
        '    let path = c"/tmp/ritz_async_test.txt"',
        '    open(c"/tmp/nonexistent_file_xyz123.txt", O_RDONLY)',
        '    let d = "/tmp/ritz_dir"',
    ]
    passed = [
        '    strcpy(buf, c"/tmp/ritz_test_wc_")',            # pid appended
        '    var s: String = string_from_strview("/tmp/ritz_x-")',
        '        dir = "/tmp"',                                # a dir, not a file
        '# Build "/tmp/ritz_test_wc_<pid>.txt" into buf',     # a comment
    ]
    assert all(ritz_fixed_tmp_names(s) for s in flagged)
    assert not any(ritz_fixed_tmp_names(s) for s in passed)


@pytest.mark.unit
def test_examples_name_no_fixed_tmp_file():
    sources = [
        f for f in sorted((RITZ / "examples").rglob("*.ritz")) if "/build/" not in str(f)
    ]
    assert len(sources) > 100, "the example glob has rotted"
    offenders = {
        str(f.relative_to(RITZ)): hits
        for f in sources
        if (hits := ritz_fixed_tmp_names(f.read_text()))
    }
    assert offenders == {}, (
        "examples run concurrently on one host: build the scratch path from "
        f"$TMPDIR and the pid, never a fixed /tmp name (AGAST #4207): {offenders}"
    )
