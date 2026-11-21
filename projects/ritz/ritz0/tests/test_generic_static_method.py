#!/usr/bin/env python3
"""`Type.m()` on a generic type's impl, and `match Some(..)` (AGAST #2185).

#2101 taught ritz0 `Opt.make(40)` for a non-generic enum's impl.  On a
generic one, `let b: Box<i32> = Box.mk(42)` was a bare Python
`ValueError: Unknown identifier: Box`: the emitter knows `Box$i32`, the
instance the monomorphizer laid out with its specialised impl, never the bare
template name, so the receiver fell through to being emitted as a value.  A
generic *struct*'s impl (`Cell.mk(42)`) took the same path to the same crash.

The receiver spells no type argument, so it takes the instance of the slot
the call fills, as a bare variant constructor does (§11.3): a typed `let`'s,
a parameter's, the fn's return type.  With no such slot, or a slot that
isn't an instance of the receiver's type, it's an error at the call that
says to give the binding a type, never a ValueError.

`match Some(42 as i32)`, the ticket's other form, already compiled by the time
this was picked up: a scrutinee constructor takes the instance its payload
binds (§11.3, AGAST #2437).  One row pins it with ritzlib's Option.

ritz1 accepted these programs and emitted the template's method,
uninstantiated (`call %Slot$T @Slot_mk(%T ..)`), which clang refused with no
source location (AGAST #3309).  It now calls the slot's instance's method,
which monomorph specialises for an enum's instance as for a struct's, and
refuses the REFUSED rows with ritz0's text at the call.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

import fast_link
from ritz0_inproc import run_ritz0

pytestmark = pytest.mark.integration

RITZ_ROOT = Path(__file__).resolve().parents[2]
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ_START = RITZ_ROOT / "runtime" / "ritz_start.x86_64.o"

SLOT = ("enum Slot<T>\n    Full(T)\n    Empty\n"
        "impl<T> Slot<T>\n    fn mk(x: T) -> Slot<T>\n        Full(x)\n")
# `Cell { v: x }` in the impl's own body is AGAST #3310: a free fn builds it.
CELL = ("struct Cell<T>\n    v: T\n"
        "fn cell<T>(x: T) -> Cell<T>\n    Cell<T> { v: x }\n"
        "impl<T> Cell<T>\n    fn mk(x: T) -> Cell<T>\n        cell(x)\n")
# `f` reads a Slot<i32>'s payload, 2 for Empty.
F = "fn f(o: Slot<i32>) -> i32\n    match o\n        Full(v) => v\n        Empty => 2\n"

# name -> (program, exit code).  One row per slot the type can come from.
RUNS = {
    # The ticket's own program, `Box` being an enum the user declares.
    "ticket_box_let": (
        "enum Box<T>\n    Val(T)\n    Nil\n"
        "impl<T> Box<T>\n    fn mk(x: T) -> Box<T>\n        Val(x)\n"
        "fn main() -> i32\n    let b: Box<i32> = Box.mk(42)\n"
        "    match b\n        Val(v) => v\n        Nil => 3\n", 42),
    # Not a name the built-in associated-call path knows (`Box` is one).
    "enum_let": (SLOT + F + "fn main() -> i32\n    let s: Slot<i32> = Slot.mk(5)\n    f(s)\n", 5),
    # An alias's target is the slot's type.
    "enum_alias_let": (SLOT + F + "type S = Slot<i32>\nfn main() -> i32\n"
                       "    let s: S = Slot.mk(4)\n    f(s)\n", 4),
    "enum_argument": (SLOT + F + "fn main() -> i32\n    f(Slot.mk(6))\n", 6),
    "enum_return": (SLOT + F + "fn g() -> Slot<i32>\n    return Slot.mk(7)\n"
                    "fn main() -> i32\n    f(g())\n", 7),
    "struct_let": (CELL + "fn main() -> i32\n    let c: Cell<i32> = Cell.mk(8)\n    c.v\n", 8),
    # The instance is the slot's, not the literal's default i64.
    "struct_let_u8": (CELL + "fn main() -> i32\n    let c: Cell<u8> = Cell.mk(200)\n"
                      "    sizeof(c.v) as i32\n", 1),
    # Form 1 of the ticket: ritzlib's Option, a scrutinee constructor.
    "match_some_scrutinee": ("import ritzlib.option\nfn main() -> i32\n"
                             "    match Some(42 as i32)\n        Some(v) => v\n        None => 3\n", 42),
}

# name -> (program, line:col of the call)
REFUSED = {
    "untyped_let": (SLOT + "fn main() -> i32\n    let s = Slot.mk(5)\n    0\n", "8:13"),
    "scrutinee": (SLOT + "fn main() -> i32\n    match Slot.mk(5)\n"
                  "        Full(v) => 1\n        Empty => 2\n", "8:11"),
    # Another generic type's instance: Slot$i32 has an `mk` too, not Cell's.
    "another_types_slot": (CELL + SLOT + "fn main() -> i32\n    let c: Slot<i32> = Cell.mk(5)\n"
                           "    0\n", "15:24"),
}


def _message(type_name, method):
    return (f"can't infer the type arguments of `{type_name}` for `{type_name}.{method}`: "
            f"give the binding a type")


def _compile(work, src):
    path, ll = work / "main.ritz", work / "main.ll"
    path.write_text(src)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    return comp, ll


@pytest.mark.parametrize("name", sorted(RUNS))
def test_static_call_on_generic_impl_runs(tmp_path, name):
    src, code = RUNS[name]
    comp, ll = _compile(tmp_path, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode == 0 and ll.exists(), f"ritz0 refused {name}:\n{src}\n{out[-2000:]}"
    exe = tmp_path / "main"
    link = fast_link.clang(["clang", "-w", str(ll), "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], timeout=60).returncode == code, name


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_static_call_without_an_instance_is_refused_at_it(tmp_path, name):
    src, where = REFUSED[name]
    comp, _ = _compile(tmp_path, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"ritz0 accepted {name}:\n{src}\n{out}"
    assert "Traceback" not in out and "ValueError" not in out, out[-2000:]
    type_name = "Cell" if "Cell" in src else "Slot"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, _message(type_name, "mk")) in found, f"{name}, wanted {where}:\n{out[-2000:]}"


# One ritz1 row per slot the instance comes from, and the struct form.
RITZ1_RUNS = ["ticket_box_let", "enum_let", "enum_alias_let", "enum_argument", "enum_return", "struct_let_u8"]


def _compile_ritz1(work, src):
    path, ll = work / "main.ritz", work / "main.ll"
    path.write_text(src)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    comp = subprocess.run([str(RITZ1_BUILD / "ritz1"), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)
    return comp, ll


@pytest.mark.parametrize("name", RITZ1_RUNS)
def test_ritz1_runs_a_static_call_on_a_generic_impl(ritz1_bin, tmp_path, name):
    """ritz1 calls the slot's instance's method (AGAST #3309)."""
    src, code = RUNS[name]
    comp, ll = _compile_ritz1(tmp_path, src)
    assert comp.returncode == 0, comp.stderr[-2000:]
    exe = tmp_path / "main"
    link = fast_link.clang(["clang", "-w", str(RITZ_START), str(ll), "-o", str(exe), "-nostdlib"],
                           cwd=tmp_path, capture_output=True, text=True)
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], timeout=60).returncode == code, name


@pytest.mark.parametrize("name", sorted(REFUSED))
def test_ritz1_refuses_a_static_call_without_an_instance_at_it(ritz1_bin, tmp_path, name):
    """ritz0's error at the call, not clang's at `%Slot$T` (AGAST #3309)."""
    src, where = REFUSED[name]
    comp, _ = _compile_ritz1(tmp_path, src)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, f"ritz1 accepted {name}:\n{src}\n{out}"
    type_name = "Cell" if "Cell" in src else "Slot"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, _message(type_name, "mk")) in found, f"{name}, wanted {where}:\n{out[-2000:]}"
