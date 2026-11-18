"""A package's `sources` has one spelling: [package].sources (AGAST #3894).

It used to be accepted in three places (the top level, [package] and
[build]), and every reader (manifest.py, resolve.py twice,
ritz0/import_resolver.py, ritz0/test_runner.py) carried its own copy of the
"top level, then [package], then [build]" fallback chain. Now:

* the schema names `sources` under [package] only;
* a top-level or [build] `sources` fails with file:line and says where it
  goes;
* every reader asks resolve.package_sources, the one helper.
"""

from __future__ import annotations

import importlib
import re
import sys
import textwrap
from pathlib import Path

import pytest

RITZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RITZ))

import manifest  # noqa: E402
# Repo modules, loaded by name as tools/test_cas_gc_race.py does: they are
# resolved by path, not installed (tools/test_tools_requirements.py).
resolve = importlib.import_module("resolve")

pytestmark = pytest.mark.unit


# --- the schema: one key, and the old spellings fail with file:line ----------

def test_schema_names_sources_under_package_only():
    fields = manifest.PACKAGE_SCHEMA.fields
    assert "sources" in fields["package"].fields
    assert "sources" not in fields, "top-level `sources` is still in the schema"
    assert "sources" not in fields["build"].fields, "[build] sources is still in the schema"


@pytest.mark.parametrize("text,line,key", [
    # Top level: a bare key before the first table.
    ('sources = ["lib"]\n\n[package]\nname = "p"\n', 1, "sources"),
    # [build], as tome wrote it.
    ('[package]\nname = "p"\n\n[build]\n\nsources = ["lib"]\n', 6, "build.sources"),
])
def test_old_spellings_fail_with_file_line_and_say_where_it_goes(text, line, key):
    with pytest.raises(manifest.ManifestError) as ei:
        manifest.loads(text, Path("pkg") / "ritz.toml")
    e = ei.value
    assert str(e).startswith(f"{Path('pkg') / 'ritz.toml'}:{line}: "), str(e)
    assert f"'{key}'" in e.message and "[package]" in e.message, e.message


@pytest.mark.parametrize("value", ['"lib"', '["lib", "bin"]'])
def test_package_sources_is_accepted(value):
    cfg = manifest.loads(f'[package]\nname = "p"\nsources = {value}\n', Path("ritz.toml"))
    assert resolve.package_sources(cfg) in (["lib"], ["lib", "bin"])


# --- the helper ---------------------------------------------------------------

@pytest.mark.parametrize("config,default,want", [
    ({"package": {"sources": ["lib", "bin"]}}, None, ["lib", "bin"]),
    ({"package": {"sources": "lib"}}, None, ["lib"]),
    ({"package": {"name": "p"}}, None, None),
    ({"package": {"name": "p"}}, ["src"], ["src"]),
    ({}, ["src"], ["src"]),
    # The retired spellings are not read, even from an unvalidated dict.
    ({"sources": ["top"], "build": {"sources": ["b"]}}, ["src"], ["src"]),
])
def test_package_sources_helper(config, default, want):
    assert resolve.package_sources(config, default) == want


def test_package_sources_returns_a_fresh_list():
    default = ["src"]
    got = resolve.package_sources({}, default)
    got.append("x")
    assert default == ["src"]


# --- every reader shares the helper -------------------------------------------

# A package-level `sources` read: config.get("sources"),
# <x>.get("package", {}).get("sources") or <x>.get("build", {}).get("sources").
_PACKAGE_LEVEL_READ = re.compile(
    r"""(?:\bconfig|\bdep_config)\.get\(\s*["']sources["']"""
    r"""|\.get\(\s*["'](?:package|build)["']\s*,\s*\{\}\s*\)\s*\.get\(\s*["']sources["']""")

READERS = ["manifest.py", "resolve.py", "build_pipeline.py", "build_cli.py",
           "build_testrun.py", "ritz0/import_resolver.py", "ritz0/test_runner.py",
           "ritz0/list_deps.py", "ritz0/ritz0.py"]


def test_only_the_helper_reads_package_level_sources():
    hits = []
    for rel in READERS:
        for n, line in enumerate((RITZ / rel).read_text().splitlines(), 1):
            if _PACKAGE_LEVEL_READ.search(line):
                hits.append(f"{rel}:{n}: {line.strip()}")
    helper = [h for h in hits if h.startswith("resolve.py:")]
    assert len(helper) == 1, hits
    others = [h for h in hits if h not in helper]
    assert not others, "read [package].sources through resolve.package_sources:\n" + "\n".join(others)
    src = (RITZ / "resolve.py").read_text()
    body = src[src.index("def package_sources("):]
    body = body[:body.index("\ndef ", 1)]
    assert helper[0].split(": ", 1)[1] in body


def test_no_private_copies_of_the_helper():
    assert not hasattr(manifest, "package_sources"), "manifest.package_sources duplicates resolve's"
    assert "def get_sources_from_config" not in (RITZ / "ritz0/test_runner.py").read_text()


# --- the ritz0 readers honour [package].sources -------------------------------

def _pkg(root: Path, name: str, toml_tail: str) -> Path:
    d = root / name
    (d / "lib").mkdir(parents=True)
    (d / "ritz.toml").write_text(f'[package]\nname = "{name}"\n' + textwrap.dedent(toml_tail))
    return d


def test_import_resolver_ritz_path_detection_reads_package_sources(tmp_path, monkeypatch):
    sys.path.insert(0, str(RITZ / "ritz0"))
    import_resolver = importlib.import_module("import_resolver")
    _pkg(tmp_path, "dep", 'sources = ["lib"]\n')
    monkeypatch.setenv("RITZ_PATH", str(tmp_path))
    r = import_resolver.ImportResolver(use_cache=False)
    assert r.dependencies["dep"].sources == ["lib"]


def test_test_runner_reads_package_sources(tmp_path):
    sys.path.insert(0, str(RITZ / "ritz0"))
    test_runner = importlib.import_module("test_runner")
    dep = _pkg(tmp_path, "dep", 'sources = ["lib"]\n')
    me = _pkg(tmp_path, "me", f'sources = "lib"\n[dependencies]\ndep = {{ path = "{dep}" }}\n')
    deps = test_runner.parse_project_dependencies(me)
    assert deps["me"].sources == ["lib"]
    assert deps["dep"].sources == ["lib"]
    assert test_runner.project_source_roots(me) == [str(me / "lib")]
