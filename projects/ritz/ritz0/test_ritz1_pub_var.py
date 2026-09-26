"""Regression tests for AGAST #1508 — ritz1 must parse a `pub var` global.

ritz1's `global_var_def` rule had no `PUB` alternative (unlike `pub fn`,
`pub const`, `pub struct`, `pub type`, `pub enum`), so

    pub var g: i64 = 0

    pub fn main() -> i32
        return 0

failed with "cannot parse item starting at 'pub'" (ritz0: exit 0).  That kept
rzsh/common.ritz, and every module importing it, off ritz1.

ritz1 has no per-item visibility: every module that sees a global emits it
`weak_odr` and the linker merges them into one storage, so `pub` only needs
to parse.  The cross-module tests compile helper and main as separate modules
(as build.py does), link them, and pin that both sides share the one global.
Global initializers are honoured since #1501, so the exit code IS the value.
"""

import os
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BIN = RITZ_ROOT / "ritz1" / "build" / "ritz1"
RITZ0 = RITZ_ROOT / "ritz0" / "ritz0.py"
# Build product, not a tracked file — see test_ritz1_ptr_arith_chain.py.
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"


def _make(target_dir: str, target: str, product: Path) -> None:
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run(
        ["make", "-C", target_dir, target],
        cwd=RITZ_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    if proc.returncode != 0 or not product.exists():
        pytest.fail(
            f"could not build {product}:\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )


@pytest.fixture(scope="module")
def ritz1_bin() -> Path:
    # A stale binary would test the old parser.
    _make("ritz1", "ritz1", RITZ1_BIN)
    _make("runtime", RITZ_START.name, RITZ_START)
    return RITZ1_BIN


# --- the ticket's repro, verbatim ------------------------------------------

REPRO = """\
pub var g: i64 = 0

pub fn main() -> i32
    return 0
"""

# --- single-module forms: exit code is what the global held ----------------

SINGLE_MODULE = {
    "pub_var_init": """\
pub var g: i32 = 5

pub fn main() -> i32
    return g
""",
    # No initializer: the `VAR IDENT COLON type_spec NEWLINE` alternative.
    "pub_var_no_init": """\
pub var g: i32

pub fn main() -> i32
    g = 5
    return g
""",
    # A pub var after other pub items must not stop item* early.
    "pub_var_between_items": """\
pub const K: i32 = 2

pub var g: i32 = 3

pub fn add() -> i32
    return g + K

pub fn main() -> i32
    return add()
""",
    # [[attr]] prefix, as items take attrs.
    "pub_var_with_attr": """\
[[inline]]
pub var g: i32 = 5

pub fn main() -> i32
    return g
""",
}

# --- cross-module: helper declares, main imports and reads/writes ----------
# (helper source, main source, expected exit code)

CROSS_MODULE = {
    # The ticket's acceptance: a second module reads the pub var.
    "read": (
        "pub var counter: i64 = 5\n",
        "import helper\n\npub fn main() -> i32\n    return counter as i32\n",
        5,
    ),
    # rzsh/common.ritz shape: pub var with no initializer, set via a pub fn
    # in the declaring module, read in the importer.
    "write_in_helper_read_in_main": (
        "pub var state: i32\n\npub fn set_state(v: i32)\n    state = v\n",
        "import helper\n\npub fn main() -> i32\n    set_state(6)\n    return state\n",
        6,
    ),
    # Importer writes, declaring module reads — one storage, not two copies.
    "write_in_main_read_in_helper": (
        "pub var state: i32 = 1\n\npub fn get_state() -> i32\n    return state\n",
        "import helper\n\npub fn main() -> i32\n    state = 7\n    return get_state()\n",
        7,
    ),
}


def _compile(compiler: str, cwd: Path, src: Path, ll: Path):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        cmd = ["python3", str(RITZ0), str(src), "-o", str(ll)]
    else:
        cmd = [str(RITZ1_BIN), str(src), "-o", str(ll), "-I", str(cwd)]
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=300
    )


def _link_run(compiler: str, cwd: Path, lls: list, exe: Path) -> int:
    link_cmd = ["clang", *map(str, lls), "-o", str(exe), "-nostdlib"]
    if compiler == "ritz1":
        link_cmd.insert(2, str(RITZ_START))
    link = subprocess.run(link_cmd, cwd=cwd, capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler} IR would not link:\n{link.stderr[-2000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _run_single(compiler: str, tmp_path: Path, name: str, program: str) -> int:
    src = tmp_path / f"{name}.ritz"
    src.write_text(program)
    ll = tmp_path / f"{name}.ll"
    comp = _compile(compiler, tmp_path, src, ll)
    assert comp.returncode == 0 and ll.exists(), (
        f"{compiler} failed to compile {name}:\n{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
    )
    return _link_run(compiler, tmp_path, [ll], tmp_path / name)


def _run_cross(compiler: str, tmp_path: Path, helper: str, main: str) -> int:
    """Compile helper and main as separate modules, link them, run.

    Both compilers emit modularly: an importer only *declares* the imported
    module's fns, so helper.ll must be linked in, as build.py does.
    """
    lls = []
    for name, text in (("helper", helper), ("main", main)):
        src = tmp_path / f"{name}.ritz"
        src.write_text(text)
        ll = tmp_path / f"{name}.ll"
        comp = _compile(compiler, tmp_path, src, ll)
        assert comp.returncode == 0 and ll.exists(), (
            f"{compiler} failed to compile {name}:\n"
            f"{comp.stdout[-2000:]}\n{comp.stderr[-2000:]}"
        )
        lls.append(ll)
    return _link_run(compiler, tmp_path, lls, tmp_path / "main")


@pytest.mark.integration
def test_ritz0_repro_oracle(tmp_path):
    assert _run_single("ritz0", tmp_path, "repro", REPRO) == 0


@pytest.mark.integration
def test_ritz1_parses_repro(ritz1_bin, tmp_path):
    """AGAST #1508, verbatim. Before the fix: 'cannot parse item starting at pub'."""
    assert _run_single("ritz1", tmp_path, "repro", REPRO) == 0


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(SINGLE_MODULE))
def test_ritz1_pub_var_single_module(ritz1_bin, tmp_path, name):
    assert _run_single("ritz1", tmp_path, name, SINGLE_MODULE[name]) == 5


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CROSS_MODULE))
def test_ritz0_cross_module_oracle(tmp_path, name):
    helper, main, expected = CROSS_MODULE[name]
    assert _run_cross("ritz0", tmp_path, helper, main) == expected


@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(CROSS_MODULE))
def test_ritz1_pub_var_cross_module(ritz1_bin, tmp_path, name):
    helper, main, expected = CROSS_MODULE[name]
    assert _run_cross("ritz1", tmp_path, helper, main) == expected


@pytest.mark.integration
def test_ritz1_plain_var_still_parses(ritz1_bin, tmp_path):
    """The non-pub alternatives must keep working after the PUB arms are added."""
    program = "var g: i32 = 4\nvar h: i32\n\npub fn main() -> i32\n    h = 1\n    return g + h\n"
    assert _run_single("ritz1", tmp_path, "plain", program) == 5
