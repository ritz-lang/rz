"""AGAST #3571: corpus files whose selective imports named modules that don't
exist, or named a directory (`import lib.style { … }`), which the resolver
never maps to the directory's mod.ritz.  Each must now resolve, the way the
build resolves it: the package's own namespaces and source roots, ritzlib
and projects/ on RITZ_PATH.

Per file:
  - spire lib/presenter, lib/form: already `spire.json.mod`,
    `spire.service.mod` (#2424); spire's [[lib]] compiles them.
  - prism src/main.ritz: already `compositor.mod` (#2195); the prism bin.
  - iris lib/layout/block.ritz: `lib.style.mod`, `lib.tree.mod`; the unused
    `prism.api { Size, Rect }` is gone, and with it `Display` and `Position`,
    which iris no longer defines (style.display is an i32 DISPLAY_*).  #4047
    ported its body; iris test/test_layout_block.ritz builds and runs it.

Resolution only: one parse of each file's import closure, no codegen.
"""

import sys
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
PROJECTS = RITZ_ROOT.parent
sys.path.insert(0, str(RITZ_ROOT))

from import_resolver import (
    DependencyMapping,
    ImportError as ResolveError,
    collect_all_source_files,
)
from resolve import package_import_namespaces, read_manifest

pytestmark = pytest.mark.unit


def _manifest(pkg: str):
    """(package dir, dependency map, source roots) for one package."""
    pkg_dir = PROJECTS / pkg
    config = read_manifest(pkg_dir)
    deps = {
        name: DependencyMapping(name=name, path=Path(spec.path), sources=spec.sources)
        for name, spec in package_import_namespaces(config, pkg_dir).items()
    }
    return pkg_dir, deps, config["package"].get("sources", ["src"])


def _closure(pkg: str, rel: str) -> list[str]:
    pkg_dir, deps, sources = _manifest(pkg)
    return collect_all_source_files(
        str(pkg_dir / rel),
        project_root=str(pkg_dir),
        dependencies=deps,
        source_roots=sources,
    )


@pytest.mark.parametrize(
    "pkg, rel, needs",
    [
        (
            "spire",
            "lib/presenter/mod.ritz",
            ["spire/lib/json/mod.ritz", "spire/lib/service/mod.ritz"],
        ),
        ("spire", "lib/form/mod.ritz", ["spire/lib/json/mod.ritz"]),
        ("prism", "src/main.ritz", ["prism/src/compositor/mod.ritz"]),
        # A prism file that imports angelo: prism's `types.*` must come from
        # prism's own tree, while angelo's internal bare `import types`
        # resolves against angelo's (#3572).
        (
            "prism",
            "src/text/renderer.ritz",
            [
                "prism/src/types/rect.ritz",
                "prism/src/types/color.ritz",
                "angelo/src/types.ritz",
            ],
        ),
        (
            "iris",
            "lib/layout/block.ritz",
            ["iris/lib/style/mod.ritz", "iris/lib/tree/mod.ritz"],
        ),
    ],
)
def test_imports_resolve_to_the_named_mod(monkeypatch, pkg, rel, needs):
    monkeypatch.setenv("RITZ_PATH", f"{RITZ_ROOT}:{PROJECTS}")
    files = [
        Path(f).resolve().relative_to(PROJECTS).as_posix() for f in _closure(pkg, rel)
    ]
    assert files[-1] == f"{pkg}/{rel}"
    for need in needs:
        assert need in files


def test_prism_bare_types_never_reaches_angelo(monkeypatch, tmp_path):
    """AGAST #3572: prism's `types` must never be angelo's font types.

    prism has its own `src/types/` package and imports angelo as `angelo.*`,
    so angelo's source root has no business in prism's `sources`.  While it
    was there, a bare `import types` resolved to `angelo/src/types.ritz`
    without a word — the resolver takes the first `types.ritz` it finds, and
    angelo's module declares none of `Point/Size/Rect/Color`.
    """
    monkeypatch.setenv("RITZ_PATH", f"{RITZ_ROOT}:{PROJECTS}")
    pkg_dir, deps, sources = _manifest("prism")
    probe = tmp_path / "probe.ritz"
    probe.write_text("import types\n")
    try:
        files = collect_all_source_files(
            str(probe),
            project_root=str(pkg_dir),
            dependencies=deps,
            source_roots=sources,
        )
    except ResolveError:
        # No bare `types` target anywhere: a loud miss, not angelo's module.
        return
    angelo_types = str((PROJECTS / "angelo/src/types.ritz").resolve())
    assert angelo_types not in [str(Path(f).resolve()) for f in files]
