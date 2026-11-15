"""AGAST #1659: ritz1/Makefile must rebuild importers when an import changes.

`$(BUILD_DIR)/%.ll: $(SRC_DIR)/%.ritz` used to depend only on the module's own
source.  Change a struct in emitter_core.ritz and every module that imports it
kept its old .o with the old field offsets; ritz1 linked and was silently
miscompiled (#1497: 30 bogus ritz0-unit failures after a rebase).

These tests drive the *real* ritz1/Makefile against a scratch copy of ritz1/,
ritzlib/ and runtime/, with RITZ0 overridden by a fake that records which
sources it compiled and writes trivial IR.  So they check Make's dependency
graph, not the compiler, and run in seconds.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent  # projects/ritz
IMPORT_RE = re.compile(r"^\s*(?:pub\s+)?import\s+([A-Za-z_][\w.]*)", re.M)

FAKE_RITZ0 = textwrap.dedent(
    """\
    import sys
    from pathlib import Path
    args = sys.argv[1:]
    src = Path(args[0])
    out = Path(args[args.index("-o") + 1])
    with open(Path(__file__).with_name("compiled.log"), "a") as f:
        f.write(src.name if src.parent.name == "src" else "ritzlib/" + src.name)
        f.write("\\n")
    ir = "; fake\\n"
    if src.name == "main.ritz":
        ir += "define i32 @main(i32 %a, ptr %b, ptr %c) {\\n  ret i32 0\\n}\\n"
    out.write_text(ir)
    """
)

# ritzlib objects come from `cas.py get-or-build` (AGAST #1894), which always
# runs the real ritz0; this stands in for it the way FAKE_RITZ0 stands in for
# ritz0: record the source, emit a trivial object.
FAKE_CAS_OBJ = textwrap.dedent(
    """\
    import subprocess, sys
    from pathlib import Path
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    with open(Path(__file__).with_name("compiled.log"), "a") as f:
        f.write("ritzlib/" + src.name + "\\n")
    ll = out.with_suffix(".ll")
    ll.write_text("; fake\\n")
    subprocess.run(["clang", "-c", str(ll), "-o", str(out)], check=True)
    """
)

pytestmark = pytest.mark.skipif(
    not (shutil.which("make") and shutil.which("clang") and shutil.which("ld")),
    reason="needs make, clang and ld",
)


def _copy_sources(src: Path, dst: Path) -> None:
    """Copy the ritz1/, ritzlib/ and runtime/ sources of `src` into `dst`."""
    shutil.copytree(
        src / "ritz1",
        dst / "ritz1",
        ignore=shutil.ignore_patterns("build", "__pycache__"),
        # Copy links as links (AGAST #2241): a dangling build.py convenience
        # link would otherwise raise shutil.Error. Tracked links are relative
        # into ritzlib/, so they resolve inside the scratch copy.
        symlinks=True,
    )
    shutil.copytree(
        src / "ritzlib",
        dst / "ritzlib",
        ignore=shutil.ignore_patterns("*.o", "*.ll", "__pycache__"),
        symlinks=True,
    )
    (dst / "runtime").mkdir()
    for f in [src / "runtime" / "Makefile", *(src / "runtime").glob("*.ll")]:
        shutil.copy(f, dst / "runtime")


@pytest.fixture(scope="module")
def built_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A scratch projects/ritz with ritz1 fully built by the fake compiler."""
    tmp_path = tmp_path_factory.mktemp("ritz") / "projects_ritz"
    tmp_path.mkdir()
    _copy_sources(ROOT, tmp_path)
    (tmp_path / "fake_ritz0.py").write_text(FAKE_RITZ0)
    (tmp_path / "fake_cas_obj.py").write_text(FAKE_CAS_OBJ)
    _make(tmp_path)
    assert (tmp_path / "ritz1" / "build" / "ritz1").exists()
    return tmp_path


@pytest.fixture
def tree(built_tree: Path, tmp_path: Path) -> Path:
    """A private copy of the built tree (copy2 keeps mtimes, so it stays built)."""
    dst = tmp_path / "projects_ritz"
    shutil.copytree(built_tree, dst, symlinks=True)
    return dst


def _make(tree: Path) -> list[str]:
    """Run `make -C ritz1 ritz1`; return the sources ritz0 compiled."""
    log = tree / "compiled.log"
    log.unlink(missing_ok=True)
    proc = subprocess.run(
        [
            "make",
            "-C",
            str(tree / "ritz1"),
            "ritz1",
            f"RITZ0={sys.executable} {tree / 'fake_ritz0.py'}",
            f"CAS_OBJ={sys.executable} {tree / 'fake_cas_obj.py'}",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return sorted(log.read_text().split()) if log.exists() else []


def _edit_struct(path: Path) -> None:
    """Change only a struct definition (add a field), and make it newer."""
    text = path.read_text()
    m = re.search(r"^(pub\s+)?struct\s+\w+[^\n]*\n", text, re.M)
    assert m, f"no struct in {path}"
    path.write_text(text[: m.end()] + "    zz_added_by_test: i64\n" + text[m.end() :])
    future = time.time() + 5
    os.utime(path, (future, future))


def _importers(tree: Path, module: str) -> set[str]:
    """ritz1 sources that import `module` directly or transitively."""
    srcs = {
        p.stem: IMPORT_RE.findall(p.read_text())
        for p in (tree / "ritz1" / "src").glob("*.ritz")
    }
    hit = {module}
    changed = True
    while changed:
        changed = False
        for name, imports in srcs.items():
            if name not in hit and any(i in hit for i in imports):
                hit.add(name)
                changed = True
    return {f"{n}.ritz" for n in hit if n != module}


@pytest.mark.integration
def test_noop_rebuild_compiles_nothing(tree: Path) -> None:
    assert _make(tree) == []


@pytest.mark.integration
def test_struct_change_rebuilds_every_importer(tree: Path) -> None:
    _edit_struct(tree / "ritz1" / "src" / "ast.ritz")
    compiled = set(_make(tree))
    expected = _importers(tree, "ast") | {"ast.ritz"}
    assert len(expected) > 10  # ast is imported nearly everywhere
    missing = expected - compiled
    assert not missing, f"stale objects would be linked: {sorted(missing)}"
    # Precise, not "rebuild the world": a leaf nobody needs stays put.
    assert "tokens_gen.ritz" not in compiled
    assert not any(c.startswith("ritzlib/") for c in compiled)


@pytest.mark.integration
def test_transitive_import_change_rebuilds(tree: Path) -> None:
    # main does not import emitter_core directly, only via emitter.
    main_imports = IMPORT_RE.findall((tree / "ritz1/src/main.ritz").read_text())
    assert "emitter_core" not in main_imports and "emitter" in main_imports
    _edit_struct(tree / "ritz1" / "src" / "emitter_core.ritz")
    assert "main.ritz" in set(_make(tree))


@pytest.mark.integration
def test_ritzlib_struct_change_rebuilds_importers(tree: Path) -> None:
    _edit_struct(tree / "ritzlib" / "gvec.ritz")
    compiled = set(_make(tree))
    assert "ritzlib/gvec.ritz" in compiled
    assert "main.ritz" in compiled  # main imports ritzlib.gvec


@pytest.mark.integration
def test_clean_removes_dep_files(tree: Path) -> None:
    subprocess.run(
        ["make", "-C", str(tree / "ritz1"), "clean"], check=True, capture_output=True
    )
    assert not list((tree / "ritz1" / "build").glob("*.d"))


# AGAST #2241: `build.py build --all` leaves a convenience link at
# <pkg>/<bin> -> build/debug/<bin> (ritz1/ritz1 among ~60 others). The gate
# deletes ritz1/build/ but not the ignored link, so it dangles; a copytree that
# follows links then raised shutil.Error and all five tests above ERRORed at
# setup, which read like a regression in the commit under test.
def _scratch_src(root: Path) -> Path:
    """A minimal source tree shaped like projects/ritz for `_copy_sources`."""
    src = root / "src"
    for d in ("ritz1", "ritzlib", "runtime"):
        (src / d).mkdir(parents=True)
    (src / "runtime" / "Makefile").write_text("")
    (src / "ritzlib" / "io.ritz").write_text("")
    return src


@pytest.mark.unit
@pytest.mark.parametrize("pkg", ["ritz1", "ritzlib"])
def test_copy_sources_tolerates_dangling_link(tmp_path: Path, pkg: str) -> None:
    src = _scratch_src(tmp_path)
    (src / pkg / "dangling").symlink_to("build/debug/dangling")
    _copy_sources(src, tmp_path / "dst")
    assert (tmp_path / "dst" / pkg / "dangling").is_symlink()


@pytest.mark.unit
def test_copy_sources_keeps_tracked_links_inside_the_copy(tmp_path: Path) -> None:
    # Tracked links (ritz1/bootstrap_ritzlib/*, bootstrap_env/ritzlib) are
    # relative into ritzlib/; copied as links they resolve in the scratch tree.
    src = _scratch_src(tmp_path)
    (src / "ritz1" / "io.ritz").symlink_to("../ritzlib/io.ritz")
    _copy_sources(src, tmp_path / "dst")
    copied = tmp_path / "dst" / "ritz1" / "io.ritz"
    assert copied.is_symlink()
    assert copied.resolve() == (tmp_path / "dst" / "ritzlib" / "io.ritz").resolve()
