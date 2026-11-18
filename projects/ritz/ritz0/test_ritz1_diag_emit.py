"""ritz1's emitter errors are printed through `diag` (AGAST #3445, #3621).

Every one is a single stderr line

    <file>:<line>:<col>: error: <message>

the shape ritz0 prints.  Before #3445 the emitter had its own printers:
emit_ir_error and friends printed `error: ritz1 cannot emit: <msg>` with no
location at all, print's errors named a line only (`error: ritz1 cannot
emit: line N: ...`), and the rest wrote the location after the word
(`error: <file>:<line>:<col>: <msg>`).  Only the prefix changed: the message
text is frozen (ritz0's *_rules.py shares it).

One row per printer, each at the construct it reports: the row fails on its
own if that printer loses or misplaces its location.  A table, one test per
compiler (docs/TESTING.md, "What a ritz0 pytest case costs"); the failure
names every failing row.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"

COMPILERS = ["ritz1", "ritz1_selfhosted"]

_SLOT = "enum Slot<T>\n    Full(T)\n    Empty\n\n"
_PAYLOAD_E = "enum E\n    A(i32)\n    B\n\n"
_UNIT_E = "enum E\n    A\n    B\n\n"
_CANNOT = "ritz1 cannot emit: "

# name -> (source, "line:col", message, extra ritz1 args)
ROWS = {
    # emit_ir_error_begin / _end
    "unknown_identifier": (
        "fn main() -> i32\n    return no_such_name\n",
        "2:12", _CANNOT + "unknown identifier 'no_such_name'", []),
    # emit_ir_error_begin through ptr_elem_size_unknown's threaded span
    "ptr_elem_size_unknown": (
        "extern fn get() -> *void\n\npub fn main() -> i32\n    let i: i64 = 1\n"
        "    let p: i64 = (get() + i) as i64\n    return 0\n",
        "5:19", _CANNOT + "pointer arithmetic: element size of pointee unknown for 'get'", []),
    # emit_nd_error
    "nd_error": (
        "fn main() -> i32\n    let a: [3]i32 = [1, 2, 3]\n    let b: i64 = a\n    0\n",
        "3:18", "a whole array is not a value here (index it, copy it into an array "
        "of the same type, or take its address with @)", []),
    # emit_qualified_variant_error
    "qualified_variant": (
        _PAYLOAD_E + "fn main() -> i32\n    let a: E = E.B(3)\n    0\n",
        "6:16", "'E.B' takes no payload", []),
    # emit_module_item_error
    "module_item": (
        "fn helper() -> i32\n    1\n\nfn main() -> i32\n    return util.helper()\n",
        "5:12", "`util.helper`: there is no `module.item` access (LANGUAGE_SPEC §15.3). "
        "Imported names share one namespace, so write `helper`", []),
    # emit_ambiguous_variant_error
    "ambiguous_variant": (
        "enum A\n    X\n    Y\n\nenum B\n    X\n    Z\n\nfn main() -> i32\n"
        "    let v = X\n    return 0\n",
        "10:13", "ambiguous enum variant 'X': declared by enum 'A' and enum 'B'; "
        "qualify it, e.g. 'A.X'", []),
    # mem_builtin_error
    "mem_builtin": (
        "fn main() -> i32\n    let v: i64 = atomic_load()\n    0\n",
        "2:18", "atomic_load takes 1 argument", []),
    # test_fn_error: a FnDef has a line only; a top-level fn is at column 1
    "test_fn": (
        "[[test]]\nfn t(x: i32) -> i32\n    return 0\n\nfn main() -> i32\n    return 0\n",
        "2:1", "[[test]] function 't' must take no parameters", ["--test-table"]),
    # emit_no_instance_error
    "no_instance": (
        _SLOT + "fn main() -> i32\n    let a: i64 = Empty\n    0\n",
        "6:18", "can't infer the `Slot` instance `Empty` builds: give its slot a "
        "`Slot<...>` type", []),
    # const_scalar_addr_refused
    "const_addr": (
        "const N: i32 = 5\n\nfn main() -> i32\n    let p: i64 = @N\n    return 0\n",
        "4:18", "cannot take the address of const `N`; a const scalar has no storage", []),
    # emit_enum_to_int
    "enum_to_int": (
        _PAYLOAD_E + "fn main() -> i32\n    let e: E = E.B\n    let n: i32 = e as i32\n    return n\n",
        "7:18", "cannot convert enum 'E' to an integer: variant 'A' carries data", []),
    # eai_check_arg
    "enum_as_int_arg": (
        _UNIT_E + "fn take(x: i32) -> i32\n    x\n\nfn main() -> i32\n    return take(E.A)\n",
        "9:17", "argument 1 of `take`: expected i32, found enum 'E'; convert with `as`", []),
    # emit_print_error: was `error: ritz1 cannot emit: line 3: ...`
    "print_error": (
        "fn main() -> i32\n    let n: i32 = 1\n    print(c\"n={n}\\n\")\n    0\n",
        "3:11", _CANNOT + "`c\"...\"` literals do not interpolate: the placeholder would "
        "be printed verbatim. Use a plain string literal `\"...\"` here, or `{{` to "
        "print a literal brace", []),
    # fmt_error: was `error: ritz1 cannot emit: line 5: format_into: ...`
    "format_into_error": (
        "import ritzlib.string\n\nfn main() -> i32\n    var m: String = string_new()\n"
        "    format_into(m, \"x\")\n    0\n",
        "5:5", _CANNOT + "format_into: format_into's sink must be a pointer to the "
        "buffer (`@&buf`), not a value: appending to a copy would be lost", []),
    # assert_placement_error
    "assert_placement": (
        "fn main() -> i32\n    assert 1 == 1\n    return 0\n",
        "2:5", "assert is only allowed in [[test]] and [[test_helper]] functions, "
        "not in 'main'", []),
}


def _row_failure(binary, tmp_path, name):
    source, where, message, extra = ROWS[name]
    d = tmp_path / name
    d.mkdir()
    (d / "unit.ritz").write_text(source)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    proc = subprocess.run([str(binary), "unit.ritz", "-o", "unit.ll", *extra], cwd=d,
                          env=env, capture_output=True, text=True, timeout=300)
    out = proc.stdout + proc.stderr
    want = rf"^unit\.ritz:{where}: error: {re.escape(message)}$"
    if proc.returncode == 0 or (d / "unit.ll").exists():
        return f"{name}: accepted\n{out[-800:]}"
    if not re.search(want, out, re.M):
        return f"{name}: want `unit.ritz:{where}: error: {message}`, got:\n{out[-800:]}"
    return None


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
def test_emitter_errors_are_located_by_diag(request, tmp_path, compiler):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    failures = [f for f in (_row_failure(binary, tmp_path, n) for n in sorted(ROWS)) if f]
    assert not failures, f"{compiler}:\n" + "\n\n".join(failures)
