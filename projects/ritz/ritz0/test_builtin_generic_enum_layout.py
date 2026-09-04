#!/usr/bin/env python3
"""Synthesized Result/Option specializations must use the shared enum layout
(AGAST #1321, discovery.ritz cascade failure).

`_ensure_builtin_generic_specialization` synthesizes `Option$T` / `Result$T$E`
on demand when monomorphization missed them. It built the LLVM struct body
with its own ad-hoc sizing:

* alignment was taken from `_type_size_bytes` (i.e. align := size — wrong for
  any aggregate), and
* the payload was sized from `_ritz_type_to_llvm` at synthesis time, when the
  payload's struct may not be registered yet, so `String` lowered to the
  1-byte generic placeholder and the body became `{i8, [1 x i8]}`.

Every *consumer* — `_get_enum_data_index`, variant construction, match
binding — computes the layout at use time through the shared helpers
(`_enum_variant_field_layout` / `_ritz_type_size_and_align`), which for
`Option$String` says align 8, padded, data at index 2. GEP index 2 into a
two-element struct raises::

    IndexError: tuple index out of range

This is the shape of angelo's `discovery.ritz` `expand_path`: a `match` on an
`Option<String>`-returning call, in an `if` branch, where nothing else forced
the specialization to exist beforehand.

The fix routes the synthesizer through `_enum_variant_field_layout`, the
documented single source of truth, so synthesis and use cannot drift.
"""

import os
import subprocess
import sys
from pathlib import Path

RITZ0 = Path(__file__).resolve().parent / "ritz0.py"
RITZ_ROOT = RITZ0.parent.parent


def _compile(tmp_path, source):
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    # String lives in ritzlib; the compiler resolves it through RITZ_PATH.
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [sys.executable, str(RITZ0), str(src),
         "-o", str(tmp_path / "unit.ll")],
        capture_output=True,
        text=True,
        env=env,
    )


# The reduced discovery.ritz `expand_path` shape. The specialization
# `Option$String` is only ever demanded by `get()`'s return type, so it is
# synthesized on the fly — with the broken layout, constructing
# `Some(String...)` GEPs past the end of the synthesized struct.
MATCH_OPTION_STRING_IN_IF = """\
import ritzlib.string

fn get() -> Option<String>
    return Some(string_from("/home"))

fn expand(flag: i32) -> String
    if flag == 1
        match get()
            Some(home) => home
            None => string_from("nope")
    else
        string_from("else")

fn main() -> i32
    let s = expand(1)
    return 0
"""


def test_match_option_string_in_if_branch(tmp_path):
    """Match on a synthesized Option<String> must construct and bind."""
    result = _compile(tmp_path, MATCH_OPTION_STRING_IN_IF)
    assert result.returncode == 0, (
        "match on Option<String>-returning call in an if branch failed:\n"
        f"{result.stderr}"
    )


# Result with an aggregate payload exercises the same synthesizer arm with
# two variants of different payload sizes.
RESULT_STRING_PAYLOAD = """\
import ritzlib.string

fn get(flag: i32) -> Result<String, i32>
    if flag == 1
        return Ok(string_from("yes"))
    return Err(7)

fn main() -> i32
    match get(1)
        Ok(s) => 0
        Err(code) => code
"""


def test_result_string_payload_synthesized(tmp_path):
    """Synthesized Result<String, i32> must agree with use-time layout."""
    result = _compile(tmp_path, RESULT_STRING_PAYLOAD)
    assert result.returncode == 0, (
        "match on synthesized Result<String, i32> failed:\n"
        f"{result.stderr}"
    )


def test_synthesized_option_string_body_uses_shared_layout(tmp_path):
    """The synthesized struct body must match the shared layout helper.

    String is `{ i8*, i64, i64 }`: size 24, align 8, so the enum layout is
    tag (1) + padding to 8 (7) + payload (24). The pre-fix synthesizer
    conflated alignment with size and padded to 24 instead::

        %"Option$String" = type {i8, [23 x i8], [24 x i8]}

    That variant is self-consistent within one module (everything GEPs by
    struct index), so the compile-only tests above cannot see it — but it
    disagrees with `_enum_variant_field_layout`, the documented single source
    of truth, and with any module that computed the layout correctly. In the
    unregistered-payload case the same drift shrank the body to
    `{i8, [1 x i8]}` and crashed `discovery.ritz` with an IndexError GEP.
    """
    result = _compile(tmp_path, MATCH_OPTION_STRING_IN_IF)
    assert result.returncode == 0, result.stderr
    ll = (tmp_path / "unit.ll").read_text()
    body = next((line for line in ll.splitlines()
                 if '"Option$String" = type' in line), None)
    assert body is not None, "Option$String type not found in module"
    assert "{i8, [7 x i8], [24 x i8]}" in body, (
        f"synthesized Option$String body drifted from shared layout: {body}"
    )
