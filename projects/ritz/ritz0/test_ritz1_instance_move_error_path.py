#!/usr/bin/env python3
"""A move error in a generic fn's instance names the file the fn is written in (AGAST #2890).

ritz1 move-checks every instance monomorph creates: `twice<i32>(3)` from
`import dup` refuses `let b = d` after `let a = d`, as ritz0 does. But
ownership.ritz's own_eprint_loc printed emitter_source_file(), the file
being compiled, so the error pointed at `main.ritz:9:13`, a line main.ritz
doesn't have. It now prints fn_source_file(emitter_current_fn()), the
instance's own file, as ritz0 does. emit_impl_method now sets the current
fn too: before, a method's error named the file of whatever fn was emitted
before it, which became dup.ritz once that could be an instance.

What #2890 reported as "ritz1 skips the move check" was a call written
`twice(3)`, without type arguments: ritz1 created no instance and emitted a
call to an undeclared `@twice`, so there was nothing to check. Since #1982
the call infers `twice<i64>` (LANGUAGE_SPEC §4.4) and is checked like the
spelled-out one (the `_inferred` rows).

ritz0 checked `twice<D>`'s instance too, but kept only its moves out of a
reference: a `T`-typed local moved twice, or borrowed after its move, at
`T = D` compiled (AGAST #2921). It now keeps every use or borrow of a moved
value an instance finds, the `_at_drop_type` rows; `t_param_at_copy_type`
is the same body at `T = i32`, where the move is a copy.

Each row compiles `main.ritz` beside one module, `dup.ritz`. Each expected
location names the file its line and column are counted in.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest
from ritz0_inproc import run_ritz0

RITZ_ROOT = Path(__file__).resolve().parent.parent
RITZ1_BUILD = RITZ_ROOT / "ritz1" / "build"
RITZ1S = ["ritz1", "ritz1_selfhosted"]

pytestmark = pytest.mark.integration

_D = ("pub struct D\n    id: i32\nimpl Drop for D\n    fn drop(self: @&D)\n"
      "        self.id = 0\n")

# A Drop local moved twice in a generic fn: `let b = d` is line 9, col 13.
_LOCAL = _D + ("pub fn twice<T>(x: T) -> i32\n    let d = D { id: 1 }\n"
               "    let a = d\n    let b = d\n    0\n")
# A T-typed param moved twice, the instance at T = D: line 8, col 16.
_PARAM = _D + ("pub fn twice<T>(x: T) -> i32\n    let a: T = x\n    let b: T = x\n"
               "    0\n")
# A T-typed param borrowed after it moved, at T = D: `@x` is line 8, col 13
# (AGAST #2921).
_BORROW = _D + ("pub fn twice<T>(x: T) -> i32\n    let a: T = x\n    let r = @x\n"
                "    0\n")
# A generic struct `w: W<T>` whose field `w.a: T` moves, at T = D. The
# second statement, line 11, uses what the first, line 10, moved.
_W = _D + "pub struct W<T>\n    a: T\npub fn twice<T>(x: T) -> i32\n    let w = W<T> { a: x }\n"
_FIELD = _W + "    let a: T = w.a\n    let b: T = w.a\n    0\n"
_WHOLE_AFTER_FIELD = _W + "    let a: T = w.a\n    let v = w\n    0\n"
_FIELD_AFTER_WHOLE = _W + "    let v = w\n    let a: T = w.a\n    0\n"
_BORROW_AFTER_FIELD = _W + "    let a: T = w.a\n    let r = @w\n    0\n"
# One move: nothing to refuse.
_ONCE = _D + ("pub fn twice<T>(x: T) -> i32\n    let d = D { id: 1 }\n"
              "    let a = d\n    0\n")

_MAIN = "import dup\n{extra}pub fn main() -> i32\n    {call}\n"

# A method in main.ritz with its own use after move, emitted after the
# instance: its error names main.ritz (lines 8 and 7 of main.ritz).
_METHOD = ("struct M\n    v: i32\nimpl M\n    fn bad(self: @M) -> i32\n"
           "        let d = D { id: 1 }\n        let a = d\n        let b = d\n        0\n")

# name: (module, main.ritz's extra items, call,
#        (file, line, col, name, moved line, moved col) or None).
# A moved line of None expects "cannot borrow `name` - ... has been moved",
# which names no move site on any compiler.
CASES = {
    "drop_local": (_LOCAL, "", "twice<i32>(3)", ("dup", 9, 13, "d", 8, 13)),
    "t_param_at_drop_type": (_PARAM, "", "twice<D>(D { id: 1 })", ("dup", 8, 16, "x", 7, 16)),
    "borrow_t_param_at_drop_type": (_BORROW, "", "twice<D>(D { id: 1 })",
                                    ("dup", 8, 13, "x", None, None)),
    "field_of_t_at_drop_type": (_FIELD, "", "twice<D>(D { id: 1 })", ("dup", 11, 16, "w.a", 10, 16)),
    "whole_after_field_at_drop_type": (_WHOLE_AFTER_FIELD, "", "twice<D>(D { id: 1 })",
                                       ("dup", 11, 13, "w.a", 10, 16)),
    "field_after_whole_at_drop_type": (_FIELD_AFTER_WHOLE, "", "twice<D>(D { id: 1 })",
                                       ("dup", 11, 16, "w", 10, 13)),
    "borrow_after_field_at_drop_type": (_BORROW_AFTER_FIELD, "", "twice<D>(D { id: 1 })",
                                        ("dup", 11, 13, "w", None, None)),
    # At T = i32 the move is a copy: nothing to refuse.
    "t_param_at_copy_type": (_PARAM, "", "twice<i32>(3)", None),
    "moved_once": (_ONCE, "", "twice<i32>(3)", None),
    "main_method_after_instance": (_ONCE, _METHOD, "twice<i32>(3)", ("main", 8, 17, "d", 7, 17)),
    # #1982: `twice(3)` infers T = i64, so its instance exists and is checked.
    "drop_local_inferred": (_LOCAL, "", "twice(3)", ("dup", 9, 13, "d", 8, 13)),
    "moved_once_inferred": (_ONCE, "", "twice(3)", None),
}

def _write(tmp_path, module, extra, call):
    (tmp_path / "dup.ritz").write_text(module)
    main = tmp_path / "main.ritz"
    main.write_text(_MAIN.format(extra=extra, call=call))
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{tmp_path}")
    return main, tmp_path / "main.ll", env


def _check(rc, out, expected):
    if expected is None:
        assert rc == 0, out
        return
    file, line, col, name, mline, mcol = expected
    other = "main" if file == "dup" else "dup"
    assert rc != 0, out
    if mline is None:
        pat = rf"(^|[\s/]){file}\.ritz:{line}:{col}: .*cannot borrow `{re.escape(name)}` - .*has been moved"
    else:
        # The error and the earlier move are both located in `file`.
        pat = (rf"(^|[\s/]){file}\.ritz:{line}:{col}: .*use of moved value: `{re.escape(name)}` "
               rf"\(moved at \S*{file}\.ritz:{mline}:{mcol}\)")
    assert re.search(pat, out, re.MULTILINE), out
    assert f"{other}.ritz:" not in out, out


@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz0(tmp_path, name):
    module, extra, call, expected = CASES[name]
    main, ll, env = _write(tmp_path, module, extra, call)
    proc = run_ritz0([str(main), "-o", str(ll)], cwd=tmp_path, env=env, timeout=300)
    _check(proc.returncode, proc.stdout + proc.stderr, expected)


@pytest.mark.parametrize("compiler", RITZ1S)
@pytest.mark.parametrize("name", sorted(CASES))
def test_ritz1(request, tmp_path, compiler, name):
    request.getfixturevalue("ritz1_bin")
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    module, extra, call, expected = CASES[name]
    main, ll, env = _write(tmp_path, module, extra, call)
    proc = subprocess.run([str(binary), str(main), "-o", str(ll)], check=False, cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=300)
    _check(proc.returncode, proc.stdout + proc.stderr, expected)
