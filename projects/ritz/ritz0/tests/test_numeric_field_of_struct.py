"""AGAST #3233: `.N` is a tuple accessor only.

On a named struct, `h.0` in any position (read, store, `@`/`@&`, method
receiver, move) is refused, at the field, on all three compilers:
"`Holder` has no field `0`" (ritz1's wording, R17 rule 5(a)). A field inserted
above `t` would otherwise silently renumber it, as R19 refused `n as E`.

ritz0 used to read `h.0` positionally. The move checker took it for a use of
all of `h`, so `var a = h.0` copied the `Tracked` out while `h` still owned
it, and both dropped it (#2244's pin). ritz1 already refused it.

Positional `let (a, b) = h` of a struct isn't changed here (#3254).
"""

import os
import re
import subprocess

import pytest

import batching
from deref_rules import no_field
from ritz0_inproc import run_ritz0
from test_generic_enum_instance import RITZ1_BUILD, RITZ_ROOT

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

PROGRAM = """\
trait Drop
    fn drop(self: @&Self)

struct Tracked
    id: i32

impl Drop for Tracked
    fn drop(self: @&Tracked)
        var z = self.id

impl Tracked
    fn get(self: @Tracked) -> i32
        self.id

struct Holder
    t: Tracked
    n: i32

fn make(id: i32) -> Tracked
    Tracked { id: id }

fn consume(t: Tracked)
    var z = t.id

fn through(r: @Holder) -> i32
{through}
    0

fn main() -> i32
    var h = Holder { t: make(1), n: 2 }
{body}
    0
"""

# Each row's line; its `.0` is where the error is.
ROWS = {
    "read": ("    var a = h.0", ""),
    "move": ("    consume(h.0)", ""),
    "store": ("    h.0 = make(3)", ""),
    "addr": ("    let p = @h.0", ""),
    "addr_mut": ("    let p = @&h.0", ""),
    "receiver": ("    var x = h.0.get()", ""),
    "copy_field": ("    var x = h.1", ""),
    "through_reference": ("", "    var x = r.0.id"),
}


def _program(name):
    body, through = ROWS[name]
    src = (PROGRAM.replace("{body}", body or "    var y = 1")
           .replace("{through}", through or "    var y = 1"))
    line = body or through
    row = src.split("\n").index(line) + 1
    col = re.search(r"[hr]\.(\d)", line).start(1) + 1
    return src, f"{row}:{col}", re.search(r"[hr]\.(\d)", line).group(1)


def _emit(compiler, path, ll, work):
    env = dict(os.environ, RITZ_PATH=f"{RITZ_ROOT}:{work}")
    if compiler == "ritz0":
        return run_ritz0([str(path), "-o", str(ll)], cwd=work, env=env, timeout=300)
    binary = RITZ1_BUILD / compiler
    # Never skip (#1327): the gate builds both ritz1 binaries before pytest.
    assert binary.exists(), f"{binary} missing; run `make -C ritz1 bootstrap`"
    return subprocess.run([str(binary), str(path), "-o", str(ll)], cwd=work, env=env,
                          capture_output=True, text=True, timeout=300)


def _batch_compile(compiler, path, work):
    comp = _emit(compiler, path, work / "main.ll", work)
    return comp.returncode, comp.stdout + comp.stderr


@pytest.mark.integration
@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", sorted(ROWS))
def test_a_numbered_field_of_a_struct_is_refused_at_it(tmp_path, compiler, name):
    src, where, field = _program(name)
    at = tuple(map(int, where.split(":")))
    got = batching.refused(compiler, src, _batch_compile, at=at)
    if got is not None:  # AGAST #2806: this row's diagnostics from its chunk's batch
        out, where = got
    else:
        batching.per_row()
        path, ll = tmp_path / "main.ritz", tmp_path / "main.ll"
        path.write_text(src)
        comp = _emit(compiler, path, ll, tmp_path)
        out = comp.stdout + comp.stderr
        assert comp.returncode != 0, f"{compiler} accepted {name}:\n{src}\n{out}"
    found = re.findall(r"main\.ritz:(\d+:\d+): (?:error: )?(.*)", out)
    assert (where, no_field("Holder", field)) in found, \
        f"{compiler}: {name}, wanted {where}:\n{src}\n{out[-2000:]}"


# The emitter refuses it too, without the move checker that runs first: the
# struct's numbered-field read was its positional fallback (`extractvalue`).
@pytest.mark.integration
@pytest.mark.parametrize("name", sorted(ROWS))
def test_ritz0s_emitter_refuses_it_alone(tmp_path, name):
    src, where, field = _program(name)
    path = tmp_path / "main.ritz"
    path.write_text(src)
    comp = run_ritz0([str(path), "--no-check-ownership", "-o", str(tmp_path / "main.ll")],
                     cwd=tmp_path, env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)), timeout=300)
    out = comp.stdout + comp.stderr
    assert comp.returncode != 0, out
    assert f"main.ritz:{where}: {no_field('Holder', field)}" in out, out[-2000:]
