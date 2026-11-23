"""The name check is on by default (AGAST #1823).

ritz0 refuses an unknown fn, type or variable with `file:line:col` and no
flag; `--no-check-names` turns it off for bisecting a checker bug only, and
nothing that builds or gates ever passes it.  The resolver bugs the corpus
measurement and the pytest suite found are pinned here too:

- `impl Display for *u8` (ritzlib/fmt/display.ritz): the parser names the
  target `ptr_u8`, which the resolver called an unknown type.  That one bug
  failed 13 packages of `./rz build --all`.
- `await` in a plain fn: LANGUAGE_SPEC §16.2 allows it (it drives the future
  in place), the resolver refused it (34 sites: tier5 examples, ritzlib tests).
- `C_mk(c)`, a plain impl method's free name (R10, §5.4), was unknown; a
  generic impl's (`W_bump`) has none, and is refused in the emitter's and
  ritz1's words, not as "Unknown function".
- `println` / `eprintln` / `write` / `writeln` with an interpolated literal
  are the emitter's own; with a plain one they're ordinary names.  The
  placeholders' names are checked, located (AGAST #4594).
- `m.K`, `m.f()` and a `m.K =>` arm keep §15.3's `module.item` wording
  (LANGUAGE_SPEC.md pins it), not "Unknown identifier: m".
- A const's value is the const folder's: it refuses an unknown name there,
  located, as ritz1 frames it (`const 'T': element 1 ...`).

ritz1 parity: the three compilers refuse the same unknown names at the same
place (`test_unknown_name_refused_by_every_compiler`).
"""

import os
import subprocess
from pathlib import Path

import pytest
from name_resolver import resolve_names
from parser import parse
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = RITZ_ROOT.parents[1]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


def names(source: str) -> list:
    return [str(e) for e in resolve_names(parse(source))]


class TestResolverCorpusBugs:
    """Valid programs the resolver refused, and what it must still refuse."""

    @pytest.mark.parametrize("trait", ["Display", "Debug"])
    def test_impl_for_pointer_target(self, trait):
        src = (f"trait {trait}\n    fn show(self: @Self) -> i64\n\n"
               f"impl {trait} for *u8\n    fn show(self: @*u8) -> i64\n        0\n")
        assert names(src) == []

    def test_impl_for_unknown_named_target_still_refused(self):
        src = "trait T\n    fn f(self: @Self) -> i64\n\nimpl T for Nope\n    fn f(self: @Nope) -> i64\n        0\n"
        assert any("Unknown type: Nope" in e for e in names(src)), names(src)

    def test_await_in_a_plain_fn(self):
        # §16.2: `await` outside an `async fn` drives the future in place.
        src = ("async fn get() -> i32\n    42\n\n"
               "fn main() -> i32\n    let v: i32 = await get()\n    v\n")
        assert names(src) == []

    IMPL = "struct C\n    x: i32\n\nimpl{TP} C{TA}\n    fn mk(self) -> i32\n        0\n\n"

    def test_free_name_of_a_plain_impl_method(self):
        # R10 (§5.4): `C_mk(c)` calls `impl C`'s `mk`.
        src = self.IMPL.format(TP="", TA="") + "fn f(c: C) -> i32\n    C_mk(c)\n"
        assert names(src) == []

    def test_generic_impl_method_has_no_free_name(self):
        # The emitter's and ritz1's words, not "Unknown function" (LARB R37).
        src = (self.IMPL.format(TP="<T>", TA="<T>").replace("struct C\n", "struct C<T>\n")
               + "fn f(c: C<i32>) -> i32\n    C_mk(c)\n")
        assert names(src) == [("<stdin>:9:5: `mk` is a method of generic `C<T>`: "
                              "call it as `c.mk()`")], names(src)

    # `m.K` / `m.f()` / a `m.K =>` arm: an unknown qualifier before an item
    # is module access, refused in §15.3's actionable words (pinned by
    # LANGUAGE_SPEC.md's doc example), not "Unknown identifier: m".
    MOD = "const K: i32 = 7\nfn f() -> i32\n    1\n\nfn main() -> i32\n"
    MSG = ("`m.{n}`: there is no `module.item` access (LANGUAGE_SPEC §15.3). "
           "Imported names share one namespace, so write `{n}`")

    @pytest.mark.parametrize("body,item", [
        ("    m.K\n", "K"),
        ("    m.f()\n", "f"),
        ("    match 7\n        m.K => 1\n        _ => 0\n", "K"),
    ], ids=["field", "method", "pattern"])
    def test_module_item_access_keeps_its_wording(self, body, item):
        errs = names(self.MOD + body)
        assert len(errs) == 1 and errs[0].endswith(self.MSG.format(n=item)), errs

    def test_a_value_before_an_item_name_is_not_module_access(self):
        # `m.f()` with `m` a local is a method call, even with a free fn `f`.
        assert names(self.MOD.replace("fn main() -> i32\n", "fn main(m: i32) -> i32\n")
                     + "    m.f()\n") == []

    def test_unknown_qualifier_before_a_non_item_still_unknown(self):
        # `m.nope`: `nope` is no item, so `m` is just an unknown name.
        assert names(self.MOD + "    m.nope\n") == ["<stdin>:6:5: Unknown identifier: m"]

    def test_const_value_is_the_folders(self):
        # The const folder refuses `NOPE`, located, as ritz1 frames it.
        assert names("const T: [2]i32 = [1, NOPE]\n") == []
        assert any("Unknown type: Nope" in e for e in names("const T: Nope = 1\n"))

    @pytest.mark.parametrize("call", ['println("{x}")', 'eprintln("{x}")',
                                      'write(w, "{x}")', 'writeln(w, "{x}")'])
    def test_interpolated_print_forms_are_builtins(self, call):
        src = f"fn f(w: i32, x: i32)\n    {call}\n"
        assert names(src) == []

    @pytest.mark.parametrize("call", ['println("x")', 'writeln(w, "x")'])
    def test_plain_print_forms_are_ordinary_names(self, call):
        # Without a placeholder the emitter calls whatever fn is in scope.
        src = f"fn f(w: i32)\n    {call}\n"
        assert any("Unknown function" in e for e in names(src)), names(src)

    # AGAST #4594: an interpolated literal's placeholders are expressions,
    # and their names are checked, located, as any other expression's.
    @pytest.mark.parametrize("call,col", [
        ('print("a {nope}\\n")', 15), ('println("{nope}")', 15),
        ('eprintln("{nope}")', 16), ('write(w, "{nope}")', 15),
        ('writeln(w, "{nope}")', 17), ('format_into(w, "{nope}")', 21),
    ], ids=["print", "println", "eprintln", "write", "writeln", "format_into"])
    def test_unknown_placeholder_name_is_unknown(self, call, col):
        errs = names(f"fn f(w: i32)\n    {call}\n")
        assert len(errs) == 1 and errs[0].endswith(": Unknown identifier: nope"), errs
        assert errs[0].startswith("<stdin>:2:"), errs

    def test_placeholder_names_in_scope_are_known(self):
        src = ("const K: i32 = 1\nfn g() -> i32\n    2\n\n"
               "fn f(w: i32, x: i32)\n    println(\"{x} {K} {g()} {x + K:08x}\")\n")
        assert names(src) == []

    def test_hidden_name_in_a_placeholder_reported_once(self):
        # import_visibility's walker is name_resolver's: it walked the
        # placeholders itself, and must not walk them twice now.
        from import_visibility import _HiddenUses
        mod = parse("fn f()\n    println(\"{c_val()}\")\n", "main.ritz")
        walker = _HiddenUses({"c_val": ("c", "b", mod.items[0], "c.ritz")}, "main.ritz")
        walker._collect_definitions(mod)
        walker._check_item(mod.items[0])
        assert len(walker.found) == 1 and "`c_val` is undefined" in walker.found[0], walker.found

    def test_await_operand_still_walked(self):
        src = "fn main() -> i32\n    let v: i32 = await nope()\n    v\n"
        assert any("Unknown function: nope" in e for e in names(src)), names(src)


# name -> (program, (line, col) of the unknown name, ritz0's line, ritz1's
# message).  An unknown type is refused before the name check, by the
# always-on type-name pass (type_names.py): same place, its own words.
CASES = {
    "fn": ("pub fn main() -> i32\n    return nope(1)\n",
           (2, 12), "Name error: {at}: Unknown function: nope",
           "Unknown function: nope"),
    "type": (("struct S\n    x: i32\n\nfn f(s: @S) -> i32\n    let q: Nope = 0\n    return 0\n\n"
             "pub fn main() -> i32\n    return 0\n"),
             (5, 12), "Error: {at}: unknown type `Nope`", "unknown type `Nope`"),
    "variable": ("pub fn main() -> i32\n    let x: i32 = 1\n    return x + nope\n",
                 (3, 16), "Name error: {at}: Unknown identifier: nope",
                 "ritz1 cannot emit: unknown identifier 'nope'"),
}


def _compile(compiler, src: Path, ll: Path, *flags):
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    if compiler == "ritz0":
        return run_ritz0([str(src), "-o", str(ll), *flags], cwd=src.parent, env=env, timeout=120)
    return subprocess.run([str(RITZ1_BUILD / compiler), str(src), "-o", str(ll)],
                          cwd=src.parent, env=env, capture_output=True, text=True,
                          timeout=120, check=False)


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(CASES))
def test_unknown_name_refused_by_every_compiler(request, tmp_path, compiler, name):
    """No flag: each compiler refuses the name at the same line and column."""
    request.getfixturevalue({"ritz0": "run_ritz0", "ritz1": "ritz1_bin",
                             "ritz1_selfhosted": "ritz1_selfhosted"}[compiler])
    program, (line, col), ritz0_line, ritz1_message = CASES[name]
    src = tmp_path / "main.ritz"
    src.write_text(program)
    ll = tmp_path / "main.ll"
    comp = _compile(compiler, src, ll)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"{compiler} accepted an unknown {name}:\n{out[-2000:]}"
    assert not ll.exists(), f"{compiler} wrote IR for a refused program"
    at = f"{src}:{line}:{col}"
    if compiler == "ritz0":
        # The checker's words: with the check off, the emitter would be the
        # first to refuse, as "Compiler error: ...".
        expected = ritz0_line.format(at=at)
    else:
        expected = f"{at}: error: {ritz1_message}"
    assert expected in out.splitlines(), f"{compiler}: want {expected!r}:\n{out[-2000:]}"


@pytest.mark.integration
def test_no_check_names_escape_turns_the_check_off(tmp_path):
    """The bisecting escape: the emitter is then the first to refuse."""
    program, (line, col), _, _ = CASES["fn"]
    src = tmp_path / "main.ritz"
    src.write_text(program)
    comp = _compile("ritz0", src, tmp_path / "main.ll", "--no-check-names")
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0
    assert f"Compiler error: {src}:{line}:{col}: Unknown function: nope" in out.splitlines(), out[-2000:]


def test_compile_file_checks_names_by_default():
    import inspect

    import ritz0
    assert inspect.signature(ritz0.compile_file).parameters["check_names"].default is True
    assert ritz0._Compile.__dataclass_fields__["check_names"].default is True


# Every place a build, test run or gate starts ritz0 from.
ESCAPE_SCAN = [
    RITZ_ROOT / "build.py", *sorted(RITZ_ROOT.glob("build_*.py")),
    RITZ_ROOT / "ritz0" / "test_runner.py", RITZ_ROOT / "Makefile",
    WORKSPACE / "rz",
    *sorted((RITZ_ROOT / "tools").rglob("*.py")),
    *sorted((RITZ_ROOT / "tools").rglob("*.sh")),
    *sorted((RITZ_ROOT / "scripts").rglob("*")),
]


def test_nothing_that_builds_or_gates_passes_the_escape():
    """`--no-check-names` is for bisecting by hand only (AGAST #1823)."""
    hits = []
    for path in ESCAPE_SCAN:
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for n, line in enumerate(text.splitlines(), start=1):
            if "no-check-names" in line or "check_names=False" in line:
                hits.append(f"{path.relative_to(WORKSPACE)}:{n}: {line.strip()}")
    assert not hits, "the name check's escape is for bisecting only:\n" + "\n".join(hits)
    assert (RITZ_ROOT / "build.py").is_file() and (RITZ_ROOT / "ritz0" / "test_runner.py").is_file()
