"""tools/ritz1_text_ratchet.py: ritz1's old emitter text form, pinned down-only (AGAST #4696)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import ritz1_text_ratchet as rt

pytestmark = pytest.mark.unit

PORTED = ("emitter_expr_arith",)


def test_counts_the_three_forms():
    text = "\n".join(
        [
            'fn put(s: *EmitterState, t: *u8) -> *u8',
            '    emit_str(s, c"  ret void\\n")',
            '    emit_str(s, IR_NL)   # emit_str( c"x" in a comment',
            '    let p: *u8 = c"two" ; let q: *u8 = c"c"',
        ]
    )
    assert rt.count_file(text) == {"c_literals": 3, "emit_str": 2, "u8_params": 2}


def test_a_string_holding_the_words_is_not_a_call():
    row = rt.count_file('    format_into(s, "emit_str(x) is the old form")\n')
    assert row["emit_str"] == 0


def test_a_ported_form_counts_nothing():
    text = 'fn add(s: *EmitterState, r: i32) -> i32\n    format_into(s, "  %.{r} = add i64 0, 0\\n")\n    r\n'
    assert rt.count_file(text) == {"c_literals": 0, "emit_str": 0, "u8_params": 0}


def test_a_count_above_its_pin_is_a_breach_and_below_is_not():
    row = {"c_literals": 3, "emit_str": 2, "u8_params": 1}
    assert rt.breaches({"f": row}, {"f": row}) == []
    assert rt.breaches({"f": row}, {"f": {"c_literals": 4, "emit_str": 2, "u8_params": 9}}) == []
    assert rt.breaches({"f": row}, {"f": {"c_literals": 2, "emit_str": 2, "u8_params": 1}}) == [
        "f.c_literals: 3 > pin 2"
    ]


def test_a_file_with_no_pin_is_pinned_at_zero():
    assert rt.breaches({"new": {"c_literals": 1, "emit_str": 0, "u8_params": 0}}, {}) == ["new.c_literals: 1 > pin 0"]


def test_update_writes_this_trees_counts_and_refuses_to_raise(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.ritz").write_text('fn f() -> i32\n    emit_str(s, c"x")\n    0\n')
    (src / "ported.ritz").write_text("fn g() -> i32\n    0\n")
    (src / "parser_gen.ritz").write_text('emit_str(s, c"generated")\n')
    base = tmp_path / "base.json"
    assert rt.main(["--src", str(src), "--baseline", str(base), "--update"]) == 0
    files = json.loads(base.read_text())["files"]
    assert files == {"a": {"c_literals": 1, "emit_str": 1, "u8_params": 0}}
    (src / "a.ritz").write_text('fn f() -> i32\n    emit_str(s, c"x")\n    emit_str(s, c"y")\n    0\n')
    assert rt.main(["--src", str(src), "--baseline", str(base)]) == 1
    assert rt.main(["--src", str(src), "--baseline", str(base), "--update"]) == 1
    assert json.loads(base.read_text())["files"] == files


def test_this_tree_is_within_its_baseline():
    assert rt.breaches(rt.measure(rt.DEFAULT_SRC), rt.load(rt.DEFAULT_BASELINE)) == []


@pytest.mark.parametrize("name", PORTED)
def test_a_ported_file_is_pinned_at_zero_in_every_column(name):
    assert name not in rt.load(rt.DEFAULT_BASELINE)
    assert rt.measure(rt.DEFAULT_SRC)[name] == dict.fromkeys(rt.COLUMNS, 0)
