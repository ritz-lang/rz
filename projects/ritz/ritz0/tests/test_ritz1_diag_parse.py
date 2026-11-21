"""AGAST #3445: ritz1's parser-side and pre-emit errors print through `diag`.

Every ritz1 error is one line, `<file>:<line>:<col>: error: <message>`, the
shape ritz0 prints.  The printers ported here used to put `error: ` first:

    error: unit.ritz:3:1: unknown attribute 'nope' (known: ...)

and each built its own location (enum_error_at, si_error_at, gi_error's,
sema_error_at's, cc_report's, eprint_location_at and a dozen inline copies
in ast_helpers.ritz).  They all go through ritz1/src/diag.ritz now; only the
prefix moved, the message text is frozen (it is shared with ritz0's
*_rules.py and pinned by the tests of each rule).

One row per printer that was ported, each the error of a different module
or helper, so reverting any one port fails its row alone:

    parse     ast_helpers  parser_report_dropped_item (eprint_location_at)
    attr      ast_helpers  attr_unknown, one of the inline prefixes
    enum      ast_helpers  enum_error_at
    index     struct_index si_error_at
    infer     generic_infer gi_error
    must_use  sema         sema_error_at
    call      call_check   cc_report

Rows run through ritz1 and ritz1_selfhosted.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz1", "ritz1_selfhosted"]

# name -> (source, the frozen message after `unit.ritz:L:C: error: `)
CASES = {
    "parse": (
        ("fn main() -> i32\n"
        "    let x: i32 = )\n"
        "    0\n"),
        "unexpected ')'",
    ),
    "attr": (
        ("[[nope]]\n"
        "fn main() -> i32\n"
        "    0\n"),
        ("unknown attribute 'nope' (known: always_inline, callconv, inline, "
        "must_use, naked, noinline, packed, target_arch, target_os, test, test_helper)"),
    ),
    "enum": (
        ("enum E: u8\n"
        "    A = 300\n"
        "\n"
        "fn main() -> i32\n"
        "    0\n"),
        "discriminant 300 of variant 'A' does not fit enum 'E''s representation type u8",
    ),
    "index": (
        ("struct P\n"
        "    x: i32\n"
        "\n"
        "fn main() -> i32\n"
        "    var p: P\n"
        "    let v: i32 = p[0]\n"
        "    0\n"),
        "`P` can't be indexed: it doesn't implement `Index` (§7.8)",
    ),
    "infer": (
        ("fn make<T>() -> i32\n"
        "    0\n"
        "\n"
        "fn main() -> i32\n"
        "    make()\n"),
        "can't infer `T` for `make`: write `make<T>(...)`",
    ),
    "must_use": (
        ("[[must_use]]\n"
        "fn f() -> i32\n"
        "    1\n"
        "\n"
        "fn main() -> i32\n"
        "    f()\n"
        "    0\n"),
        "result of [[must_use]] fn 'f' is discarded",
    ),
    "call": (
        ("fn f(a: i32) -> i32\n"
        "    a\n"
        "\n"
        "fn main() -> i32\n"
        "    f(1, 2)\n"),
        "`f` called with 2 argument(s) but defined with 1",
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_error_is_file_line_col_error_message(request, tmp_path, compiler, name):
    source, message = CASES[name]
    src = tmp_path / "unit.ritz"
    src.write_text(source)
    ll = tmp_path / "unit.ll"
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), str(src), "-o", str(ll)], check=False, cwd=tmp_path,
                          env=env, capture_output=True, text=True, timeout=300)
    err = proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{err[-1500:]}"
    # AGAST #1819: the located diagnostic may now end with
    # `; expected one of: ...` (the grammar's FIRST set at the failure).
    want = rf"^\S*unit\.ritz:\d+:\d+: error: {re.escape(message)}(; .*)?$"
    assert re.search(want, err, re.MULTILINE), f"{compiler}, {name}: want {want!r}:\n{err[-1500:]}"


# AGAST #3621: exact locations for the two parser errors #3445 left short.
# `trait_decl_refused` printed col 0 (the grammar passed the `fn` token's line
# only); it is at the `fn` token now, where ritz0 reports it.  The dropped-item
# tally is about the whole file, so it is `<file>: error: ` (diag_file_error_at)
# with no line.
EXACT = {
    "trait_extern": (
        ("trait T\n"
        "    fn f(self) -> i32 = extern\n"
        "\n"
        "fn main() -> i32\n"
        "    0\n"),
        r"unit\.ritz:2:5: error: trait method 'f' cannot be declaration-only "
        r"\(= extern\): a trait method is a signature already; drop '= extern'",
    ),
    "dropped_tally": (
        ("struct P\n"
        "    x: m.S\n"
        "\n"
        "fn main() -> i32\n"
        "    0\n"),
        r"unit\.ritz: error: 1 top-level item\(s\) failed to parse; "
        r"refusing to emit a partial module",
    ),
}


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(EXACT))
def test_error_is_at_its_exact_place(request, tmp_path, compiler, name):
    source, want = EXACT[name]
    (tmp_path / "unit.ritz").write_text(source)
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    # A relative path, so the prefix is exactly `unit.ritz`.
    proc = subprocess.run([str(binary), "unit.ritz", "-o", "unit.ll"], check=False,
                          cwd=tmp_path, env=env, capture_output=True, text=True, timeout=300)
    err = proc.stderr
    assert proc.returncode != 0, f"{compiler} accepted {name}:\n{err[-1500:]}"
    assert not (tmp_path / "unit.ll").exists(), f"{compiler} wrote IR for {name}"
    assert re.search(rf"^{want}$", err, re.MULTILINE), f"{compiler}, {name}: want {want!r}:\n{err[-1500:]}"
