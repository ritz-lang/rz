"""AGAST #1868: ritz0 emits the `[[test]]` table that ritzunit runs.

A test binary is the test file, compiled in test mode, linked with ritzunit's
runner (LANGUAGE_SPEC.md §17.1). The compiler, not a naming convention,
decides what is a test: test mode emits

    @__ritz_tests        [N x { StrView name, i32 ()* run }]
    @__ritz_tests_count  i64 N
    @__ritz_test_table   %RitzTest* (i64* count)   -- what the runner calls

with one entry per `[[test]]` function of the file being compiled, in source
order, and a `_start` that calls the runner's `main`. Before this, ritzunit
found tests by the `test_` symbol prefix (so ~114 helpers named `test_*` would
have run as tests and a `[[test]] fn check_x` would not), and the Python
harness generated a `main` per file.

`run` is always `fn() -> i32`: a `-> i64` or unit test is wrapped, so the
runner can call every entry the same way. These tests are in-process: they
parse and emit, nothing is spawned.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from emitter_llvmlite import EmitError, emit  # noqa: E402
from lexer import Lexer  # noqa: E402
from parser import Parser  # noqa: E402

pytestmark = pytest.mark.unit

SOURCE = """\
[[test]]
fn check_first() -> i32
    0

fn test_helper_not_a_test() -> i32
    1

[[test]]
fn test_unit()
    let x: i32 = 1

[[test]]
fn test_wide() -> i64
    256
"""


def _ir(src: str, test_mode: bool) -> str:
    module = Parser(Lexer(src, "t.ritz").tokenize()).parse_module()
    return emit(module, test_mode=test_mode, source_file="t.ritz")


def _table_names(ir: str) -> list:
    """Names in @__ritz_tests, in order, decoded from their string constants."""
    table = re.search(r'^@"?__ritz_tests"? = .*$', ir, re.M)
    assert table, f"no @__ritz_tests in test-mode IR:\n{ir}"
    names = []
    for gname in re.findall(r'@"?(__ritz_test_name\.\d+)"?', table.group(0)):
        const = re.search(rf'^@"?{re.escape(gname)}"? = .*c"([^"]*)"', ir, re.M)
        assert const.group(1).endswith("\\00"), "names are NUL-terminated"
        names.append(const.group(1)[:-3])
    return names


def test_table_lists_exactly_the_test_attributed_functions_in_order():
    """[[test]] decides membership: `check_first` is in, `test_helper_*` is out."""
    assert _table_names(_ir(SOURCE, True)) == ["check_first", "test_unit", "test_wide"]


def test_count_and_accessor_are_emitted_with_external_linkage():
    ir = _ir(SOURCE, True)
    assert re.search(r'^@"?__ritz_tests_count"? = (dso_local )?constant i64 3', ir, re.M), ir
    accessor = re.search(r'^define .*@"?__ritz_test_table"?\(.*$', ir, re.M)
    assert accessor, ir
    assert "internal" not in accessor.group(0) and "private" not in accessor.group(0)


def test_every_entry_is_called_as_fn_returning_i32():
    """Unit and i64 tests get an i32 wrapper; an i64 result is 0 or 1, never truncated.

    `test_wide` returns 256. Truncated to an exit status that is 0: a pass.
    """
    ir = _ir(SOURCE, True)
    entries = re.search(r'^@"?__ritz_tests"? = .*$', ir, re.M).group(0)
    assert "i32 ()*" in entries and "i64 ()*" not in entries, entries
    wide =re.search(r'define internal i32 @"?__ritz_test_run\.\d+"?\(\)[^{]*\{(?:(?!^\}).)*call i64 @"?test_wide"?(?:(?!^\}).)*^\}',
                     ir, re.M | re.S)
    assert wide, ir
    assert "icmp ne i64" in wide.group(0) and "trunc" not in wide.group(0), wide.group(0)


def test_test_mode_starts_in_the_runners_main():
    """The test file has no `main`; _start calls ritzunit's `main(argc, argv)`."""
    ir = _ir(SOURCE, True)
    assert "define void @_start() naked" in ir
    assert "call main" in ir
    assert "leaq 8(%rsp), %rsi" in ir  # argv is passed


def test_test_mode_drops_the_files_own_main():
    """A file's own `main` would clash with the runner's: test mode leaves it out."""
    ir = _ir(SOURCE + "\nfn main() -> i32\n    42\n", True)
    assert not re.search(r'^define .*@"?main"?\(', ir, re.M), ir


def test_normal_mode_emits_no_table():
    ir = _ir(SOURCE, False)
    assert "__ritz_tests" not in ir and "__ritz_test_table" not in ir


def test_file_without_tests_has_an_empty_table():
    ir = _ir("fn helper() -> i32\n    0\n", True)
    assert re.search(r'^@"?__ritz_tests_count"? = (dso_local )?constant i64 0', ir, re.M), ir


def test_test_with_parameters_is_rejected():
    with pytest.raises(EmitError, match=r"\[\[test\]\] function 'takes_arg'.*no parameters"):
        _ir("[[test]]\nfn takes_arg(x: i32) -> i32\n    x\n", True)


def test_test_with_non_integer_result_is_rejected():
    with pytest.raises(EmitError, match=r"\[\[test\]\] function 'gives_ptr'.*must return"):
        _ir("[[test]]\nfn gives_ptr() -> *u8\n    null\n", True)


def test_test_mode_ir_passes_the_llvm_verifier():
    import llvmlite.binding as llvm
    llvm.parse_assembly(_ir(SOURCE + "\nfn main() -> i32\n    42\n", True)).verify()
