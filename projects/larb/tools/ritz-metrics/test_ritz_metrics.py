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
    # if, and, while, elif, or, two match arms => 1 + 7
    assert fns["branchy"].complexity == 8
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
