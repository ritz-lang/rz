#!/usr/bin/env python3
"""One list of the packages in indium's initramfs (AGAST #2759).

init's Tier-1 suite spawns binaries from several packages: indium's own,
rzsh, and prism's hello_gfx.  `make -C projects/indium run-uefi` packed
indium's build/debug only, so hello_gfx was missing and the suite reported
"hello_gfx ... FAIL (spawn error)", while harland/tools/test_tier1_boot.sh,
which kept its own USER_PKGS list, passed.

The package list now lives in projects/indium/initramfs.pkgs, and
projects/indium/tools/stage_initramfs.sh is its one reader (AGAST #4834): an
entry may pin `compiler=ritz1_selfhosted` (built in the builder image) and
name `bin=SRC[:DEST]` ELFs.  These tests pin it:

  * every /bin/NAME that init.ritz spawns is a [[bin]] of a listed package;
  * every consumer (indium's Makefile and tools/mkiso.sh, harland's boot
    scripts, buddhafinger's console test) stages through the stager and
    keeps no list or `rz build` of its own;
  * Buddhafinger's entry selects ritz1_selfhosted and stages its Harland
    ELF, and only it, as /bin/buddhafinger;
  * the stager builds a pinned entry in the builder image (never `rz build`),
    stages only its named ELF, and refuses a manifest naming another
    compiler;
  * `make -n build/initramfs.tar` stages through it and packs the staged
    directory.

Run with:
    python3 -m pytest projects/ritz/tools/test_indium_initramfs_pkgs.py -q
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
PROJECTS = REPO / "projects"
INDIUM = PROJECTS / "indium"
PKGS_FILE = INDIUM / "initramfs.pkgs"
STAGER = INDIUM / "tools" / "stage_initramfs.sh"
HARLAND_TOOLS = PROJECTS / "harland" / "tools"
CONSUMERS = (
    INDIUM / "Makefile",
    INDIUM / "tools" / "mkiso.sh",
    *(
        HARLAND_TOOLS / name
        for name in (
            "test_tier1_boot.sh", "test_shell_boot.sh", "test_fbcon_boot.sh",
            "test_ps2_boot.sh", "test_usb_boot.sh", "test_msix_boot.sh",
            "test_esp_initramfs_boot.sh", "net_latency.sh",
        )
    ),
    PROJECTS / "buddhafinger" / "tools" / "test_harland_console.sh",
)


def read_entries() -> list[list[str]]:
    """initramfs.pkgs' entries: `pkg field...` per line, `#` starts a comment."""
    return [
        line.split("#", 1)[0].split()
        for line in PKGS_FILE.read_text().splitlines()
        if line.split("#", 1)[0].split()
    ]


def read_pkgs() -> list[str]:
    """The package names, in order."""
    return [e[0] for e in read_entries()]


def entry_fields(pkg: str) -> dict[str, list[str]]:
    (entry,) = [e for e in read_entries() if e[0] == pkg]
    fields: dict[str, list[str]] = {}
    for f in entry[1:]:
        k, _, v = f.partition("=")
        fields.setdefault(k, []).append(v)
    return fields


def manifest_bins(pkg: str) -> list[dict]:
    return tomllib.loads((PROJECTS / pkg / "ritz.toml").read_text()).get("bin", [])


def package_bins(pkg: str) -> set[str]:
    """The /bin names a package installs: its bin= DESTs, else every [[bin]]."""
    named = entry_fields(pkg).get("bin")
    if named:
        return {b.partition(":")[2] or b for b in named}
    return {b["name"] for b in manifest_bins(pkg)}


def test_pkgs_file_lists_real_packages():
    pkgs = read_pkgs()
    assert pkgs, f"{PKGS_FILE} lists no packages"
    assert len(pkgs) == len(set(pkgs)), f"duplicate package in {PKGS_FILE}: {pkgs}"
    for pkg in pkgs:
        assert (PROJECTS / pkg / "ritz.toml").is_file(), (
            f"{pkg}: no projects/{pkg}/ritz.toml"
        )


def test_every_binary_init_spawns_is_packed():
    """The #2759 bug: init spawns /bin/hello_gfx, which only prism builds."""
    spawned = set(
        re.findall(
            r'"/bin/([A-Za-z0-9_.]+)"', (INDIUM / "user" / "init.ritz").read_text()
        )
    )
    assert "hello_gfx" in spawned and "rzsh" in spawned, spawned
    packed: set[str] = set()
    for pkg in read_pkgs():
        packed |= package_bins(pkg)
    missing = sorted(spawned - packed)
    assert not missing, (
        f"init.ritz spawns {missing}, built by no package in {PKGS_FILE.name}"
    )


def _code(path: Path) -> str:
    """Code only: a comment naming initramfs.pkgs is not a read of it."""
    return "\n".join(
        ln for ln in path.read_text().splitlines() if not ln.lstrip().startswith("#")
    )


@pytest.mark.parametrize("consumer", CONSUMERS, ids=lambda p: p.name)
def test_consumers_stage_through_the_stager(consumer: Path):
    code = _code(consumer)
    assert "stage_initramfs.sh" in code, f"{consumer} does not use the stager"
    # The stager is initramfs.pkgs' one reader: no consumer parses it, keeps
    # a USER_PKGS list, loops over package names or builds a listed package
    # by hand other than its own (indium's `userspace`; harland's scripts
    # build harland, the kernel, which is no initramfs package).
    assert not re.search(r"\bsed\b[^\n]*initramfs\.pkgs", code), (
        f"{consumer} reads initramfs.pkgs itself"
    )
    assert "USER_PKGS" not in code, f"{consumer} keeps its own package list"
    own = consumer.relative_to(PROJECTS).parts[0]
    for pkg in read_pkgs():
        assert not re.search(rf"\bfor[ \t]+\w+[ \t]+in[ \t]+[^;$\n]*\b{pkg}\b", code), (
            f"{consumer} loops over its own list"
        )
        if pkg == own:
            continue
        assert not re.search(rf"\brz\S*\s+build\s+{pkg}\b", code), (
            f"{consumer} builds {pkg} by hand"
        )


def test_the_stager_is_the_one_reader():
    assert re.search(r"\bsed\b[^\n]*\$PKGS_FILE", _code(STAGER))
    assert 'PKGS_FILE="$INDIUM_DIR/initramfs.pkgs"' in STAGER.read_text()


def test_buddhafinger_is_built_by_ritz1_selfhosted_and_stages_its_harland_elf():
    """AGAST #4834: the editor builds with ritz1_selfhosted only (#4813), and
    only its Harland ELFs belong in the image: the editor as /bin/buddhafinger
    and the save contract (#4835) as /bin/bf-save-contract."""
    assert "buddhafinger" in read_pkgs()
    fields = entry_fields("buddhafinger")
    assert fields.get("compiler") == ["ritz1_selfhosted"], fields
    assert fields.get("bin") == ["buddhafinger.harland:buddhafinger",
                                 "bf-save-contract.harland:bf-save-contract"], fields
    for name in ("buddhafinger.harland", "bf-save-contract.harland"):
        (harland,) = [b for b in manifest_bins("buddhafinger") if b["name"] == name]
        assert harland.get("target_os") == "harland", harland
    # The Linux editor and bench exist, and are exactly what bin= keeps out.
    linux = {b["name"] for b in manifest_bins("buddhafinger") if b.get("target_os") == "linux"}
    assert {"buddhafinger", "buddhafinger-bench"} <= linux, linux


def test_only_the_builder_image_compiler_is_pinnable():
    for entry in read_entries():
        for f in entry[1:]:
            k, _, v = f.partition("=")
            assert k in ("compiler", "bin"), f"{entry[0]}: unknown field {f!r}"
            if k == "compiler":
                assert v == "ritz1_selfhosted", f"{entry[0]}: {f}"


# --- the stager, against a fake rz and a fake builder run --------------------


def _exe(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body)
    path.chmod(0o755)


def _manifest(elf: Path, compiler: str) -> None:
    Path(f"{elf}.manifest.json").write_text(json.dumps({"compiler": compiler}))


@pytest.fixture
def stager(tmp_path):
    """A repo with the real stager, two packages (`plain`; `ed`, pinned with a
    Linux and a Harland ELF), a fake rz and a fake builder run that writes
    the image's /out as $ED_COMPILER built it."""
    root = tmp_path / "repo"
    tools = root / "projects" / "indium" / "tools"
    tools.mkdir(parents=True)
    shutil.copy(STAGER, tools / STAGER.name)
    (root / "projects" / "indium" / "initramfs.pkgs").write_text(
        "plain\n# the editor\ned  compiler=ritz1_selfhosted  bin=ed.harland:ed\n"
    )
    log = tmp_path / "calls.log"
    _exe(root / "rz", f'echo "rz $*" >> {log}\n'
         'd="$PKGS_ROOT/$2/build/debug"; mkdir -p "$d"; echo plain > "$d/$2.elf"\n'
         'echo "{\\"compiler\\": \\"${4:-ritz0}\\"}" > "$d/$2.elf.manifest.json"\n')
    run = tmp_path / "builder-run"
    # run_builder_package.sh [--build-only] [--cache D] IMAGE PKG OUT
    _exe(run, f'echo "run $*" >> {log}\n'
         'out="${@: -1}"; d="$out/build/debug"; mkdir -p "$d"\n'
         'for n in ed ed.harland; do echo "$n" > "$d/$n.elf"\n'
         '  echo "{\\"compiler\\": \\"$ED_COMPILER\\"}" > "$d/$n.elf.manifest.json"; done\n')
    env = dict(
        os.environ,
        RZ_CLI=str(root / "rz"),
        PKGS_ROOT=str(root / "projects"),
        RZ_BUILDER_IMAGE="rz-builder:fake",
        RZ_BUILDER_RUN=str(run),
        RZ_BUILDER_CAS=str(tmp_path / "cas"),
        ED_COMPILER="ritz1_selfhosted",
    )
    env.pop("COMPILER", None)
    return {"script": tools / STAGER.name, "env": env, "log": log,
            "root": root, "bin": tmp_path / "bin"}


def _stage(s, *args, **env) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(s["script"]), *args],
        env={**s["env"], **env}, capture_output=True, text=True, timeout=60,
    )


@pytest.mark.integration
def test_stager_builds_a_pinned_entry_in_the_builder_image(stager):
    r = _stage(stager, str(stager["bin"]))
    assert r.returncode == 0, r.stdout + r.stderr
    calls = stager["log"].read_text().splitlines()
    assert calls[0] == "rz build plain", calls
    assert not [c for c in calls if c.startswith("rz") and " ed" in c], calls
    out = stager["root"] / "projects" / "ed" / "build" / "builder"
    assert calls[1] == f"run --build-only --cache {stager['env']['RZ_BUILDER_CAS']} rz-builder:fake projects/ed {out}"
    # Only the Harland ELF, as /bin/ed, with its manifest beside it.
    staged = sorted(p.name for p in stager["bin"].iterdir())
    assert staged == ["ed.elf", "ed.elf.manifest.json", "plain.elf", "plain.elf.manifest.json"]
    assert (stager["bin"] / "ed.elf").read_text() == "ed.harland\n"


@pytest.mark.integration
def test_stager_refuses_a_pinned_entry_built_by_another_compiler(stager):
    r = _stage(stager, str(stager["bin"]), ED_COMPILER="ritz0")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: ed.harland.elf was built by ritz0, not ritz1_selfhosted" in r.stdout


@pytest.mark.integration
def test_stager_check_compiler_holds_unpinned_entries_to_it(stager):
    # COMPILER=ritz1 builds `plain` with ritz1; the pinned entry keeps its own.
    r = _stage(stager, "--check-compiler", "ritz1", str(stager["bin"]), COMPILER="ritz1")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rz build plain --compiler ritz1" in stager["log"].read_text()
    # A stale ritz0 `plain` fails the check.
    r = _stage(stager, "--no-build", "--check-compiler", "ritz1", str(stager["bin"]))
    assert r.returncode == 0, r.stdout + r.stderr
    _manifest(stager["root"] / "projects/plain/build/debug/plain.elf", "ritz0")
    r = _stage(stager, "--no-build", "--check-compiler", "ritz1", str(stager["bin"]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: plain.elf was built by ritz0, not ritz1" in r.stdout


@pytest.mark.integration
def test_stager_no_build_stages_what_is_built_and_runs_nothing(stager):
    r = _stage(stager, "--no-build", str(stager["bin"]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert not stager["log"].exists()
    assert "note: plain: nothing built" in r.stdout
    assert "note: ed: ed.harland.elf not built" in r.stdout
    assert list(stager["bin"].iterdir()) == []


@pytest.mark.integration
def test_stager_build_only_stages_nothing(stager):
    r = _stage(stager, "--build-only")
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(stager["log"].read_text().splitlines()) == 2
    assert not stager["bin"].exists()


@pytest.mark.integration
def test_stager_fails_when_a_pinned_bin_is_missing(stager):
    (stager["root"] / "projects/indium/initramfs.pkgs").write_text(
        "ed  compiler=ritz1_selfhosted  bin=nope:ed\n"
    )
    r = _stage(stager, str(stager["bin"]))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL: ed built no nope.elf" in r.stdout


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")
def test_make_initramfs_stages_and_packs_the_listed_packages():
    out = subprocess.run(
        ["make", "-n", "-C", str(INDIUM), "-B", "build/initramfs.tar"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    # The packages are built and staged by the stager, once...
    stages = re.findall(r"tools/stage_initramfs\.sh (\S+)", out)
    assert stages == ["build/initramfs-bin"], out
    assert not re.search(r"\brz build\b", out), out
    # ...and the tar is packed from the staging dir, not indium's build/debug.
    pack = [
        ln for ln in out.splitlines() if "mkinitramfs.py" in ln or "--bin-dir" in ln
    ]
    assert any("build/initramfs-bin" in ln for ln in pack), out
    assert not any("build/debug" in ln for ln in pack), out
