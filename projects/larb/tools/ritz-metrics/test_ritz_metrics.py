"""Unit tests for ritz_metrics (LARB v4 review tooling, AGAST #1800)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import ritz_metrics as rm  # noqa: E402

RITZ_SRC = """\
import ritzlib.sys

# a comment with if and or that must not count
fn simple(a: i32) -> i32
    return a

pub fn branchy(name: *u8, name_len: i32) -> i32
    var buf: [64]u8
    if name_len > 3 and name_len < 10
        while name_len > 0
            name_len = name_len - 1
    elif name_len == 0 or name_len == 1
        return 1
    match name_len
        2 => 3
        _ => 4
    return 0
"""


@pytest.mark.unit
def test_function_extraction_and_complexity(tmp_path):
    f = tmp_path / "x.ritz"
    f.write_text(RITZ_SRC)
    fns = {fn.name: fn for fn in rm.extract_functions(f, RITZ_SRC.splitlines(), "ritz")}
    assert set(fns) == {"simple", "branchy"}
    assert fns["simple"].complexity == 1
    assert fns["simple"].line == 4
    # if, and, while, elif, or, and a lookup match (one decision) => 1 + 6
    assert fns["branchy"].complexity == 7
    assert fns["branchy"].max_depth == 3  # fn -> if -> while -> stmt
    assert (
        fns["branchy"].smells.get("ptr_len_param_pair", 0) == 0
    )  # header line is not body
    assert fns["branchy"].smells["fixed_u8_buffer"] == 1


@pytest.mark.unit
def test_comments_and_strings_do_not_count():
    assert rm.strip_strings_and_comment('x = "if and or" # if or') == 'x = "" '


@pytest.mark.unit
def test_duplicates_found_across_files():
    block = [f'    emit_str(s, c"  line number {i} of the block")' for i in range(6)]
    files = {"a.ritz": ["fn a()"] + block, "b.ritz": ["fn b()"] + block}
    dups = rm.find_duplicates(files, window=6)
    assert dups and dups[0]["count"] == 2


@pytest.mark.unit
def test_cli_runs_on_directory(tmp_path, capsys):
    (tmp_path / "x.ritz").write_text(RITZ_SRC)
    assert rm.main([str(tmp_path), "--top", "5"]) == 0
    out = capsys.readouterr().out
    assert "branchy" in out and "## Duplicated" in out


# AGAST #4566: a `match` whose every arm maps a constant pattern to a constant
# value is a lookup table.  A const array would score 1; Ritz can't index one
# by an enum that carries data (`Tag.Unknown(StrView)`, LANGUAGE_SPEC §10.4),
# so the match is the table, and it counts as one decision, not one per arm.
def _cc(src: str) -> int:
    fns = rm.extract_functions(Path("x.ritz"), src.splitlines(), "ritz")
    assert len(fns) == 1, fns
    return fns[0].complexity


def _fn(*arms: str, scrutinee: str = "tag") -> str:
    return "fn f(tag: Tag) -> i32\n    match " + scrutinee + "\n" + "".join(
        f"        {a}\n" for a in arms
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "arms",
    [
        # enum -> bool set membership (tag_is_special)
        ("Tag.Area => true", "Tag.Base => true", "Tag.Br => true", "_ => false"),
        # string -> variant, default wrapping the scrutinee (tag_from_name)
        ('"html" => Tag.Html', '"head" => Tag.Head', "_ => Tag.Unknown(name)"),
        # variant -> string, a payload echoed back (tag_name)
        ('Tag.Html => "html"', 'Tag.Head => "head"', "Tag.Unknown(name) => name"),
        # or-patterns, chars, negative ints, consts
        ("' ' | '\\t' => 1", "Kind.A | Kind.B => -1", "_ => MODE_IN_BODY"),
    ],
    ids=["enum-to-bool", "string-to-variant", "variant-to-string", "or-patterns"],
)
def test_a_lookup_match_counts_once(arms):
    assert _cc(_fn(*arms)) == 2


@pytest.mark.unit
@pytest.mark.parametrize(
    "arms",
    [
        # a call is work, not data: a dispatch match still counts every arm
        ("Op.Read => sys_read(a)", "Op.Write => 1", "_ => 0"),
        # an operator computes
        ("Op.Read => n + 1", "Op.Write => 1", "_ => 0"),
        # a field read depends on state
        ("Op.Read => tb.mode", "Op.Write => 1", "_ => 0"),
        # a guard tests state
        ("Op.Read if n > 0 => 1", "Op.Write => 1", "_ => 0"),
    ],
    ids=["call", "operator", "field", "guard"],
)
def test_a_match_that_computes_counts_every_arm(arms):
    assert _cc(_fn(*arms)) == 4


@pytest.mark.unit
def test_a_block_arm_counts_every_arm():
    src = _fn("Op.Read =>", "    1", "Op.Write => 1", "_ => 0")
    assert _cc(src) == 4


@pytest.mark.unit
def test_a_lookup_nested_in_a_dispatch_counts_once_inside_it():
    src = (
        "fn f(x: Option<Op>) -> i32\n"
        "    match x\n"
        "        Some(s) => match s\n"
        "            Op.Read => 1\n"
        "            Op.Write => 2\n"
        "            _ => 3\n"
        "        None => 0\n"
    )
    # outer: two arms (its first is a nested match, not a constant); inner: one
    assert _cc(src) == 1 + 2 + 1
