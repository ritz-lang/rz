"""AGAST #4690: ritzlib.json is `enum Json`, not a C tagged struct.

The module used to be `struct JsonValue { kind: i32, str_val: *u8, items:
**JsonValue, keys: **u8, .. }` with `JSON_*: i32` kind and error-code consts,
null-for-absent returns and a manual `free`.  standard_report doesn't count
struct fields or locals, so it reported 0 for it; these pins read the source.

  * no raw pointer in a struct field, a parameter or a return type;
  * no `i32` kind or code field, no `JSON_*` const, no `JsonValue`;
  * the shape is the enum `Json` (owned String/Vec payloads) and an error
    enum `JsonErrorKind`, returned in `Result<Json, JsonError>`;
  * standard_report counts nothing for the module.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from standard_report import scan_tree, summarise

pytestmark = pytest.mark.unit

RITZ_ROOT = Path(__file__).resolve().parent.parent.parent
JSON = RITZ_ROOT / "ritzlib" / "json.ritz"

# `*T`, `**T` or `*mut T` as a type: after a `:` or `->`, possibly inside a
# generic argument list or `Option<..>`.
RAW_PTR_TYPE = re.compile(r"(?::|->|<|,)\s*\*+\s*(?:mut\s+)?[A-Za-z_]")


def code_lines(text: str):
    """(lineno, line) of `text` without comment-only lines and trailing comments."""
    for n, line in enumerate(text.splitlines(), 1):
        line = line.split("#", 1)[0].rstrip()
        if line.strip():
            yield n, line


def raw_pointer_sites(text: str) -> list[str]:
    """Struct fields and fn signatures (params, returns) that name a raw pointer."""
    sites = []
    in_struct = False
    for n, line in code_lines(text):
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            in_struct = bool(re.match(r"(pub\s+)?struct\s", stripped))
        is_sig = re.match(r"(pub\s+)?fn\s", stripped)
        is_field = in_struct and indent > 0 and ":" in stripped
        if (is_sig or is_field) and RAW_PTR_TYPE.search(stripped):
            sites.append(f"{n}: {stripped}")
    return sites


def c_shape_sites(text: str) -> list[str]:
    """An i32 `kind` or `code` field, a JSON_* const, or the old type's name."""
    sites = []
    for n, line in code_lines(text):
        stripped = line.strip()
        if (re.match(r"(kind|code)\s*:\s*i32\b", stripped)
                or re.match(r"(pub\s+)?const\s+JSON_", stripped)
                or "JsonValue" in stripped):
            sites.append(f"{n}: {stripped}")
    return sites


OLD_SHAPE = """\
const JSON_STRING: i32 = 3

struct JsonValue
    kind: i32           # JSON_* type constant
    str_val: *u8        # Heap-allocated string (null-terminated)
    items: **JsonValue  # Array of JsonValue pointers
    keys: **u8          # For objects: array of key strings

struct JsonError
    code: i32           # JSON_ERR_* error code
    pos: i64

pub fn json_parse(input: StrView) -> Result<*JsonValue, JsonError>
    return Err(0)

impl JsonValue
    pub fn get_field(self: @JsonValue, key: StrView) -> Option<*JsonValue>
        return None
"""


def test_json_has_no_raw_pointer_field_param_or_return():
    assert raw_pointer_sites(JSON.read_text()) == []


def test_json_has_no_i32_kind_or_code_and_no_jsonvalue():
    assert c_shape_sites(JSON.read_text()) == []


def test_the_old_struct_turns_both_pins_red():
    """Mutation check: today's (pre-#4690) shape trips every pin above."""
    raw = raw_pointer_sites(OLD_SHAPE)
    assert len(raw) == 5, raw          # str_val, items, keys, json_parse, get_field
    assert len(c_shape_sites(OLD_SHAPE)) == 8


def test_json_is_an_enum_with_owned_parts():
    text = JSON.read_text()
    assert re.search(r"^pub enum Json\n", text, re.M)
    for variant in ("Null", "Bool(bool)", "Number(i64)", "Str(String)",
                    "Array(Vec<Json>)", "Object(Vec<JsonMember>)"):
        assert re.search(rf"^    {re.escape(variant)}\s*$", text, re.M), variant
    assert re.search(r"^pub enum JsonErrorKind\n", text, re.M)
    assert re.search(r"^pub fn json_parse\(input: StrView\) -> Result<Json, JsonError>$", text, re.M)


def test_json_has_no_standard_report_findings():
    summary = summarise(scan_tree([JSON]))
    assert {k: v for k, v in summary.items() if v["violations"] or v["exempt"]} == {}
