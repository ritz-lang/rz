"""Types follow the fn rule (AGAST #4609; LANGUAGE_SPEC §15.3).

Two structs, enums or type aliases of one name conflict only in the namespace
of a file that sees both: one that declares one and imports the other, or
imports both, directly or by `pub import`. A type reached only through
another module's plain (private) import is not in the importer's namespace,
so it conflicts with nothing there. Bare-variant ambiguity is judged over the
enums the file sees.

    # ta.ritz                  # ea.ritz                 # t.ritz
    pub enum Tag               import ta { Tag }         import ea { fa }
        A                      pub fn fa() -> i32        pub enum Tag
        B                          ... Tag.B ...             X

Found wiring tempest to lexis (#4012): lexis/lib/event.ritz imports its own
`Tag` privately, and tempest's own `pub enum Tag` was refused.

Both `Tag`s are in one program, so what is emitted from them must not
collide: a generic's instance over each (`pick$Box`) is its own object's copy
(internal), and a generated `E.from` carries its enum's file in its symbol.
Methods are `T_m` symbols, so two `Box`es that both define `get` are still
refused, as two `pub fn`s of one name are.

Every case runs ritz0 and both ritz1 binaries, compiles each file to its own
object as build.py does, links and runs.
"""

import os
import subprocess
from pathlib import Path

import pytest

import fast_link

from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]


def _write(tmp_path, files):
    for name, text in files.items():
        (tmp_path / f"{name}.ritz").write_text(text)


def _compile(compiler, tmp_path, name):
    src = tmp_path / f"{name}.ritz"
    ll = tmp_path / f"{name}_{compiler}.ll"
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    args = [str(src), "-o", str(ll)]
    if compiler == "ritz0":
        proc = run_ritz0(args + ["--no-runtime"], cwd=tmp_path, env=env, timeout=300)
    else:
        binary = RITZ1_BUILD / compiler
        # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
        assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
        proc = subprocess.run([str(binary)] + args, cwd=tmp_path, env=env,
                              capture_output=True, text=True, timeout=300)
    return proc, ll


def _run(compiler, tmp_path, files):
    """Write, compile each file to its own object, link, run: the exit code."""
    _write(tmp_path, files)
    objs = [str(RITZ_START)]
    for name in files:
        proc, ll = _compile(compiler, tmp_path, name)
        out = proc.stderr + proc.stdout
        assert proc.returncode == 0 and ll.exists(), f"{compiler} rejected {name}:\n{out}"
        objs.append(str(ll))
    exe = tmp_path / f"t_{compiler}"
    link = fast_link.clang(["clang", "-Wno-override-module", *objs, "-o", str(exe),
                           "-nostdlib", "-no-pie"], capture_output=True, text=True)
    assert link.returncode == 0, f"{compiler}: link failed:\n{link.stderr[-3000:]}"
    return subprocess.run([str(exe)], capture_output=True, timeout=60).returncode


def _refused(compiler, tmp_path, files, main, text):
    """`main` is refused, with `text` in the diagnostic."""
    _write(tmp_path, files)
    proc, _ = _compile(compiler, tmp_path, main)
    out = proc.stderr + proc.stdout
    assert proc.returncode != 0, f"{compiler} accepted {main}:\n{out}"
    assert text in out, out


# lexis's side: a `Tag` and a `Box`, imported privately by `ea`, which `t`
# imports for `fa` alone.
TA = """\
pub enum Tag
    A
    B
    Comment

pub struct Box
    v: i32

impl Box
    pub fn get(self: @Box) -> i32
        self.v + 100
"""

EA = """\
import ta { Tag, Box }

pub fn fa() -> i32
    let b = Box { v: 2 }
    match Tag.B
        Tag.A => 1
        Tag.B => b.get() - 100
        Tag.Comment => 3
"""

# tempest's side: its own `Tag` and `Box`, of other layouts.
T_OWN = """\
import ea { fa }

pub enum Tag
    X
    Y
    Z

pub struct Box
    w: i64
    v: i32

impl Box
    pub fn val(self: @Box) -> i32
        (self.w as i32) * 10 + self.v

fn main() -> i32
    let b = Box { w: 4, v: 5 }
    match Tag.Z
        Tag.Z => b.val() + fa()
        _ => 0
"""


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_privately_imported_type_conflicts_with_nothing(compiler, tmp_path):
    """The acceptance case: t's own Tag and Box beside ta's, reached only
    through ea's plain import. Each file's code reaches its own."""
    assert _run(compiler, tmp_path, {"ta": TA, "ea": EA, "t": T_OWN}) == 47
    # AGAST #4914: the SAME name imported twice from the SAME module stays
    # allowed (one definition, seen through two selective imports of it) --
    # unlike importing a name of one definition from two different modules
    # (test_two_modules_importing_one_name_of_different_kinds_is_refused).
    same_twice_dir = tmp_path / "same_twice"
    same_twice_dir.mkdir()
    assert _run(compiler, same_twice_dir, {
        "sa": "pub enum Command\n    Quit\n    Goto(i64)\n",
        "st": ("import sa { Command }\nimport sa { Command }\n\n"
               "fn main() -> i32\n"
               "    match Command.Quit\n"
               "        Command.Quit => 0\n"
               "        Command.Goto(_) => 1\n")}) == 0


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_generic_instance_over_each_twin_is_its_own(compiler, tmp_path):
    """`pick$Box` is emitted in ea's object for ta's Box and in t's for t's.
    Merged by the linker as one ODR symbol, one object calls the other's,
    which has the other's layout."""
    pick = ("pub fn pick<T>(a: T, b: T, second: bool) -> T\n"
            "    if second\n        return b\n    a\n")
    ea = ("import ta { Box }\nimport w { pick }\n\n"
          "pub fn fa() -> i32\n"
          "    pick<Box>(Box { v: 1 }, Box { v: 2 }, true).get() - 100\n")
    t = ("import ea { fa }\nimport w { pick }\n\n"
         "pub struct Box\n    w: i64\n    v: i32\n\n"
         "fn main() -> i32\n"
         "    let b = pick<Box>(Box { w: 7, v: 3 }, Box { w: 9, v: 4 }, true)\n"
         "    (b.w as i32) * 10 + b.v + fa()\n")
    assert _run(compiler, tmp_path, {"ta": TA, "w": pick, "ea": ea, "t": t}) == 96


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_renamed_twins_method_keeps_its_symbol(compiler, tmp_path):
    """ea's generic calls ta's `Box.get`; its instance is emitted in t's
    object, where ta's Box is renamed. The call is to `Box_get`, which ta's
    object defines."""
    ea = EA + ("\npub fn fg<T>(x: T) -> i32\n"
               "    let b = Box { v: 5 }\n    b.get() - 100\n")
    t = T_OWN.replace("import ea { fa }", "import ea { fa, fg }").replace(
        "b.val() + fa()", "b.val() + fa() + fg<i32>(0)")
    assert _run(compiler, tmp_path, {"ta": TA, "ea": ea, "t": t}) == 52


@pytest.mark.parametrize("compiler", COMPILERS)
def test_each_twins_generated_from_is_its_own(compiler, tmp_path):
    """Two `enum Tag: u8`s each get a generated `Tag.from` (§10.4). One
    symbol for both would hand one file's discriminants to the other."""
    ta = ("import ritzlib.option\n\npub enum Tag: u8\n    A = 1\n    B = 2\n")
    ea = ("import ritzlib.option\nimport ta { Tag }\n\n"
          "fn code(t: Tag) -> i32\n"
          "    match t\n        Tag.A => 50\n        Tag.B => 1\n\n"
          "pub fn fa() -> i32\n"
          "    match Tag.from(2)\n"
          "        Some(t) => code(t)\n"
          "        None => 60\n")
    t = ("import ritzlib.option\nimport ea { fa }\n\n"
         "pub enum Tag: u8\n    X = 2\n    Y = 5\n\n"
         "fn code(t: Tag) -> i32\n"
         "    match t\n        Tag.X => 90\n        Tag.Y => 10\n\n"
         "fn main() -> i32\n"
         "    match Tag.from(5)\n"
         "        Some(t) => code(t) + fa()\n"
         "        None => 70\n")
    assert _run(compiler, tmp_path, {"ta": ta, "ea": ea, "t": t}) == 11


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_hidden_enums_variant_leaves_a_bare_variant_unambiguous(compiler, tmp_path):
    """t's bare `Comment` is its own Ev's: ta's Tag declares a `Comment`
    too, but t doesn't see Tag (#4012's ParseEvent / State)."""
    t = ("import ea { fa }\n\n"
         "enum Ev\n    Other\n    Comment\n\n"
         "fn pick() -> Ev\n    Comment\n\n"
         "fn main() -> i32\n"
         "    match pick()\n"
         "        Ev.Comment => 20 + fa()\n"
         "        Ev.Other => 0\n")
    assert _run(compiler, tmp_path, {"ta": TA, "ea": EA, "t": t}) == 22


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_file_that_declares_one_and_imports_the_other_is_refused(compiler, tmp_path):
    t = T_OWN.replace("import ea { fa }", "import ea { fa }\nimport ta { Tag }")
    _refused(compiler, tmp_path, {"ta": TA, "ea": EA, "t": t}, "t",
             "Conflicting enum definition for 'Tag'")
    # AGAST #4914: two modules each selectively import a name of theirs that
    # names a DIFFERENT KIND -- m/a's `pub enum Command` beside m/b's `pub
    # struct Command`.  Both compilers used to register each kind in its own
    # namespace (structs, enums) and never compared one against the other,
    # so the second selective import silently won wherever the two met
    # (buddhafinger's core.commands Command enum and core.normal's Command
    # struct, found by #4909): the ticket's own words for the error this
    # must be are a guess, so only "Conflicting" and both files are checked.
    kinds_dir = tmp_path / "dup_kinds"
    kinds_dir.mkdir()
    files = {
        "ka": "pub enum Command\n    Quit\n    Goto(i64)\n",
        "kb": "pub struct Command\n    count: i64\n    extra: i64\n",
        "kt": ("import ka { Command }\nimport kb { Command }\n\n"
               "fn main() -> i32\n"
               "    let c = Command { count: 1, extra: 2 }\n"
               "    (c.extra - 2) as i32\n"),
    }
    _refused(compiler, kinds_dir, files, "kt", "Conflicting")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_a_file_that_imports_both_through_a_pub_import_is_refused(compiler, tmp_path):
    """m re-exports ta; t imports m and tb: t sees both Tags."""
    _refused(compiler, tmp_path, {
        "ta": TA,
        "m": "pub import ta\n",
        "tb": "pub enum Tag\n    X\n",
        "t": "import m\nimport tb\n\nfn main() -> i32\n    0\n"},
        "t", "Conflicting enum definition for 'Tag'")


@pytest.mark.parametrize("compiler", COMPILERS)
def test_twins_with_a_method_of_one_name_are_refused(compiler, tmp_path):
    """Both Boxes define `get`: one `Box_get` symbol for two methods."""
    t = T_OWN.replace("pub fn val(", "pub fn get(").replace("b.val()", "b.get()")
    _refused(compiler, tmp_path, {"ta": TA, "ea": EA, "t": t}, "t",
             "Conflicting method symbol 'Box_get'")
