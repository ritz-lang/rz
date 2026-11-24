"""AGAST #3937, #4566: no fn in lexis is over 150 SLOC / CC 80 (measured by
ritz-metrics).

#3937 split tokenizer_next (510 SLOC, CC 173, an if-chain over 80 `STATE_*`
i32 consts) into one fn per state, dispatched by a `match` over `enum State`.
#4566 took the guard lexis-wide: process_start_tag_in_body (CC 95) became a
name -> group lookup plus one fn per group, and ritz-metrics counts a pure
lookup `match` as one decision (tag_name, tag_from_name, tag_is_special).
This keeps the next feature from being bolted back onto one giant fn.
"""

import functools
import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
METRICS_PY = REPO / "projects" / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"
LEXIS = REPO / "projects" / "lexis"
TOKENIZER = LEXIS / "lib" / "html" / "tokenizer.ritz"
# Sources only: build output and fetched deps are not lexis's code.
SOURCE_DIRS = ("lib", "src", "test")

MAX_SLOC = 150
MAX_CC = 80


@functools.cache
def _metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_for_lexis", METRICS_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


def _lexis_sources():
    return sorted(p for d in SOURCE_DIRS for p in (LEXIS / d).rglob("*.ritz"))


def _over_the_limit(path):
    lines = path.read_text().splitlines()
    fns = _metrics().extract_functions(path, lines, "ritz")
    return [f"{path.relative_to(LEXIS)}: {f.name} (line {f.line}): "
            f"{f.sloc} SLOC, CC {f.complexity}"
            for f in fns if f.sloc > MAX_SLOC or f.complexity > MAX_CC]


@pytest.mark.unit
def test_the_guard_sees_all_of_lexis():
    # A path typo would make the guard below pass on nothing.
    files = {p.relative_to(LEXIS).as_posix() for p in _lexis_sources()}
    assert {"lib/html/tokenizer.ritz", "lib/html/tree_builder.ritz",
            "lib/dom/tag.ritz"} <= files, sorted(files)


@pytest.mark.unit
def test_no_lexis_function_over_the_limit():
    found = [row for p in _lexis_sources() for row in _over_the_limit(p)]
    assert not found, (f"over {MAX_SLOC} SLOC / CC {MAX_CC}; split it:\n  "
                       + "\n  ".join(found))


@pytest.mark.unit
def test_state_is_an_enum_not_i32_consts():
    src = TOKENIZER.read_text()
    assert re.search(r"^pub enum State$", src, re.M), "no `pub enum State`"
    assert not re.search(r"\bSTATE_[A-Z_]+\b", src), "STATE_* i32 consts remain"
    assert not re.search(r"\bt\.state ==", src), "state compared in an if-chain"
