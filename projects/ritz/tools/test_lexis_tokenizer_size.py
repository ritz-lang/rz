"""AGAST #3937: lexis's HTML tokenizer is one fn per state, dispatched by a
`match` over `enum State`, and no fn in it is over 150 SLOC / CC 80
(measured by ritz-metrics).

tokenizer_next was a 510 SLOC, CC 173 if-chain over 80 `STATE_*` i32 consts.
This keeps the next state from being bolted back onto one giant fn.
"""

import functools
import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
METRICS_PY = REPO / "projects" / "larb" / "tools" / "ritz-metrics" / "ritz_metrics.py"
TOKENIZER = REPO / "projects" / "lexis" / "lib" / "html" / "tokenizer.ritz"

MAX_SLOC = 150
MAX_CC = 80


@functools.cache
def _metrics():
    spec = importlib.util.spec_from_file_location("ritz_metrics_for_lexis", METRICS_PY)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod      # its dataclasses look their module up
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_no_tokenizer_function_over_the_limit():
    lines = TOKENIZER.read_text().splitlines()
    fns = _metrics().extract_functions(TOKENIZER, lines, "ritz")
    found = [f"{f.name} (line {f.line}): {f.sloc} SLOC, CC {f.complexity}"
             for f in fns if f.sloc > MAX_SLOC or f.complexity > MAX_CC]
    assert not found, (f"over {MAX_SLOC} SLOC / CC {MAX_CC}; split it:\n  "
                       + "\n  ".join(found))


@pytest.mark.unit
def test_state_is_an_enum_not_i32_consts():
    src = TOKENIZER.read_text()
    assert re.search(r"^pub enum State$", src, re.M), "no `pub enum State`"
    assert not re.search(r"\bSTATE_[A-Z_]+\b", src), "STATE_* i32 consts remain"
    assert not re.search(r"\bt\.state ==", src), "state compared in an if-chain"
