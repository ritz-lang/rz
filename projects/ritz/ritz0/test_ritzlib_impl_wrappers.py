"""LARB R66 step 1 (AGAST #3495): String's methods are a real `impl String`.

THE CHANGE

`s.push_str(x)` on a ritzlib `String` found its free fn (`string_push_str`)
through a name table, ritz0's `ufcs.py` and ritz1's `ufcs_non_generic_prefix`.
R66 replaces the table with impl blocks in the type's own file, each method a
one-line `pub` wrapper of the free fn, as `span.ritz`'s `impl<T> Span<T>`
already is. The table itself is deleted later, one ticket per compiler
(#3496, #3497); this step must leave `rz test --all` unchanged.

ONLY String, FOR NOW

`impl<T> Vec<T>` and `impl<T> Option<T>` wait on #3617. Both compilers
specialize every method of a generic impl for every instance of the type, even
one only an imported signature names. The Vec wrappers then pulled `malloc`
into every importer of ritzlib.gvec, and the `pop` / `get` / `unwrap_or`
wrappers were refused for a move-only T ("cannot move out of a reference")
though nothing called them. This step's first gate measured 272 failures.
`impl String` isn't generic: it compiles once, in string.ritz.

THE TESTS

  * `impl String` holds exactly the methods listed here, each `pub`, each a
    single `return string_<method>(...)` of its own free fn. A missing,
    extra, private or misrouted wrapper fails here by name.
  * with ritz0's table switched off for String (find_ufcs_function -> None,
    as #3496 will do), one program calling every wrapper by method syntax
    still compiles: every call resolves through the impl.
  * literal arguments, end to end on ritz0 and ritz1: ritz1 now reaches its
    impl method arms for String, which mis-passed a `"..."` into a `StrView`
    param (test_ritz1_impl_strview_lit_arg.py).

Behaviour of each method is not re-tested here: ritzlib/tests/
test_string_methods.ritz calls them by method syntax, and now reaches the impl.

NOT WRAPPED, on purpose

  * `drop`: ritz0 takes any `(T, 'drop')` method as T's destructor
    (_get_drop_fn_name), so a plain `drop` wrapper would make a String drop
    itself at scope end on top of the explicit `s.drop()`. Free a String
    with `string_drop(@&s)` instead (#3614; checked on the ritzlib suite).
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

import ritz_ast as rast
from lexer import Lexer
from parser import Parser

RITZ0_DIR = Path(__file__).resolve().parent
RITZ_ROOT = RITZ0_DIR.parent
RITZLIB = RITZ_ROOT / "ritzlib"

STRING_STATIC = {
    "new", "with_cap", "from", "from_cstr", "from_bytes", "from_strview",
    "from_i64", "from_hex",
}
STRING_METHODS = STRING_STATIC | {
    "len", "cap", "is_empty", "as_ptr", "as_view", "get", "push", "push_str",
    "push_cstr", "push_string", "push_bytes", "clear", "pop", "eq",
    "eq_string", "hash", "eq_cstr", "clone", "starts_with_string",
    "ends_with_string", "contains_string", "find", "slice", "char_at",
    "set_char", "starts_with", "ends_with", "contains", "push_i64",
    "to_lower", "eq_strview",
}


def _impl_methods(path: Path, type_name: str) -> dict:
    """name -> FnDef of the non-trait `impl` of `type_name` in `path`."""
    src = path.read_text()
    module = Parser(list(Lexer(src, str(path)).tokenize())).parse_module()
    found = {}
    for item in module.items:
        if (isinstance(item, rast.ImplBlock) and item.type_name == type_name
                and not item.trait_name):
            for m in item.methods:
                found[m.name] = m
    return found


def _body_text(path: Path, fn: rast.FnDef) -> str:
    """The source of fn's body, its lines after the header, stripped."""
    lines = path.read_text().splitlines()
    start = fn.span.line  # 1-based header line; the body follows it
    body = []
    for line in lines[start:]:
        if line.strip() and not line.startswith(" " * 8):
            break
        if line.strip():
            body.append(line.strip())
    return "\n".join(body)


@pytest.mark.unit
def test_impl_string_wraps_each_free_fn():
    path = RITZLIB / "string.ritz"
    methods = _impl_methods(path, "String")
    assert set(methods) == STRING_METHODS, (
        f"impl String: missing {sorted(STRING_METHODS - set(methods))}, "
        f"unexpected {sorted(set(methods) - STRING_METHODS)}")
    for name, fn in sorted(methods.items()):
        assert fn.is_pub, f"String.{name} must be `pub` (#3418)"
        params = [p.name for p in fn.params]
        want = f"string_{name}({', '.join(params)})"
        if fn.ret_type is not None:
            want = f"return {want}"
        body = _body_text(path, fn)
        assert body == want, f"String.{name}: body {body!r}, want {want!r}"
        if name in STRING_STATIC:
            assert "self" not in params, f"String.{name} is a constructor"
        else:
            assert params and params[0] == "self", f"String.{name} takes self"


# Every wrapper, by method syntax (constructors as `String.m(...)`).
EVERY_METHOD = """\
import ritzlib.string

fn main() -> i32
    var t: i64 = 0
    var s: String = String.new()
    var u: String = String.with_cap(8)
    let a: String = String.from("ab")
    let b: String = String.from_cstr(c"cd")
    let c: String = String.from_bytes(c"ef", 2)
    let d: String = String.from_strview("gh")
    let e: String = String.from_i64(42)
    let f: String = String.from_hex(255)
    s.push('x')
    s.push_str("yz")
    s.push_cstr(c"w")
    s.push_string(@a)
    s.push_bytes(c"qq", 2)
    s.push_i64(7)
    s.set_char(0, 'X')
    u.push_str("Hi")
    let g: String = s.clone()
    let h: String = s.slice(0, 2)
    let l: String = u.to_lower()
    t = t + s.len() + s.cap() + s.find(@a) + s.hash() as i64
    t = t + (s.get(0) + s.char_at(1) + s.pop()) as i64
    let ptr: *u8 = s.as_ptr()
    let view: StrView = s.as_view()
    if s.is_empty() or s.eq("x") or s.eq_string(@b) or s.eq_cstr(c"x")
        t = t + 1
    if s.starts_with("X") and s.ends_with("q") and s.contains("yz")
        t = t + 1
    if s.starts_with_string(@c) or s.ends_with_string(@d) or s.contains_string(@e)
        t = t + 1
    if s.eq_strview(view) or f.eq_strview(l.as_view()) or g.eq_strview(h.as_view())
        t = t + 1
    s.clear()
    return t as i32
"""

# The table, switched off for String as #3496 will delete it; the
# rest of ritz0 is unchanged. One interpreter launch: the in-process ritz0
# (ritz0_inproc) forks from a server that imported the emitter before any
# patch here could reach it.
NO_TABLE = """\
import sys
sys.path.insert(0, {ritz0!r})
import emitter_llvmlite
real = emitter_llvmlite.find_ufcs_function

def no_table(functions, type_name, method_name):
    if type_name == 'String':
        return None
    return real(functions, type_name, method_name)

emitter_llvmlite.find_ufcs_function = no_table
import ritz0
sys.argv = ['ritz0.py', {src!r}, '-o', {out!r}] + {extra!r}
ritz0.main()
"""


def _compile_without_table(src: Path, out: Path, extra=()) -> str:
    """ritz0 `src` -> `out` with the String table off; the IR text."""
    driver = NO_TABLE.format(ritz0=str(RITZ0_DIR), src=str(src),
                             out=str(out), extra=list(extra))
    proc = subprocess.run(
        [sys.executable, "-c", driver], cwd=out.parent, capture_output=True,
        text=True, timeout=300, check=False,
        env={"RITZ_PATH": str(RITZ_ROOT), "PATH": "/usr/bin:/bin"})
    assert proc.returncode == 0 and out.exists(), (
        f"ritz0 without the table:\n{proc.stdout[-3000:]}\n{proc.stderr[-3000:]}")
    return out.read_text()


@pytest.mark.integration
def test_every_method_resolves_without_the_table(tmp_path):
    src = tmp_path / "every.ritz"
    src.write_text(EVERY_METHOD)
    ir = _compile_without_table(src, tmp_path / "every.ll")
    # Each call went through a wrapper: its symbol is defined or declared.
    for sym in ("String_push_str", "String_from", "String_eq_strview"):
        assert re.search(rf'@"?[\w.$]*{re.escape(sym)}"?\(', ir), (
            f"{sym} not in the IR")


# String's literal-taking methods, end to end with ritzlib linked in: on ritz1
# these now reach `impl String`'s static and instance arms, which passed a
# `"..."` as a %Span$u8 where the StrView goes until this ticket
# (test_ritz1_impl_strview_lit_arg.py has the compiler-only rows).
STRING_LITERALS = """\
import ritzlib.string

fn main() -> i32
    var s: String = String.from("hi")
    let x = "xy"
    s.push_str("ab")
    s.push_str(x)
    if not s.eq("hiabxy")
        return 1
    if not s.starts_with("hia") or not s.contains(x)
        return 2
    return 42
"""


@pytest.mark.integration
@pytest.mark.parametrize("compiler", ["ritz0", "ritz1"])
def test_string_literal_args(request, tmp_path, compiler):
    from test_ritz1_builtin_struct_shadow import _run_pkg
    if compiler == "ritz1":
        request.getfixturevalue("ritz1_bin")
    assert _run_pkg(compiler, tmp_path, "strlit", STRING_LITERALS) == 42


# ritz0 gave every impl method `internal` linkage outside --no-runtime builds,
# `pub` or not, so an object compiled from string.ritz exported no
# `String_len` for another object to call (build.py compiles --no-runtime and
# never saw it; the pytest harnesses that link ritzlib units do). A `pub`
# method is exported like a `pub fn`; a private one stays internal.
LINKAGE = """\
struct Foo
    n: i64

impl Foo
    pub fn shown(self: @Foo) -> i64
        return self.n

    fn hidden(self: @Foo) -> i64
        return self.n

pub fn main() -> i32
    let f = Foo { n: 3 }
    return (f.shown() + f.hidden()) as i32
"""


@pytest.mark.integration
def test_a_pub_impl_method_is_exported(tmp_path):
    from ritz0_inproc import run_ritz0
    src = tmp_path / "linkage.ritz"
    src.write_text(LINKAGE)
    out = tmp_path / "linkage.ll"
    comp = run_ritz0([str(src), "-o", str(out)], cwd=tmp_path, timeout=300)
    assert comp.returncode == 0, comp.stdout + comp.stderr
    defs = {m.group(2): m.group(1) for m in re.finditer(
        r'^define (internal )?.*?@"?(Foo_\w+)"?\(', out.read_text(), re.MULTILINE)}
    assert defs == {"Foo_shown": None, "Foo_hidden": "internal "}, defs


@pytest.mark.integration
def test_string_methods_suite_compiles_without_the_table(tmp_path):
    """#3614: `String` has no `drop` method on purpose (see NOT WRAPPED), so
    its ritzlib suite frees a String with `string_drop(@&s)`. An `s.drop()`
    only resolved through the table and fails once #3496 deletes it."""
    _compile_without_table(
        RITZLIB / "tests" / "test_string_methods.ritz",
        tmp_path / "suite.ll", ["--no-runtime"])
