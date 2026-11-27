"""rllvm against the clang oracle, entry by entry (../razm/DESIGN.md "Tests").

The oracle half always runs: clang compiles every entry, every link
succeeds, and the runnable binaries run, so the corpus is proven today.
rllvm exits 2 for a file it cannot compile yet; that entry is an expected
failure naming what it waits on, never a pass and never a skip. Any other
non-zero exit is a failure. Exit 0 links rllvm's objects in clang's place,
compares link status, stdout and exit status, runs the entry's disassembly
and symbol checks, and checks every relocation against the profile table.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import corpus as c

PKG = Path(__file__).resolve().parent.parent
EXIT_UNSUPPORTED = 2

# The runnable hosted entries, the objects each links (hello's shape: the
# shim, these, then the razm object), and the oracle's exit status.
RUNS = {
    "hello": (["hosted/hello.ll"], 30),
    "intrin_run": (["hosted/intrin_run.ll"], 1),
    "asm_run": (["hosted/asm_run.ll"], 0),
    "abi": (["hosted/abi_a.ll", "hosted/abi_b.ll"], 0),
    "comdat": (["hosted/comdat_a.ll", "hosted/comdat_b.ll"], 0),
    "weak_strong": (["hosted/weak_strong.ll"], 7),
}
# The ODR functions comdat_a and comdat_b define; one copy survives a link.
COMDAT_FUNCTIONS = ["future_poll", "shared_a$poll", "shared_b$poll"]
# Link-only hosted entries and the disassembly each must show.
DISASSEMBLY = {
    "hosted/asm.ll": c.ASM_MNEMONICS,
    "hosted/simd.ll": c.SIMD_MNEMONICS,
    "hosted/intrin.ll": c.INTRIN_MNEMONICS,
}
# Freestanding links: the script (None: --pie --no-dynamic-linker) and
# whether the Harland shim goes in.
FREESTANDING = {
    "freestanding/pic.ll": (None, True),
    "freestanding/kernel.ll": ("freestanding/kernel.ld", False),
    "freestanding/large.ll": ("freestanding/linker.ld", True),
}
# Entries rllvm must compile: exit 2 on one is a failure, never an xfail.
# abi_a/abi_b: the call ABI (#4804) linked against clang's object both ways.
REQUIRED = {"hosted/abi_a.ll", "hosted/abi_b.ll"}
LINUX_SHIM = "hosted/shim.ll"
HARLAND_SHIM = "freestanding/harland_start.ll"


class Build:
    """Objects and links for one session, each oracle object built once."""

    def __init__(self, root: Path):
        self.root = root
        self._clang: dict[str, Path] = {}
        self.hosted_extra = c.assemble("hosted", root / "extra_hosted.o")
        self.freestanding_extra = c.assemble("freestanding",
                                             root / "extra_freestanding.o")

    def clang(self, rel: str) -> Path:
        if rel not in self._clang:
            e = c.entry(rel)
            self._clang[rel] = c.clang_compile(e, self.root / f"{e.stem}.clang.o")
        return self._clang[rel]

    def hosted(self, objs: list[Path], name: str, shim: Path | None = None) -> Path:
        out = self.root / name
        r = c.link_hosted([shim or self.clang(LINUX_SHIM), *objs,
                           self.hosted_extra], out)
        assert r.returncode == 0, f"link {name}: {r.stderr}"
        return out

    def freestanding(self, rel: str, obj: Path, name: str,
                     shim: Path | None = None) -> Path:
        script, with_shim = FREESTANDING[rel]
        objs = [obj, self.freestanding_extra]
        if with_shim:
            objs.insert(0, shim or self.clang(HARLAND_SHIM))
        out = self.root / name
        r = (c.link_script(script, objs, out) if script
             else c.link_pie(objs, out))
        assert r.returncode == 0, f"link {name}: {r.stderr}"
        return out


@pytest.fixture(scope="session")
def build(tmp_path_factory) -> Build:
    return Build(tmp_path_factory.mktemp("oracle"))


@pytest.fixture(scope="session")
def oracle_runs(build) -> dict[str, c.RunResult]:
    """Each runnable entry's oracle binary, run once."""
    return {name: c.run(build.hosted([build.clang(r) for r in rels], f"{name}.clang"))
            for name, (rels, _) in RUNS.items()}


@pytest.fixture(scope="session")
def rllvm() -> list[str]:
    """The rllvm under test: $RLLVM, else this package's debug build."""
    path = Path(os.environ.get("RLLVM") or PKG / "build" / "debug" / "rllvm")
    if not os.access(path, os.X_OK):
        pytest.fail(f"rllvm is not built at {path}: run ./rz build rllvm first")
    return [str(path)]


def rllvm_compile(rllvm: list[str], rel: str, root: Path) -> Path:
    """rllvm's object for `rel`, its relocations checked; xfail on exit 2
    unless `rel` is REQUIRED."""
    e = c.entry(rel)
    out = root / f"{e.stem}.rllvm.o"
    r = c.compile_entry(rllvm, e, out)
    if r.returncode == EXIT_UNSUPPORTED and rel not in REQUIRED:
        pytest.xfail(f"rllvm does not compile {rel} yet: {r.stderr.strip()}")
    assert r.returncode == 0, f"rllvm {rel}: exit {r.returncode}: {r.stderr}"
    assert c.check_relocations(out, e.profile, c.asm_symbols(e.path)) == []
    return out


# --- the oracle: the corpus is sound with clang alone ----------------------

@pytest.mark.parametrize("rel", [e.rel for e in c.entries()])
def test_oracle_compiles_entry(build, rel):
    assert build.clang(rel).stat().st_size > 0


@pytest.mark.parametrize("rel", [e.rel for e in c.entries()])
def test_oracle_relocations_fit_the_profile_table(build, rel):
    # The table rllvm is held to is the one clang already meets.
    e = c.entry(rel)
    assert c.check_relocations(build.clang(rel), e.profile,
                               c.asm_symbols(e.path)) == []


@pytest.mark.parametrize("name", RUNS)
def test_oracle_binary_runs(oracle_runs, name):
    result = oracle_runs[name]
    assert result.stdout, f"{name} printed nothing"
    assert result.status == RUNS[name][1]


# intrin.ll's list (andps, andpd) is rllvm's lowering, not the corpus's.
@pytest.mark.parametrize("rel", ["hosted/asm.ll", "hosted/simd.ll"])
def test_oracle_disassembly_covers_the_set(build, rel):
    assert c.missing_mnemonics(build.clang(rel), DISASSEMBLY[rel]) == []
    build.hosted([build.clang(rel)], f"{Path(rel).stem}.clang")


@pytest.mark.parametrize("rel", FREESTANDING)
def test_oracle_freestanding_links(build, rel):
    build.freestanding(rel, build.clang(rel), f"{Path(rel).stem}.clang")


def test_oracle_comdat_keeps_one_copy(build):
    binary = build.hosted([build.clang("hosted/comdat_a.ll"),
                           build.clang("hosted/comdat_b.ll")], "comdat.nm.clang")
    for name in COMDAT_FUNCTIONS:
        assert c.definitions(binary, name) == 1, name


# --- rllvm ----------------------------------------------------------------

@pytest.mark.parametrize("name", ["hello", "intrin_run", "asm_run"])
def test_rllvm_run_matches_oracle(build, oracle_runs, rllvm, tmp_path, name):
    objs = [rllvm_compile(rllvm, rel, tmp_path) for rel in RUNS[name][0]]
    assert c.run(build.hosted(objs, f"{name}.rllvm")) == oracle_runs[name]


@pytest.mark.parametrize("rel", DISASSEMBLY)
def test_rllvm_link_and_disassembly(build, rllvm, tmp_path, rel):
    obj = rllvm_compile(rllvm, rel, tmp_path)
    build.hosted([obj], f"{Path(rel).stem}.rllvm")
    assert c.missing_mnemonics(obj, DISASSEMBLY[rel]) == []
    if rel == "hosted/intrin.ll":
        refs = c.read_elf(obj).undefined()
        assert [f for f in c.FORBIDDEN_REFS
                if any(f in name for name in refs)] == []


@pytest.mark.parametrize("rllvm_side", ["abi_a", "abi_b", "both"])
def test_rllvm_abi_both_directions(build, oracle_runs, rllvm, tmp_path, rllvm_side):
    objs = [rllvm_compile(rllvm, f"hosted/{side}.ll", tmp_path)
            if rllvm_side in (side, "both") else build.clang(f"hosted/{side}.ll")
            for side in ("abi_a", "abi_b")]
    assert c.run(build.hosted(objs, f"abi.{rllvm_side}")) == oracle_runs["abi"]


@pytest.mark.parametrize("mix", ["both", "a_only", "b_only"])
def test_rllvm_comdat_links_with_one_copy(build, oracle_runs, rllvm, tmp_path, mix):
    use = {"both": ("a", "b"), "a_only": ("a",), "b_only": ("b",)}[mix]
    objs = [rllvm_compile(rllvm, f"hosted/comdat_{s}.ll", tmp_path) if s in use
            else build.clang(f"hosted/comdat_{s}.ll") for s in ("a", "b")]
    binary = build.hosted(objs, f"comdat.{mix}")
    assert c.run(binary) == oracle_runs["comdat"]
    for name in COMDAT_FUNCTIONS:
        assert c.definitions(binary, name) == 1, name


def test_rllvm_weak_shim_yields_to_strong(build, oracle_runs, rllvm, tmp_path):
    shim = rllvm_compile(rllvm, LINUX_SHIM, tmp_path)
    obj = rllvm_compile(rllvm, "hosted/weak_strong.ll", tmp_path)
    result = c.run(build.hosted([obj], "weak_strong.rllvm", shim=shim))
    assert result == oracle_runs["weak_strong"]
    assert result.status == 7


def test_rllvm_shim_runs_hello(build, oracle_runs, rllvm, tmp_path):
    shim = rllvm_compile(rllvm, LINUX_SHIM, tmp_path)
    binary = build.hosted([build.clang("hosted/hello.ll")], "hello.rllvm_shim",
                          shim=shim)
    assert c.run(binary) == oracle_runs["hello"]


@pytest.mark.parametrize("rel", FREESTANDING)
def test_rllvm_freestanding_links(build, rllvm, tmp_path, rel):
    obj = rllvm_compile(rllvm, rel, tmp_path)
    build.freestanding(rel, obj, f"{Path(rel).stem}.rllvm")


def test_rllvm_harland_shim_links_pic(build, rllvm, tmp_path):
    shim = rllvm_compile(rllvm, HARLAND_SHIM, tmp_path)
    build.freestanding("freestanding/pic.ll", build.clang("freestanding/pic.ll"),
                       "pic.rllvm_shim", shim=shim)
