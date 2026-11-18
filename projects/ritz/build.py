#!/usr/bin/env python3
"""
🎭 Ritz Build System

A simple build helper that reads ritz.toml configs and compiles examples.

Usage:
    python build.py list              # List all packages
    python build.py build <name>      # Build a specific package
    python build.py build --all       # Build all packages
    python build.py test <name>       # Build and test a package
    python build.py test --all        # Build and test all packages
    python build.py clean             # Remove build artifacts
    python build.py cache-status      # Show cache status
    python build.py cache-clear       # Clear the build cache

The entry point only (AGAST #3632). The build system lives in:

    manifest.py        ritz.toml schema, and what a package asks to build
                       ([[bin]], [[lib]], profiles: plan_binaries)
    resolve.py         [dependencies] and import namespaces (shared with rz)
    build_pipeline.py  per-module compile, links, archives, provenance,
                       build_package
    build_testrun.py   test discovery, per-file runs, rz's test units
    build_cli.py       cmd_* and main

(`build_` prefixed: a bare `cli` or `pipeline` on sys.path can be some other
installed package, as `build` itself is on PyPI.)

This module stands for all of them: `build.X` reads X from the module that
defines it, and assigning `build.X` (a test's monkeypatch) rebinds X in every
one of those modules that holds the same object, so code that calls X from
another module sees the patch, as it did when this was one file.
"""

import sys
import types
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)   # the siblings below, whoever loaded us

import manifest          # noqa: E402
import resolve           # noqa: E402

# The modules that hold build state (the clang failure count, the build
# caches, the setup misses). As one file, every load of build.py had its own;
# tools and tests load it by path to get a fresh one (cas.py, test_runner,
# per-test fixtures). So each load gets its own copies: the first is the one
# in sys.modules, a later load's are private to it. manifest.py and
# resolve.py hold no state and are shared, as before.
_OWN = ("build_pipeline", "build_testrun", "build_cli")


def _load_own():
    import importlib
    saved = {n: sys.modules.pop(n) for n in _OWN if n in sys.modules}
    try:
        return [importlib.import_module(n) for n in _OWN]
    finally:
        if saved:
            for n in _OWN:
                sys.modules.pop(n, None)
            sys.modules.update(saved)


build_pipeline, build_testrun, build_cli = _load_own()

# Lowest layer first: a name two modules share is defined by the lower one
# and imported by the other, so the first holder is its owner.
_MODULES = (manifest, resolve, build_pipeline, build_testrun, build_cli)

# The one name two of them define differently: manifest.py's `main` is the
# spec generator. build.py's is the build command line.
main = build_cli.main


def _owner(name: str):
    for mod in _MODULES:
        if name in vars(mod):
            return mod
    return None


def __getattr__(name: str):
    mod = _owner(name)
    if mod is None or name.startswith("__"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return vars(mod)[name]


def __dir__():
    names = set(globals())
    for mod in _MODULES:
        names.update(n for n in vars(mod) if not n.startswith("__"))
    return sorted(names)


class _BuildModule(types.ModuleType):
    """Forwards `build.X = v` to the modules that hold X (see the docstring)."""

    def __setattr__(self, name, value):
        mod = _owner(name)
        if mod is None or name.startswith("__") or name in vars(self):
            super().__setattr__(name, value)
            return
        current = vars(mod)[name]
        for m in _MODULES:
            if vars(m).get(name, m) is current:
                setattr(m, name, value)

    def __delattr__(self, name):
        if name in vars(self):
            super().__delattr__(name)
        else:
            raise AttributeError(name)


def _this_module() -> types.ModuleType:
    """This module's object. Tests and tools load build.py by path
    (`spec.loader.exec_module`) without registering it in sys.modules, so
    look it up by its namespace there too."""
    mod = sys.modules.get(__name__)
    if mod is not None and vars(mod) is globals():
        return mod
    import gc
    return next(m for m in gc.get_referrers(globals())
                if isinstance(m, types.ModuleType) and vars(m) is globals())


_this_module().__class__ = _BuildModule

# ritz0/test_runner.py uses the build system through one module object
# (store key, object flags); hand it this one when build_testrun loads it.
if build_testrun.BUILD_MODULE is None:
    build_testrun.BUILD_MODULE = _this_module()


if __name__ == "__main__":
    sys.exit(main() or 0)
