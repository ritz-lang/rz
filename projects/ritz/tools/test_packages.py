"""Packages: `ritz-package.toml`, `rz pack`, `rz install` (AGAST #4865).

docs/PACKAGES.md §1-2 and "Slices" item 3. A package is a library's full
source tree, its `ritz.toml`, a `ritz-package.toml` manifest and one
`lib<name>.a` per object profile. `rz pack` builds it from a staged copy,
`rz install` checks every hash before it publishes the tree under
`$RITZ_PACKAGES/<name>/<version>/`, and `rz install --verify` rebuilds every
archive member from the shipped source and compares. A dependency names an
installed package as `{ version = "…" }`; a path dependency whose directory
holds `ritz-package.toml` is a package too.

The round trip packs a two-module fixture with ritz0 once (module scope) and
installs it into a fresh `$RITZ_PACKAGES` per test.
"""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
import tarfile
import textwrap
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parents[1]
REPO = RITZ.parents[1]
PACKAGES_PY = RITZ / "packages.py"
sys.path.insert(0, str(RITZ))

import manifest  # noqa: E402
import packages  # noqa: E402
import resolve  # noqa: E402


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"))
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_package(root: Path) -> Path:
    """`pk`: a [[lib]] of two modules, one calling a private fn and
    importing the other by its package name; tests/ and README.md are not
    part of the module set, so pack ships neither."""
    pkg = root / "pk"
    _write(pkg / "ritz.toml", """
        [package]
        name = "pk"
        version = "0.2.0"
        sources = [".", "!tests"]

        [[lib]]
        name = "pk"
    """)
    _write(pkg / "a.ritz", """
        import pk.sub.b

        fn helper(x: i32) -> i32
            b_one() * x

        pub fn twice(x: i32) -> i32
            helper(x) + helper(x)
    """)
    _write(pkg / "sub" / "b.ritz", """
        pub fn b_one() -> i32
            1
    """)
    _write(pkg / "tests" / "ritz.toml", '[package]\nname = "pk-tests"\n')
    _write(pkg / "README.md", "not shipped\n")
    return pkg


def _run(*argv: str, root: Path, **env: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, RITZ_PACKAGES=str(root), RITZ_PATH=str(RITZ), **env)
    return subprocess.run([sys.executable, str(PACKAGES_PY), *argv],
                          capture_output=True, text=True, env=env)


def _main(monkeypatch, capsys, root: Path, *argv: str) -> tuple[int, str, str]:
    """packages.py's CLI in this process: (exit code, stdout, stderr)."""
    monkeypatch.setenv("RITZ_PACKAGES", str(root))
    rc = packages.main(list(argv))
    out = capsys.readouterr()
    return rc, out.out, out.err


@pytest.fixture(scope="module")
def packed(tmp_path_factory) -> Path:
    """The fixture packed once, at version 0.2.0 (it is not in a checkout).
    Its users share one xdist group, so one worker compiles it."""
    work = tmp_path_factory.mktemp("pack")
    pkg = _fixture_package(work)
    out = work / "pk.tar.gz"
    r = _run("pack", str(pkg), "-o", str(out), root=work / "unused")
    assert r.returncode == 0, r.stdout + r.stderr
    return out


@pytest.fixture
def installed(packed, tmp_path) -> tuple[Path, Path]:
    """(packages root, install dir) after `install` of the packed tarball."""
    root = tmp_path / "packages"
    r = _run("install", str(packed), root=root)
    assert r.returncode == 0, r.stdout + r.stderr
    return root, root / "pk" / "0.2.0"


# --- the dependency kind: `{ version = … }`, `prebuilt`, the marker ---------

PKG = '[package]\nname = "p"\n'


@pytest.mark.unit
@pytest.mark.parametrize("deps,needle", [
    ('a = { path = "../a", version = "1.0.0" }', "exactly one of 'path', 'version'"),
    ('a = { sources = ["."] }', "exactly one of 'path', 'version'"),
    ('a = { version = "1.0.0", prebuilt = "no" }', "'dependencies.a.prebuilt' must be a bool"),
])
def test_schema_rejects_a_dependency_without_exactly_one_source(deps, needle):
    with pytest.raises(manifest.ManifestError) as ei:
        manifest.loads(PKG + "[dependencies]\n" + deps + "\n", Path("ritz.toml"))
    assert (ei.value.line, needle in ei.value.message) == (4, True), str(ei.value)


@pytest.mark.unit
def test_a_version_dependency_resolves_to_its_install(tmp_path, monkeypatch, capsys):
    root = tmp_path / "packages"
    monkeypatch.setenv("RITZ_PACKAGES", str(root))
    inst = _fake_install(root / "dep" / "1.0.0+gabc", "dep", "1.0.0+gabc")
    cfg = manifest.loads(PKG + '[dependencies]\n'
                         'dep = { version = "1.0.0+gabc", prebuilt = false }\n'
                         'gone = { version = "9.9.9" }\n'
                         'pinned = { path = "packages/dep/1.0.0+gabc", source_sha256 = "00" }\n',
                         Path("ritz.toml"))
    deps = resolve.parse_dependencies(cfg, tmp_path)
    assert set(deps) == {"dep"}
    spec = deps["dep"]
    assert (spec.path, spec.sources, spec.prebuilt) == (inst, ["src"], False)
    assert (spec.package.name, spec.package.version) == ("dep", "1.0.0+gabc")
    err = capsys.readouterr().err
    assert "'gone' 9.9.9 is not installed" in err and "rz install" in err
    assert "'pinned'" in err and "source_sha256" in err


@pytest.mark.unit
def test_a_path_dependency_holding_a_marker_is_a_package(tmp_path, monkeypatch):
    monkeypatch.setenv("RITZ_PACKAGES", str(tmp_path / "none"))
    marked = _fake_install(tmp_path / "tree" / "dep", "dep", "1.0.0")
    (tmp_path / "plain").mkdir()
    cfg = {"dependencies": {"dep": {"path": str(marked)}, "plain": {"path": "plain"}}}
    deps = resolve.parse_dependencies(cfg, tmp_path)
    assert deps["dep"].package.version == "1.0.0" and deps["dep"].prebuilt
    assert deps["plain"].package is None


@pytest.mark.unit
def test_two_versions_of_one_package_in_a_build_is_an_error(tmp_path, monkeypatch):
    root = tmp_path / "packages"
    monkeypatch.setenv("RITZ_PACKAGES", str(root))
    _fake_install(root / "lib" / "1.0.0", "lib", "1.0.0")
    _fake_install(root / "lib" / "2.0.0", "lib", "2.0.0")
    _write(tmp_path / "mid" / "ritz.toml",
           '[package]\nname = "mid"\n[dependencies]\nlib = { version = "2.0.0" }\n')
    cfg = {"package": {"name": "app"},
           "dependencies": {"lib": {"version": "1.0.0"}, "mid": {"path": "mid"}}}
    with pytest.raises(ValueError) as ei:
        resolve.get_transitive_dependencies(tmp_path, cfg)
    msg = str(ei.value)
    assert "lib" in msg and "1.0.0" in msg and "2.0.0" in msg
    assert str(tmp_path) in msg and str(tmp_path / "mid") in msg


def _fake_install(d: Path, name: str, version: str) -> Path:
    """A minimal package tree at `d`: no archives, one source file."""
    _write(d / "ritz.toml", f'[package]\nname = "{name}"\nversion = "{version}"\n')
    src = {"ritz.toml": _sha(d / "ritz.toml")}
    (d / packages.MARKER).write_text(packages.render_marker(packages.PackageInfo(
        dir=d, name=name, version=version,
        source_sha256=packages.source_tree_sha256(src), source=src,
        dependencies={}, archives=())))
    return d


# --- install's checks, no compiler ------------------------------------------

def _tarball(path: Path, members: dict[str, bytes], links: dict[str, str] = {}) -> Path:
    with tarfile.open(path, "w:gz") as tf:
        for name, data in members.items():
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
        for name, target in links.items():
            ti = tarfile.TarInfo(name)
            ti.type = tarfile.SYMTYPE
            ti.linkname = target
            tf.addfile(ti)
    return path


@pytest.mark.unit
@pytest.mark.parametrize("members,links,needle", [
    ({"../evil/ritz.toml": b"x"}, {}, "'../evil/ritz.toml' leaves the package"),
    ({"/abs/ritz.toml": b"x"}, {}, "'/abs/ritz.toml' leaves the package"),
    ({"pk/a.ritz": b"x"}, {"pk/out": "a.ritz"}, "'pk/out' is not a file or directory"),
    ({"pk/a.ritz": b"x", "other/b.ritz": b"y"}, {}, "one top-level directory"),
])
def test_install_refuses_an_unsafe_or_malformed_tarball(tmp_path, monkeypatch, capsys,
                                                        members, links, needle):
    bad = _tarball(tmp_path / "bad.tar.gz", members, links)
    rc, _, err = _main(monkeypatch, capsys, tmp_path / "packages", "install", str(bad))
    assert rc != 0 and needle in err, err
    assert not (tmp_path / "evil").exists()
    assert not any((tmp_path / "packages").glob("*/*")), "nothing published"


@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_a_url_needs_its_sha256(packed, tmp_path):
    root = tmp_path / "packages"
    r = _run("install", packed.as_uri(), root=root)
    assert r.returncode != 0 and "--sha256" in r.stderr, r.stderr
    r = _run("install", packed.as_uri(), "--sha256", "0" * 64, root=root)
    assert r.returncode != 0 and "sha256" in r.stderr and _sha(packed) in r.stderr
    r = _run("install", packed.as_uri(), "--sha256", _sha(packed), root=root)
    assert r.returncode == 0, r.stderr
    assert (root / "pk" / "0.2.0" / packages.MARKER).is_file()


@pytest.mark.unit
def test_pack_refuses_unpacked_path_dependencies(tmp_path, monkeypatch, capsys):
    pkg = _fixture_package(tmp_path)
    (tmp_path / "loose").mkdir()
    _write(tmp_path / "loose" / "ritz.toml", '[package]\nname = "loose"\n')
    with open(pkg / "ritz.toml", "a") as f:
        f.write('\n[dependencies]\nloose = { path = "../loose" }\npk = { path = "." }\n')
    rc, _, err = _main(monkeypatch, capsys, tmp_path / "p",
                       "pack", str(pkg), "-o", str(tmp_path / "x.tar.gz"))
    assert rc != 0 and "loose" in err and "not packed" in err, err
    assert "pk (" not in err, "the self-reference is dropped, not refused"
    assert not (tmp_path / "x.tar.gz").exists()


@pytest.mark.unit
def test_pack_rewrites_packed_path_dependencies_as_versions(tmp_path):
    """A path dependency that is a package becomes name, version and
    source_sha256; the self-reference goes. Comments survive."""
    dep = _fake_install(tmp_path / "tree" / "dep", "dep", "1.0.0")
    text = ('[package]\nname = "pk"  # keep me\n\n[dependencies]\n'
            f'dep = {{ path = "{dep}", prebuilt = false }}\npk = {{ path = "." }}\n')
    cfg = manifest.loads(text, Path("ritz.toml"))
    deps = packages.packed_dependencies(cfg, tmp_path, "pk")
    pin = packages.read_package(dep).source_sha256
    assert deps == {"dep": {"version": "1.0.0", "source_sha256": pin, "prebuilt": False}}
    staged = packages.staged_manifest_text(text, cfg, deps)
    assert "# keep me" in staged
    assert manifest.loads(staged, Path("ritz.toml"))["dependencies"] == deps


@pytest.mark.integration
def test_the_default_version_names_the_commit(tmp_path):
    pkg = _fixture_package(tmp_path)
    cfg = manifest.load(pkg / "ritz.toml")
    assert packages.default_version(pkg, cfg, "ab" * 32) == "0.2.0"
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(pkg)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-qm", "x"], check=True)
    head = subprocess.run([*git, "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    assert packages.default_version(pkg, cfg, "ab" * 32) == f"0.2.0+g{head[:12]}"
    (pkg / "a.ritz").write_text("edited\n")
    assert packages.default_version(pkg, cfg, "ab" * 32) == f"0.2.0+g{head[:12]}.dirtyabababab"


# --- the round trip, with ritz0 ----------------------------------------------

@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_pack_then_install_round_trips(installed):
    root, inst = installed
    info = packages.read_package(inst)
    assert (info.name, info.version) == ("pk", "0.2.0")
    assert sorted(info.source) == ["a.ritz", "ritz.toml", "sub/b.ritz"]
    shipped = sorted(p.relative_to(inst).as_posix() for p in inst.rglob("*") if p.is_file())
    assert shipped == sorted([packages.MARKER, "a.ritz", "lib/hosted/libpk.a",
                              "ritz.toml", "sub/b.ritz"])
    [arc] = info.archives
    assert (arc.profile, arc.path, arc.compiler, arc.object_flags) == (
        "hosted", "lib/hosted/libpk.a", "ritz0", {})
    assert arc.archive_sha256 == _sha(inst / arc.path)
    assert sorted(arc.modules) == ["a.ritz", "sub/b.ritz"]
    members = packages.archive_members(inst / arc.path)
    for stamp in arc.modules.values():
        assert hashlib.sha256(members[stamp.member]).hexdigest() == stamp.object_sha256
    # --verify: the keys this install computes are the ones pack recorded
    # (the identity rule, docs/PACKAGES.md §3) and a rebuild matches.
    r = _run("install", "--verify", "pk", "0.2.0", root=root)
    assert r.returncode == 0, r.stdout + r.stderr
    # A dependent names it by version.
    cfg = {"dependencies": {"pk": {"version": "0.2.0", "source_sha256": info.source_sha256}}}
    os.environ["RITZ_PACKAGES"], old = str(root), os.environ.get("RITZ_PACKAGES")
    try:
        assert resolve.parse_dependencies(cfg, root)["pk"].path == inst
    finally:
        os.environ.pop("RITZ_PACKAGES") if old is None else os.environ.update(RITZ_PACKAGES=old)


@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_verify_on_a_cold_store_compiles_the_same_objects(installed, tmp_path):
    """With no CAS entry to reuse, --verify compiles the install itself: its
    objects must be pack's to the byte, so nothing in them may name the
    directory a module sat in (ritz0's DWARF directory did: the staging
    dir's absolute path)."""
    root, _ = installed
    r = _run("install", "--verify", "pk", "0.2.0", root=root,
             RITZ_CACHE_DIR=str(tmp_path / "cas"),
             RITZ_BUILD_CACHE_DIR=str(tmp_path / "build-cache"))
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_verify_catches_a_tampered_source(installed):
    root, inst = installed
    (inst / "sub" / "b.ritz").write_text("pub fn b_one() -> i32\n    2\n")
    r = _run("install", "--verify", "pk", "0.2.0", root=root)
    assert r.returncode != 0 and "sub/b.ritz" in r.stderr and "sha256" in r.stderr, r.stderr


@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_verify_rebuilds_and_catches_a_forged_member(installed):
    """An archive whose member was replaced and whose manifest was rewritten
    to match passes every hash check; only the rebuild catches it."""
    root, inst = installed
    info = packages.read_package(inst)
    [arc] = info.archives
    stamp = arc.modules["sub/b.ritz"]
    ar = inst / arc.path
    blob = ar.read_bytes()
    old = packages.archive_members(ar)[stamp.member]
    forged = bytearray(old)
    forged[-1] ^= 0xFF
    ar.write_bytes(blob.replace(old, bytes(forged)))
    modules = dict(arc.modules)
    modules["sub/b.ritz"] = packages.ModuleStamp(
        stamp.key, hashlib.sha256(forged).hexdigest(), stamp.member)
    arc2 = packages.ArchiveInfo(**{**arc.__dict__, "archive_sha256": _sha(ar),
                                   "modules": modules})
    (inst / packages.MARKER).write_text(packages.render_marker(
        packages.PackageInfo(**{**info.__dict__, "archives": (arc2,)})))
    r = _run("install", "--verify", "pk", "0.2.0", root=root)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "sub/b.ritz" in r.stderr and "rebuild" in r.stderr, r.stderr


@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_install_checks_hashes_and_refuses_other_sources(installed, packed, tmp_path):
    root, inst = installed
    # The same tarball again: already there.
    r = _run("install", str(packed), root=root)
    assert r.returncode == 0 and "already installed" in r.stdout, r.stdout + r.stderr
    # A tree edited after pack fails install's own checks.
    work = tmp_path / "x"
    with tarfile.open(packed) as tf:
        tf.extractall(work, filter="data")
    [top] = work.iterdir()
    (top / "a.ritz").write_text("edited\n")
    edited = tmp_path / "edited.tar.gz"
    with tarfile.open(edited, "w:gz") as tf:
        tf.add(top, top.name)
    r = _run("install", str(edited), root=tmp_path / "fresh")
    assert r.returncode != 0 and "a.ritz" in r.stderr and "sha256" in r.stderr, r.stderr
    # A consistent tree of other sources under the installed version.
    (top / "a.ritz").write_text("pub fn other() -> i32\n    0\n")
    info = packages.read_package(top)
    src = dict(info.source, **{"a.ritz": _sha(top / "a.ritz")})
    (top / packages.MARKER).write_text(packages.render_marker(packages.PackageInfo(
        **{**info.__dict__, "source": src, "archives": (),
           "source_sha256": packages.source_tree_sha256(src)})))
    (top / "lib" / "hosted" / "libpk.a").unlink()
    (top / "lib" / "hosted").rmdir()
    (top / "lib").rmdir()
    with tarfile.open(edited, "w:gz") as tf:
        tf.add(top, top.name)
    r = _run("install", str(edited), root=root)
    assert r.returncode != 0 and "other sources" in r.stderr, r.stderr
    assert packages.read_package(inst).source_sha256 != packages.source_tree_sha256(src)


@pytest.mark.integration
@pytest.mark.xdist_group("packages_4865")
def test_uninstall_removes_the_version(installed):
    root, inst = installed
    r = _run("uninstall", "pk", "0.2.0", root=root)
    assert r.returncode == 0, r.stderr
    assert not inst.exists() and not (root / "pk").exists()
    r = _run("uninstall", "pk", "0.2.0", root=root)
    assert r.returncode != 0 and "not installed" in r.stderr


@pytest.mark.unit
def test_rz_pack_names_a_package_by_its_package_name():
    """`rz pack ritzlib`: no projects/ritzlib, but one workspace package is
    named ritzlib (docs/PACKAGES.md §2's CLI)."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("rz_cli_4865", str(REPO / "rz"))
    rz = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(rz)
    assert rz.resolve_package("ritzlib") == "ritz/ritzlib"
    assert rz.resolve_package("ritz/ritzlib") == "ritz/ritzlib"
    assert rz.resolve_package("no-such-package-4865") is None


@pytest.mark.unit
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_packages_py_is_in_every_compiler_fingerprint(tmp_path, compiler):
    """packages.py turns `{ version = … }` into the directory every module
    is compiled against, so an edit to it must miss the CAS, as an edit to
    resolve.py does (cache.RITZ0_DRIVER_FILES)."""
    from cache import compute_compiler_hash
    (tmp_path / "ritz0").mkdir()
    (tmp_path / "ritz0" / "ritz0.py").write_text("# x")
    (tmp_path / "ritz1" / "build").mkdir(parents=True)
    (tmp_path / "ritz1" / "build" / "ritz1").write_bytes(b"binary")
    (tmp_path / "packages.py").write_text("# v1")
    before = compute_compiler_hash(tmp_path, compiler)
    (tmp_path / "packages.py").write_text("# v2")
    assert compute_compiler_hash(tmp_path, compiler) != before
