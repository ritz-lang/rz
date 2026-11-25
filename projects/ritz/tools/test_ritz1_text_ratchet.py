"""tools/ritz1_text_ratchet.py: ritz1's old emitter text form, pinned down-only (AGAST #4696)."""

import json
import re
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


# AGAST #4770: outside the emitter, literal text is a plain "..." StrView. A
# C literal wrapped in a hand-counted view, or compared with memcmp /
# bytes_eq_cstr, is the C form the port removed: its length is counted by hand.
_C_VIEW = re.compile(r'ptr: \(c"')
_C_COMPARE = re.compile(r'\b(?:memcmp|bytes_eq_cstr)\([^)]*c"')


def c_text_forms(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if _C_VIEW.search(line) or _C_COMPARE.search(line)]


@pytest.mark.parametrize(
    "line",
    [
        '    f(StrView { ptr: (c"self"), len: (4) as i64 })',
        '    if len > 4 and memcmp(name, c"ptr_", 4) == 0',
        '    if bytes_eq_cstr(name, c"Ok") == 1',
    ],
)
def test_a_c_literal_view_or_compare_is_found(line):
    assert c_text_forms(line) == [line.strip()]


def test_a_plain_literal_and_a_pointer_compare_are_not():
    text = '    f("self")\n    if name.starts_with("ptr_")\n    memcmp(a, b, n)\n'
    assert c_text_forms(text) == []


def test_no_c_literal_text_outside_the_emitter():
    found = [
        f"{p.name}: {line}"
        for p in sorted(rt.DEFAULT_SRC.glob("*.ritz"))
        if not p.name.startswith("emitter") and p.stem not in rt.GENERATED_MODULES
        for line in c_text_forms(p.read_text())
    ]
    assert found == []
