#!/usr/bin/env python3
"""Packages: `ritz-package.toml`, `rz pack`, `rz install` (AGAST #4865).

docs/PACKAGES.md §1-2. A package is a library's full source tree, its
`ritz.toml`, a `ritz-package.toml` manifest (the marker, which also names
every module `pkg/<name>/<path>`: cas.file_anchor) and one `lib<name>.a`
per object profile:

    packages.py pack <pkg dir> [--profile hosted] [--version V] [-o OUT] [--compiler C]
    packages.py install <tarball | URL --sha256 H>
    packages.py install --verify <name> <version>
    packages.py uninstall <name> <version>

`rz pack`, `rz install` and `rz uninstall` run this file, as `rz cache` runs
cas.py. Installs live in `$RITZ_PACKAGES/<name>/<version>/` (packages_root):
data, not cache, so nothing here ever deletes one but `uninstall`.

The manifest reader (read_package) and the root are standard library only,
so resolve.py imports this without loading the compiler; pack and verify
import build_pipeline when they run.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib

import cas

MARKER = cas.PACKAGE_MARKER
HOSTED = "hosted"

# A name is a path component and a marker name (cas._MARKER_NAME_RE, which
# ritz1 scans for too); a version is a path component, so neither may hold
# a separator or `..`.
_NAME_RE = re.compile(r"[A-Za-z0-9_-]+")
_VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z.+_-]*")
_URL_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://")


class PackageError(Exception):
    """A package that can't be packed, installed or trusted: the message
    says which file and why."""


def packages_root() -> Path:
    """`$RITZ_PACKAGES`, else `${XDG_DATA_HOME:-~/.local/share}/ritz/packages`."""
    env = os.environ.get("RITZ_PACKAGES")
    if env:
        return Path(env)
    data = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(data) / "ritz" / "packages"


def check_name_version(name: str, version: str) -> None:
    if not _NAME_RE.fullmatch(name):
        raise PackageError(f"package name {name!r}: letters, digits, '_' and '-' only")
    if not _VERSION_RE.fullmatch(version) or ".." in version:
        raise PackageError(f"package version {version!r}: letters, digits and "
                           "'.', '+', '_', '-' only, starting with a letter or digit")


def install_dir(name: str, version: str, root: Path | None = None) -> Path:
    """Where `name` `version` is (or would be) installed."""
    check_name_version(name, version)
    return (root if root is not None else packages_root()) / name / version


# ---------------------------------------------------------------------------
# ritz-package.toml
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModuleStamp:
    """One module of an archive: its CAS key (the stamp, cas_module_key),
    its object's sha256 and the archive member holding that object."""
    key: str
    object_sha256: str
    member: str


@dataclass(frozen=True)
class ArchiveInfo:
    """One `[[archive]]`: a profile's `lib<name>.a` and how it was built.
    `compiler_fp`, `target`, `triple` and `object_flags` repeat what the keys
    cover, so a mismatch can say why without re-deriving a key."""
    profile: str
    path: str
    archive_sha256: str
    compiler: str
    compiler_fp: str
    target: str
    triple: str
    object_flags: dict
    modules: dict  # relative path -> ModuleStamp


@dataclass(frozen=True)
class PackageInfo:
    """A parsed `ritz-package.toml`. `dir` is the directory holding it."""
    dir: Path
    name: str
    version: str
    source_sha256: str
    source: dict        # relative path -> sha256, ritz.toml included
    dependencies: dict  # name -> {version, source_sha256[, prebuilt]}
    archives: tuple     # ArchiveInfo, one per profile


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def source_tree_sha256(source: dict) -> str:
    """sha256 over the sorted (relative path, sha256) of every source file."""
    h = hashlib.sha256()
    for rel in sorted(source):
        h.update(f"{rel}\0{source[rel]}\n".encode())
    return h.hexdigest()


def _fields(table, keys: dict, where: str, path: Path) -> dict:
    """`table`'s values for `keys` ({key: type}), all required, no others."""
    if not isinstance(table, dict):
        raise PackageError(f"{path}: {where} must be a table")
    extra = sorted(set(table) - set(keys))
    if extra:
        raise PackageError(f"{path}: unknown key '{extra[0]}' in {where}")
    for k, kind in keys.items():
        if not isinstance(table.get(k), kind):
            raise PackageError(f"{path}: {where} needs '{k}' ({kind.__name__})")
    return table


def _string_map(table, where: str, path: Path) -> dict:
    if not isinstance(table, dict) or not all(isinstance(v, str) for v in table.values()):
        raise PackageError(f"{path}: {where} must map names to strings")
    return dict(table)


def read_package(pkg_dir: Path) -> PackageInfo:
    """Parse `pkg_dir/ritz-package.toml`. Checks its shape, not its hashes
    (check_tree does)."""
    path = Path(pkg_dir) / MARKER
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise PackageError(f"{path}: {e.strerror}") from None
    except tomllib.TOMLDecodeError as e:
        raise PackageError(f"{path}: {e}") from None
    extra = sorted(set(data) - {"package", "source", "dependencies", "archive"})
    if extra:
        raise PackageError(f"{path}: unknown table '{extra[0]}'")
    pkg = _fields(data.get("package"), {"name": str, "version": str,
                                        "source_sha256": str}, "[package]", path)
    check_name_version(pkg["name"], pkg["version"])
    deps = data.get("dependencies", {})
    if not isinstance(deps, dict):
        raise PackageError(f"{path}: [dependencies] must be a table")
    for dep, spec in deps.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("version"), str) \
                or not isinstance(spec.get("source_sha256"), str):
            raise PackageError(f"{path}: [dependencies] {dep} needs version and source_sha256")
    archives = []
    entries = data.get("archive", [])
    if not isinstance(entries, list):
        raise PackageError(f"{path}: archive must be [[archive]]")
    for i, a in enumerate(entries):
        where = f"[[archive]] {i + 1}"
        mods = a.get("modules") if isinstance(a, dict) else None
        _fields({k: v for k, v in a.items() if k != "modules"} if isinstance(a, dict) else a,
                {"profile": str, "path": str, "archive_sha256": str, "compiler": str,
                 "compiler_fp": str, "target": str, "triple": str, "object_flags": dict},
                where, path)
        if not isinstance(mods, dict):
            raise PackageError(f"{path}: {where} needs [archive.modules]")
        stamps = {}
        for rel, m in mods.items():
            m = _fields(m, {"key": str, "object_sha256": str, "member": str},
                        f"{where} module {rel}", path)
            stamps[rel] = ModuleStamp(m["key"], m["object_sha256"], m["member"])
        archives.append(ArchiveInfo(
            a["profile"], a["path"], a["archive_sha256"], a["compiler"], a["compiler_fp"],
            a["target"], a["triple"], dict(a["object_flags"]), stamps))
    return PackageInfo(Path(pkg_dir), pkg["name"], pkg["version"], pkg["source_sha256"],
                       _string_map(data.get("source"), "[source]", path),
                       {k: dict(v) for k, v in deps.items()}, tuple(archives))


def _toml_key(k: str) -> str:
    return k if _NAME_RE.fullmatch(k) else _toml_value(k)


def _toml_value(v) -> str:
    """A TOML value. A JSON string is a TOML basic string: the escapes
    json.dumps writes (\\" \\\\ \\n \\t \\uXXXX ...) are all TOML's too."""
    import json
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, str)):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        if not v:
            return "{}"
        return "{ " + ", ".join(f"{_toml_key(k)} = {_toml_value(x)}"
                                for k, x in v.items()) + " }"
    raise TypeError(f"no TOML form for {type(v).__name__}")


def render_marker(info: PackageInfo) -> str:
    """`ritz-package.toml` for `info`. `name = "…"` is the first line of
    [package], the form cas.package_marker_name and ritz1 scan for."""
    out = ["# Written by `rz pack` (docs/PACKAGES.md §1): edit nothing.",
           "[package]",
           f"name = {_toml_value(info.name)}",
           f"version = {_toml_value(info.version)}",
           "# sha256 over the sorted (relative path, sha256) of every source file.",
           f"source_sha256 = {_toml_value(info.source_sha256)}",
           "", "[source]"]
    out += [f"{_toml_value(rel)} = {_toml_value(info.source[rel])}"
            for rel in sorted(info.source)]
    if info.dependencies:
        out += ["", "[dependencies]"]
        out += [f"{_toml_key(n)} = {_toml_value(info.dependencies[n])}"
                for n in sorted(info.dependencies)]
    for a in info.archives:
        out += ["", "[[archive]]"]
        for k in ("profile", "path", "archive_sha256", "compiler", "compiler_fp",
                  "target", "triple", "object_flags"):
            out.append(f"{k} = {_toml_value(getattr(a, k))}")
        out += ["", "[archive.modules]"]
        out += [f"{_toml_value(rel)} = "
                + _toml_value({"key": s.key, "object_sha256": s.object_sha256,
                               "member": s.member})
                for rel, s in sorted(a.modules.items())]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Archives
# ---------------------------------------------------------------------------

def archive_members(path: Path) -> dict[str, bytes]:
    """Each member of an `ar` archive (GNU or BSD names), by name. Read in
    Python, so checking an untrusted archive writes nothing."""
    data = Path(path).read_bytes()
    if not data.startswith(b"!<arch>\n"):
        raise PackageError(f"{path}: not an ar archive")
    pos, names, out = 8, b"", {}
    while pos < len(data):
        header = data[pos:pos + 60]
        if len(header) < 60 or header[58:60] != b"`\n":
            raise PackageError(f"{path}: corrupt member header at byte {pos}")
        try:
            size = int(header[48:58].decode("ascii").strip())
        except ValueError:
            raise PackageError(f"{path}: corrupt member size at byte {pos}") from None
        body = data[pos + 60:pos + 60 + size]
        if len(body) != size:
            raise PackageError(f"{path}: truncated member at byte {pos}")
        pos += 60 + size + (size & 1)
        name = header[:16].decode("ascii", "replace").rstrip()
        if name in ("/", "/SYM64/", "__.SYMDEF", "__.SYMDEF SORTED"):
            continue  # the symbol table
        if name == "//":
            names = body
            continue
        if name.startswith("#1/"):          # BSD: the name leads the body
            n = int(name[3:])
            name, body = body[:n].rstrip(b"\0").decode(), body[n:]
        elif name.startswith("/") and name[1:].isdigit():   # GNU long name
            off = int(name[1:])
            name = names[off:names.find(b"/\n", off)].decode()
        elif name.endswith("/"):
            name = name[:-1]
        if name in out:
            raise PackageError(f"{path}: two members named {name}")
        out[name] = body
    return out


def check_tree(pkg_dir: Path) -> PackageInfo:
    """The package at `pkg_dir`, after checking every hash its manifest
    records: each [source] file, source_sha256, each archive and each
    archive member's object. Every file must be one the manifest names, and
    none a link. All problems in one PackageError."""
    info = read_package(pkg_dir)
    problems = []
    listed = set(info.source) | {MARKER} | {a.path for a in info.archives}
    if "ritz.toml" not in info.source:
        problems.append("[source] does not list ritz.toml")
    present = set()
    for p in sorted(Path(pkg_dir).rglob("*")):
        rel = p.relative_to(pkg_dir).as_posix()
        if p.is_symlink():
            problems.append(f"{rel}: a link")
        elif p.is_file():
            present.add(rel)
            if rel not in listed:
                problems.append(f"{rel}: not listed in {MARKER}")
    for rel, want in sorted(info.source.items()):
        if rel not in present:
            problems.append(f"{rel}: missing")
        elif file_sha256(Path(pkg_dir) / rel) != want:
            problems.append(f"{rel}: sha256 differs from {MARKER}'s")
    if source_tree_sha256(info.source) != info.source_sha256:
        problems.append("source_sha256 does not match [source]")
    for a in info.archives:
        ar = Path(pkg_dir) / a.path
        if a.path not in present:
            problems.append(f"{a.path}: missing")
            continue
        if file_sha256(ar) != a.archive_sha256:
            problems.append(f"{a.path}: sha256 differs from archive_sha256")
            continue
        members = archive_members(ar)
        for rel, stamp in sorted(a.modules.items()):
            body = members.get(stamp.member)
            if body is None:
                problems.append(f"{a.path}: no member {stamp.member} ({rel})")
            elif hashlib.sha256(body).hexdigest() != stamp.object_sha256:
                problems.append(f"{a.path}: member {stamp.member} ({rel}): "
                                "sha256 differs from object_sha256")
    if problems:
        raise PackageError(f"{pkg_dir}: " + "; ".join(problems))
    return info


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------

def _git(pkg_dir: Path, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(pkg_dir), *args],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def default_version(pkg_dir: Path, config: dict, tree_sha256: str) -> str:
    """The ritz.toml version, plus `+g<12 hex of HEAD>` in a checkout, so two
    packs of different commits never share a version; a tree with
    uncommitted changes adds `.dirty<8 hex of its source_sha256>`, so two of
    different edits don't either."""
    base = config.get("package", {}).get("version")
    if not base:
        raise PackageError(f"{pkg_dir}/ritz.toml: [package] has no version: pass --version")
    head = _git(pkg_dir, "rev-parse", "HEAD")
    if head is None:
        return base
    version = f"{base}{'.' if '+' in base else '+'}g{head.strip()[:12]}"
    if _git(pkg_dir, "status", "--porcelain", "--", "."):
        version += f".dirty{tree_sha256[:8]}"
    return version


def packed_dependencies(config: dict, pkg_dir: Path, name: str) -> dict:
    """The staged ritz.toml's [dependencies]: each as an installed package's
    name, version and source_sha256 (and `prebuilt`, when it says false).
    A path dependency must be a package (holds ritz-package.toml) or pack
    refuses, naming them all; the self-reference (`{ path = "." }`) goes,
    the marker's identity rule covers it."""
    out, loose = {}, []
    pkg_dir = Path(pkg_dir).resolve()
    for dep, spec in config.get("dependencies", {}).items():
        if isinstance(spec, str):
            spec = {"path": spec}
        if "version" in spec:
            where = install_dir(dep, spec["version"])
        else:
            where = (pkg_dir / spec["path"]).resolve()
            if where == pkg_dir:
                continue
        if not (where / MARKER).is_file():
            loose.append(f"{dep} ({where})")
            continue
        info = read_package(where)
        if info.name != dep:
            raise PackageError(f"dependency '{dep}' is the package '{info.name}': "
                               "name it by its package name")
        entry = {"version": info.version, "source_sha256": info.source_sha256}
        if spec.get("prebuilt") is False:
            entry["prebuilt"] = False
        out[dep] = entry
    if loose:
        raise PackageError(f"pack {name}: dependencies not packed: {', '.join(loose)}. "
                           "Pack and install each, or name a packed tree")
    return out


def staged_manifest_text(text: str, config: dict, deps: dict) -> str:
    """`text` (the package's ritz.toml) with its [dependencies] table
    replaced by `deps`. Everything else, comments included, is kept byte for
    byte; the result is re-parsed and must equal `config` with only that
    table changed, so a form this can't edit (a dotted or inline
    `dependencies`) is refused rather than shipped wrong."""
    if not config.get("dependencies") and not deps:
        return text
    kept, skipping = [], False
    for line in text.split("\n"):
        head = line.strip()
        if head.startswith("[") and not head.startswith("[["):
            name = head[1:head.index("]")].strip() if "]" in head else ""
            skipping = name == "dependencies" or name.startswith("dependencies.")
        elif head.startswith("[["):
            skipping = False
        if not skipping:
            kept.append(line)
    new = "\n".join(kept).rstrip("\n") + "\n"
    if deps:
        new += ("\n# Rewritten by `rz pack`: each dependency is a package, by version.\n"
                "[dependencies]\n")
        new += "".join(f"{_toml_key(n)} = {_toml_value(deps[n])}\n" for n in sorted(deps))
    want = {k: v for k, v in config.items() if k != "dependencies"}
    if deps:
        want["dependencies"] = deps
    if tomllib.loads(new) != want:
        raise PackageError("can't rewrite ritz.toml's dependencies: write them as "
                           "one [dependencies] table")
    return new


def _the_library(pkg_dir: Path, config: dict):
    import manifest
    libs = manifest.plan_binaries(pkg_dir, config).libraries
    if len(libs) != 1:
        raise PackageError(f"{pkg_dir}: a package is one [[lib]]; "
                           f"ritz.toml has {len(libs)}")
    return libs[0]


def _module_set(pkg_dir: Path, lib) -> list[str]:
    rels = []
    for m in lib.modules:
        try:
            rels.append(Path(m).resolve().relative_to(pkg_dir).as_posix())
        except ValueError:
            raise PackageError(f"lib{lib.name}: {m} is outside {pkg_dir}") from None
    return sorted(rels)


def host_triple() -> str:
    r = subprocess.run(["clang", "-dumpmachine"], capture_output=True, text=True,
                       timeout=60)
    return r.stdout.strip() if r.returncode == 0 else ""


def build_archive(pkg_dir: Path, profile: str, compiler: str, out_dir: Path,
                  namespaces: dict | None = None) -> tuple[ArchiveInfo, Path]:
    """Compile the package at `pkg_dir` (staged or installed) through the
    CAS into `out_dir/lib<name>.a`: its ArchiveInfo and the archive.
    `namespaces` overrides the import namespaces its ritz.toml declares."""
    if profile != HOSTED:
        raise PackageError(f"profile {profile!r}: only {HOSTED!r} archives are "
                           "built so far (freestanding profiles: docs/PACKAGES.md slice 5)")
    import build_pipeline as bp
    import manifest
    from resolve import package_import_namespaces, package_sources
    config = manifest.load(pkg_dir / "ritz.toml")
    lib = _the_library(pkg_dir, config)
    if namespaces is None:
        namespaces = package_import_namespaces(config, pkg_dir)
    members: dict = {}
    archive = bp.compile_library(lib, out_dir, dependencies=namespaces, pkg_dir=pkg_dir,
                                 source_roots=package_sources(config), compiler=compiler,
                                 members=members)
    if archive is None:
        raise PackageError(f"lib{lib.name} did not build (the compiler's errors are above)")
    stamps = {Path(m).resolve().relative_to(pkg_dir).as_posix():
              ModuleStamp(s["key"], s["object_sha256"], s["member"])
              for m, s in members.items()}
    info = ArchiveInfo(
        profile=profile, path=f"lib/{profile}/{archive.name}",
        archive_sha256=file_sha256(archive), compiler=compiler,
        compiler_fp=bp.get_build_cache(compiler)._get_current_compiler_hash(),
        target=cas.target_id(), triple=host_triple(), object_flags={},
        modules=stamps)
    return info, archive


def write_tarball(stage: Path, out: Path) -> None:
    """`stage` as `<stage name>/…` in a gzip tarball: sorted, owner 0, mtime
    0, 0644/0755, so packing one tree twice gives one tarball."""
    out = Path(out)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "wb") as raw, \
                gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, \
                tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for p in [stage, *sorted(stage.rglob("*"))]:
                arc = Path(stage.name) / p.relative_to(stage)
                ti = tf.gettarinfo(str(p), arc.as_posix())
                ti.uid = ti.gid = 0
                ti.uname = ti.gname = ""
                ti.mtime = 0
                ti.mode = 0o755 if p.is_dir() else 0o644
                if p.is_file():
                    with open(p, "rb") as f:
                        tf.addfile(ti, f)
                else:
                    tf.addfile(ti)
        os.replace(tmp, out)
    finally:
        tmp.unlink(missing_ok=True)


def pack(pkg_dir: Path, *, profiles=(HOSTED,), version: str | None = None,
         out: Path | None = None, compiler: str = "ritz0") -> Path:
    """Pack the package at `pkg_dir` into a tarball; its path.

    The [[lib]] module set and ritz.toml (dependencies rewritten:
    packed_dependencies) are copied into a staging directory with the
    marker, and every archive is built from that staged tree, so its
    modules are keyed and named `pkg/<name>/…` exactly as in any install.
    """
    import manifest
    from resolve import DependencySpec, package_import_namespaces, package_sources
    pkg_dir = Path(pkg_dir).resolve()
    config = manifest.load(pkg_dir / "ritz.toml")
    name = config["package"]["name"]
    rels = _module_set(pkg_dir, _the_library(pkg_dir, config))
    deps = packed_dependencies(config, pkg_dir, name)
    profiles = list(dict.fromkeys(profiles or [HOSTED]))
    work = Path(tempfile.mkdtemp(prefix=f"ritz-pack-{name}-"))
    try:
        stage = work / "stage"
        for rel in rels:
            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pkg_dir / rel, stage / rel)
        staged_text = staged_manifest_text(
            (pkg_dir / "ritz.toml").read_text(encoding="utf-8"), config, deps)
        (stage / "ritz.toml").write_text(staged_text, encoding="utf-8")
        source = {rel: file_sha256(stage / rel) for rel in [*rels, "ritz.toml"]}
        tree = source_tree_sha256(source)
        version = version or default_version(pkg_dir, config, tree)
        check_name_version(name, version)
        info = PackageInfo(stage, name, version, tree, source, deps, ())
        # The marker before any compile: it is what names the staged modules.
        (stage / MARKER).write_text(render_marker(info), encoding="utf-8")
        staged_config = manifest.load(stage / "ritz.toml")
        if _module_set(stage, _the_library(stage, staged_config)) != rels:
            raise PackageError(f"{name}: the staged tree's [[lib]] is not the package's")
        # Compile against the dependencies as the package names them (a
        # packed path dependency need not be installed), and the package's
        # own name against the staged tree, never the original.
        namespaces = {n: s for n, s in package_import_namespaces(config, pkg_dir).items()
                      if s.path != pkg_dir and n != name}
        namespaces[name] = DependencySpec(name=name, path=stage,
                                          sources=package_sources(staged_config, ["src"]))
        archives = []
        for profile in profiles:
            built = work / "out" / profile
            built.mkdir(parents=True)
            arc, archive = build_archive(stage, profile, compiler, built, namespaces)
            (stage / arc.path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(archive, stage / arc.path)
            archives.append(arc)
        info = PackageInfo(stage, name, version, tree, source, deps, tuple(archives))
        (stage / MARKER).write_text(render_marker(info), encoding="utf-8")
        final = work / f"{name}-{version}"
        stage.rename(final)
        out = Path(out) if out else Path.cwd() / f"{name}-{version}.tar.gz"
        write_tarball(final, out)
        return out
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# install / verify / uninstall
# ---------------------------------------------------------------------------

def install(src: str, *, sha256: str | None = None, root: Path | None = None) -> Path:
    """Install a packed tarball (a file, or a URL with its `sha256`); the
    install directory. Extracted with tarfile's `data` filter into a temp
    dir under the root, checked (check_tree), then renamed into place. The
    same version with other sources is an error; with the same sources and
    other archives (another compiler's pack), the new tree replaces it."""
    root = Path(root) if root is not None else packages_root()
    is_url = bool(_URL_RE.match(src))
    if is_url and not sha256:
        raise PackageError(f"{src}: a URL needs --sha256 <the tarball's sha256>")
    root.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".install-", dir=root))
    try:
        if is_url:
            tarball = tmp / "download"
            with urllib.request.urlopen(src, timeout=300) as r, open(tarball, "wb") as f:
                shutil.copyfileobj(r, f)
        else:
            tarball = Path(src)
        if sha256:
            got = file_sha256(tarball)
            if got != sha256.lower():
                raise PackageError(f"{src}: sha256 is {got}, not {sha256}")
        tree = tmp / "tree"
        tree.mkdir()
        try:
            with tarfile.open(tarball, "r:*") as tf:
                # Stricter than the `data` filter, which strips a leading `/`
                # and allows links inside the tree: a package is regular
                # files and directories, named below its top directory.
                for m in tf.getmembers():
                    if m.name.startswith("/") or ".." in PurePosixPath(m.name).parts:
                        raise PackageError(f"{src}: member {m.name!r} leaves the package")
                    if not (m.isfile() or m.isdir()):
                        raise PackageError(f"{src}: member {m.name!r} is not a file "
                                           "or directory")
                tf.extractall(tree, filter="data")
        except (tarfile.TarError, OSError) as e:
            raise PackageError(f"{src}: {e}") from None
        tops = list(tree.iterdir())
        if len(tops) != 1 or tops[0].is_symlink() or not tops[0].is_dir():
            raise PackageError(f"{src}: a package tarball holds one top-level directory")
        info = check_tree(tops[0])
        dest = install_dir(info.name, info.version, root)
        if dest.exists():
            old = read_package(dest)
            if old.source_sha256 != info.source_sha256:
                raise PackageError(
                    f"{info.name} {info.version} is already installed with other sources "
                    f"(source_sha256 {old.source_sha256[:12]}, this is "
                    f"{info.source_sha256[:12]}): uninstall it first")
            if (dest / MARKER).read_bytes() == (tops[0] / MARKER).read_bytes():
                print(f"{info.name} {info.version} already installed at {dest}")
                return dest
            os.replace(dest, tmp / "replaced")
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tops[0], dest)
        print(f"installed {info.name} {info.version} at {dest}")
        return dest
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def verify(name: str, version: str, *, root: Path | None = None) -> PackageInfo:
    """`install --verify`: check_tree, then rebuild every archive from the
    shipped source through the CAS and compare. Each module's key must be
    the stamp pack recorded (so this install names its modules as pack's
    staging tree did), and its rebuilt object must be the archive member's
    bytes: `clang -c` of identical IR is deterministic, so a difference means
    the archive was not built from this source."""
    import build_pipeline as bp
    d = install_dir(name, version, root)
    if not (d / MARKER).is_file():
        raise PackageError(f"{name} {version} is not installed (under {d.parent.parent})")
    info = check_tree(d)
    problems = []
    for arc in info.archives:
        fp = bp.get_build_cache(arc.compiler)._get_current_compiler_hash()
        if fp != arc.compiler_fp:
            problems.append(f"{arc.path}: built by {arc.compiler} {arc.compiler_fp[:12]}, "
                            f"this {arc.compiler} is {fp[:12]}: verify it with that compiler")
            continue
        if arc.target != cas.target_id():
            problems.append(f"{arc.path}: built for {arc.target}, this is {cas.target_id()}")
            continue
        members = archive_members(d / arc.path)
        with tempfile.TemporaryDirectory(prefix="ritz-verify-") as out:
            rebuilt, _ = build_archive(d, arc.profile, arc.compiler, Path(out))
        for rel in sorted(set(arc.modules) | set(rebuilt.modules)):
            want, now = arc.modules.get(rel), rebuilt.modules.get(rel)
            if want is None or now is None:
                problems.append(f"{arc.path}: {rel} is "
                                + ("not in the archive" if want is None
                                   else "not a module of the shipped [[lib]]"))
            elif now.key != want.key:
                problems.append(f"{arc.path}: {rel}: CAS key {now.key[:12]} is not the "
                                f"recorded {want.key[:12]}")
            elif now.object_sha256 != hashlib.sha256(members[want.member]).hexdigest():
                problems.append(f"{arc.path}: {rel}: member {want.member} differs from "
                                "a rebuild of the shipped source")
    if problems:
        raise PackageError(f"{d}: " + "; ".join(problems))
    return info


def uninstall(name: str, version: str, *, root: Path | None = None) -> None:
    d = install_dir(name, version, root)
    if not d.is_dir():
        raise PackageError(f"{name} {version} is not installed (under {d.parent.parent})")
    # Renamed away first, so the version vanishes at once, never half-deleted.
    aside = Path(tempfile.mkdtemp(prefix=".uninstall-", dir=d.parent.parent))
    try:
        os.replace(d, aside / "tree")
    finally:
        shutil.rmtree(aside, ignore_errors=True)
    try:
        d.parent.rmdir()
    except OSError:
        pass  # other versions remain


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="command", required=True)
    pk = sub.add_parser("pack", help="Pack a package directory into a tarball")
    pk.add_argument("pkg_dir")
    pk.add_argument("--profile", action="append", choices=[HOSTED],
                    help="object profile to archive (default: hosted)")
    pk.add_argument("--version", help="default: ritz.toml's, +g<HEAD> in a checkout")
    pk.add_argument("-o", "--output", help="default: ./<name>-<version>.tar.gz")
    pk.add_argument("--compiler", choices=["ritz0", "ritz1", "ritz1_selfhosted"],
                    default="ritz0")
    ins = sub.add_parser("install", help="Install a tarball, or --verify an install")
    ins.add_argument("args", nargs="+", metavar="TARBALL | NAME VERSION")
    ins.add_argument("--sha256", help="the tarball's sha256 (required for a URL)")
    ins.add_argument("--verify", action="store_true",
                     help="rebuild NAME VERSION's archives and compare")
    un = sub.add_parser("uninstall", help="Remove an installed version")
    un.add_argument("name")
    un.add_argument("version")
    args = p.parse_args(argv)
    try:
        if args.command == "pack":
            out = pack(Path(args.pkg_dir), profiles=args.profile or [HOSTED],
                       version=args.version, out=args.output and Path(args.output),
                       compiler=args.compiler)
            print(f"packed {out} sha256 {file_sha256(out)}")
        elif args.command == "install" and args.verify:
            if len(args.args) != 2:
                p.error("install --verify takes NAME VERSION")
            info = verify(*args.args)
            print(f"verified {info.name} {info.version}: "
                  f"{sum(len(a.modules) for a in info.archives)} members match a rebuild")
        elif args.command == "install":
            if len(args.args) != 1:
                p.error("install takes one TARBALL (or --verify NAME VERSION)")
            install(args.args[0], sha256=args.sha256)
        else:
            uninstall(args.name, args.version)
            print(f"uninstalled {args.name} {args.version}")
    except PackageError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
