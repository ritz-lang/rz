"""The ritz.toml / rz.toml schema is strict, live and documented (AGAST #1837).

Before this, manifests carried keys nothing read ([build] target in 36
packages, [agents], [[test]], [scripts], ...) and RITZ_TOML_SPEC.md promised
features nothing implemented, while keys that were read went undocumented.
A misspelt key was silently ignored. Now:

* every committed manifest validates against manifest.py's schema;
* every schema key names functions that read it, and each one does: so no
  committed manifest can carry a key nothing reads;
* an unknown key fails `rz build` / `build.py` as `<file>:<line>: ...`;
* docs/RITZ_TOML_SPEC.md is generated from the schema and must be current.
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import textwrap
from functools import cache
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parents[1]
REPO = RITZ.parents[1]
sys.path.insert(0, str(RITZ))

import manifest

pytestmark = pytest.mark.unit


def _committed_manifests() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "--", "rz.toml", "*ritz.toml"],
                         cwd=REPO, capture_output=True, text=True, check=True)
    files = [REPO / f for f in out.stdout.split()
             if Path(f).name in ("ritz.toml", "rz.toml")]
    assert len(files) > 100, files  # the glob found the workspace, not nothing
    return files


def _walk(node, path: tuple[str, ...]):
    """Yield (key path, node) for every schema node with a key of its own."""
    if isinstance(node, manifest.Table):
        for k, child in node.fields.items():
            yield path + (k,), child
            yield from _walk(child, path + (k,))
        if node.self_named is not None:
            yield from _walk(node.self_named, path + ("<name>",))
    elif isinstance(node, manifest.Array):
        yield from _walk(node.item, path)
    elif isinstance(node, manifest.Map):
        yield from _walk(node.value, path + ("<key>",))


@cache
def _functions(rel: str) -> dict[str, str]:
    """Function name -> source text, for every def in a file."""
    src = (REPO / rel).read_text()
    out = {}
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(n.name, ast.get_source_segment(src, n))
    return out


# --- liveness and coverage ---------------------------------------------------

@pytest.mark.integration
def test_every_committed_manifest_validates():
    bad = []
    for f in _committed_manifests():
        try:
            manifest.load(f)
        except manifest.ManifestError as e:
            bad.append(str(e).replace(str(REPO) + "/", ""))
    assert not bad, "manifests the schema rejects:\n" + "\n".join(bad)


@pytest.mark.integration
def test_every_test_sources_dir_exists():
    """A `[test] sources` entry names a directory in its package.

    build.py skips a missing one silently (it searches each for [[test]]
    fns), so a stale entry reads as live but runs nothing: harland named
    "tests" while its tests live in test/ (AGAST #3282).
    """
    missing = []
    for f in _committed_manifests():
        test_cfg = manifest.load(f).get("test")
        if not isinstance(test_cfg, dict):
            continue
        for rel in test_cfg.get("sources", []):
            if not (f.parent / rel).is_dir():
                missing.append(f"{f.relative_to(REPO)}: [test] sources "
                               f"names '{rel}', which is not a directory")
    assert not missing, "\n".join(missing)


@pytest.mark.parametrize("name", sorted(manifest.SCHEMAS))
def test_every_schema_key_is_read_by_its_named_reader(name):
    """Each key's `read_by` functions exist and mention the key literally.

    A key whose reader stops reading it (or never did) fails here, so the
    schema can only accept keys code reads, and test above holds every
    committed manifest to the schema.
    """
    problems = []
    for path, node in _walk(manifest.SCHEMAS[name], ()):
        key = path[-1]
        readers = getattr(node, "read_by", ())
        if not readers:
            problems.append(f"{'.'.join(path)}: no read_by")
        if key.startswith("<"):
            continue  # an author-chosen key: its children are checked
        for r in readers:
            rel, fn = r.split("::")
            body = _functions(rel).get(fn)
            if body is None:
                problems.append(f"{'.'.join(path)}: {r} does not exist")
            elif f'"{key}"' not in body and f"'{key}'" not in body:
                problems.append(f"{'.'.join(path)}: {r} never reads '{key}'")
    assert not problems, "\n".join(problems)


def test_spec_is_generated_from_the_schema():
    committed = (RITZ / "docs" / "RITZ_TOML_SPEC.md").read_text()
    assert committed == manifest.render_spec(), (
        "docs/RITZ_TOML_SPEC.md has drifted from manifest.py: "
        "run `make -C projects/ritz manifest-spec`")


# --- strictness, with file:line ----------------------------------------------

def _error(text: str, name: str = "ritz.toml") -> manifest.ManifestError:
    with pytest.raises(manifest.ManifestError) as ei:
        manifest.loads(textwrap.dedent(text).lstrip("\n"), Path("pkg") / name)
    return ei.value


PKG = '[package]\nname = "p"\n'


@pytest.mark.parametrize("text,line,needle", [
    # A top-level table nothing reads.
    (PKG + '\n[scripts]\nbuild = "make"\n', 4, "unknown key 'scripts' in the top level"),
    # A misspelt key in a known table.
    (PKG + 'descripton = "x"\n', 3, "unknown key 'descripton' in [package]"),
    # The second [[bin]] entry, after a multi-line array that must not be
    # mistaken for keys.
    (PKG + '[[bin]]\nname = "a"\nsources = [\n  "x = 1",\n]\n[[bin]]\nname = "b"\nmain = "m"\n',
     10, "unknown key 'main' in [bin]"),
    # [bin.NAME.linker], keyed by the entry's own name.
    (PKG + '[[bin]]\nname = "k"\n[bin.k.linker]\nscript = "l.ld"\nsubsystem = "efi"\n',
     7, "unknown key 'subsystem' in [bin.k.linker]"),
    # Inside an inline table: reported at its key's line.
    (PKG + '[dependencies]\nfoo = { path = "../foo", srcs = ["."] }\n', 4,
     "unknown key 'srcs' in [dependencies.foo]"),
    # [[test]] is not a manifest feature (test discovery is test/ and [test]).
    (PKG + '[[test]]\nname = "t"\n', 3, "'test' must be a table"),
    # Wrong type.
    (PKG + '[build]\ntest_only = "yes"\n', 4, "'build.test_only' must be a bool"),
    # Missing required key: reported at its table.
    ('[package]\nversion = "1"\n', 1, "[package] is missing required key 'name'"),
])
def test_package_manifest_errors_name_the_line(text, line, needle):
    e = _error(text)
    assert (e.line, needle in e.message) == (line, True), str(e)
    assert str(e).startswith(f"{Path('pkg') / 'ritz.toml'}:{line}: ")


def test_workspace_manifest_is_strict_too():
    e = _error('[workspace]\nmembers = ["p"]\n\n[agents]\nlock_timeout_ms = 1\n', "rz.toml")
    assert (e.line, "unknown key 'agents'" in e.message) == (4, True), str(e)


def test_author_chosen_keys_are_free_but_their_values_are_not():
    ok = manifest.loads(PKG + '[dependencies]\nany-name = "../x"\n'
                        'other = { path = "../o" }\n', Path("ritz.toml"))
    assert set(ok["dependencies"]) == {"any-name", "other"}
    e = _error(PKG + '[dependencies.other]\npath = "../o"\nvers = "1"\n')
    assert "unknown key 'vers' in [dependencies.other]" in e.message


def test_only_the_two_selectable_profiles_are_accepted():
    # build.py selects `release` (--release) or `debug`; nothing reaches a
    # third, so [profile.bench] would be a table nothing reads.
    e = _error(PKG + '[profile.release]\nlto = true\n[profile.bench]\nlto = true\n')
    assert (e.line, "unknown key 'bench' in [profile]" in e.message) == (5, True), str(e)


def test_toml_syntax_errors_carry_the_line_too():
    e = _error(PKG + '[build\n')
    assert e.line == 3, str(e)


def test_rz_list_shows_the_identity_keys(monkeypatch, capsys):
    """[package] version and [workspace] name/version/description are read
    by `rz list` and nothing else: pin that they appear, since the
    literal-key check above cannot tell the two `"version"` reads apart."""
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("rz_cli_1837", str(REPO / "rz"))
    rz = importlib.util.module_from_spec(
        importlib.util.spec_from_loader("rz_cli_1837", loader))
    loader.exec_module(rz)
    monkeypatch.setattr(rz, "discover_projects", lambda: ["p"])
    monkeypatch.setattr(rz, "load_workspace_config", lambda: {"workspace": {
        "name": "wsname", "version": "9.8.7", "description": "wsdesc"}})
    monkeypatch.setattr(rz, "get_project_config", lambda p: {"package": {
        "name": "p", "version": "1.2.3", "description": "pdesc"}})
    assert rz.cmd_list(None) == 0
    out = capsys.readouterr().out
    assert "Workspace: wsname 9.8.7" in out and "wsdesc" in out, out
    assert "1.2.3" in out and "pdesc" in out, out


# --- `rz build` and build.py stop at a bad manifest -------------------------

@pytest.fixture
def workspace(tmp_path):
    """A workspace with `rz`, the real projects/ritz, and one package whose
    ritz.toml has an unknown key on line 4."""
    ws = tmp_path / "ws"
    (ws / "projects" / "bad").mkdir(parents=True)
    shutil.copy(REPO / "rz", ws / "rz")
    (ws / "projects" / "ritz").symlink_to(RITZ)
    (ws / "rz.toml").write_text('[workspace]\nmembers = ["projects/bad"]\n')
    (ws / "projects" / "bad" / "ritz.toml").write_text(
        '[package]\nname = "bad"\n\ncolour = "blue"\n')
    return ws


@pytest.mark.integration
@pytest.mark.parametrize("argv", [["rz", "build", "bad"],
                                  ["projects/ritz/build.py", "build", "projects/bad"]])
def test_unknown_key_fails_the_build_with_file_and_line(workspace, argv):
    env = {k: v for k, v in os.environ.items() if k != "RITZ_PATH"}
    r = subprocess.run([sys.executable, *argv], cwd=workspace, env=env,
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "ritz.toml:4: unknown key 'colour' in [package]" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr
