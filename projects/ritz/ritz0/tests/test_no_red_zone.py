"""AGAST #4308: harland's kernel functions used the x86-64 red zone.

THE DEFECT

build.py hands clang already-emitted .ll, so a [[bin]]'s `-mno-red-zone`
(`[bin.NAME.flags] no-red-zone = true`) is a frontend flag that never
reaches codegen: only the IR function attribute `noredzone` does. ritz0
added it only when its `--target` triple was freestanding, and build.py
never passes `--target` (only `--target-os`), so ritz0 emitted for its
default `x86_64-unknown-linux-gnu` and harland.elf had ~250 leaf functions
keeping locals below %rsp. An interrupt taken on the current kernel stack
(IST 0, ring 0) pushes its frame there and clobbers them.

THE FIX

* `--no-red-zone` (ritz0 and ritz1) puts `noredzone` on every function the
  module defines. Without it nothing changes (ritz0 still adds it for a
  freestanding `--target`, as before).
* The flag keys each compiler's own IR cache: a warm compile must not
  reuse IR built without it.
* build.py passes it for a [[bin]] whose flags set `no-red-zone = true`
  (tools/test_build_no_red_zone.py), and keys the artifact store on it.
* harland's boot test (tools/test_tier1_boot.sh) runs
  harland/tools/check_no_red_zone.py on harland.elf, so a regression fails
  the boot step in CI. The checker is tested here on synthetic input.
"""

import importlib.util
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ritz0_inproc import run_ritz0
import test_ir

RITZ0_DIR = Path(__file__).resolve().parents[1]
RITZ_ROOT = RITZ0_DIR.parent
HARLAND = RITZ_ROOT.parent / "harland"
CHECKER = HARLAND / "tools" / "check_no_red_zone.py"


# A leaf fn (no call, so no `sub rsp`: its locals go in the red zone, as
# ioapic_read's did), an impl method (a separate define path in ritz1) and a
# naked fn (no frame: noredzone is optional there), and a struct returned
# by pointer (ritz1 writes its __ritz_sret_copy helper by hand).
PROGRAM = """\
struct Ctr
    n: i64

impl Ctr
    fn bump(self: *Ctr) -> i64
        self.n = self.n + 1
        self.n

fn leaf(a: i64, i: i64) -> i64
    var buf: [4]i64
    buf[0] = a
    buf[1] = a * 3
    buf[2] = a + 7
    buf[3] = a - 1
    buf[i & 3]

[[naked]]
fn bare()
    asm x86_64:
        ret

struct Big
    data: [40]i64

fn make_big(x: i64) -> Big
    var b: Big
    b.data[39] = x
    b

fn main() -> i32
    var c: Ctr = Ctr { n: 0 }
    c.bump()
    let big: Big = make_big(3)
    (leaf(1, 2) + big.data[39]) as i32
"""


def _define_lines(ir: str) -> dict:
    """{fn name: its `define` line}, quoted or bare names."""
    out = {}
    for line in ir.splitlines():
        m = re.match(r'define [^@]*@"?([A-Za-z0-9_$.]+)"?\(', line)
        if m:
            # A private fn's symbol carries its file (AGAST #1858).
            out[test_ir.strip(m.group(1))] = line
    return out


def _attr_groups(ir: str) -> dict:
    """{'#N': attribute text} for the module's `attributes #N = { ... }`."""
    return {m.group(1): m.group(2)
            for m in re.finditer(r"^attributes (#\d+) = \{(.*)\}$", ir, re.M)}


def _has_noredzone(ir: str, define_line: str) -> bool:
    if "noredzone" in define_line:
        return True
    groups = _attr_groups(ir)
    return any("noredzone" in groups.get(g, "")
               for g in re.findall(r"#\d+", define_line))


def _assert_all_noredzone(ir: str, method_name: str) -> None:
    defs = _define_lines(ir)
    # Not the naked fn: it has no frame, so nothing to keep below %rsp.
    for fn in ("leaf", "main", method_name):
        assert fn in defs, f"no define for {fn} in:\n{ir}"
        assert _has_noredzone(ir, defs[fn]), f"{fn} lacks noredzone: {defs[fn]}"


def _assert_none_noredzone(ir: str) -> None:
    assert "noredzone" not in ir, ir


def _ritz0(tmp_path: Path, src: Path, *extra) -> str:
    ll = tmp_path / (src.stem + ".ll")
    proc = run_ritz0([src, "-o", ll, "--no-runtime", *extra], cwd=RITZ0_DIR,
                     env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ll.read_text()


def _ritz1(ritz1: Path, tmp_path: Path, src: Path, *extra) -> str:
    """Compile with `ritz1`: the `ritz1_bin` fixture's path (AGAST #5005)."""
    ll = tmp_path / (src.stem + ".ll")
    proc = subprocess.run([str(ritz1), str(src), "-o", str(ll), *extra],
                          cwd=tmp_path, capture_output=True, text=True, timeout=300,
                          env=dict(os.environ, RITZ_PATH=str(RITZ_ROOT)))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return ll.read_text()


@pytest.fixture
def program(tmp_path):
    src = tmp_path / "rz_prog.ritz"
    src.write_text(PROGRAM)
    return src


def _below_rsp(obj: Path) -> list:
    """objdump lines that address memory below %rsp."""
    dis = subprocess.run(["objdump", "-d", "--no-show-raw-insn", str(obj)],
                         capture_output=True, text=True, check=True).stdout
    return [l for l in dis.splitlines() if re.search(r"-0x[0-9a-f]+\(%rsp", l)]


def _compile_obj(tmp_path: Path, ir: str, name: str) -> Path:
    """`ir` as a harland object. alignstack(16) is stripped: a realigned
    frame happens to avoid the red zone, and the point is that noredzone
    alone keeps it out (harland's IR had no alignstack before #4308)."""
    ll = tmp_path / f"{name}.ll"
    ll.write_text(ir.replace(" alignstack(16)", ""))
    obj = tmp_path / f"{name}.o"
    # harland's object flags (build_pipeline.freestanding_target: no -O, so
    # every parameter's alloca is a stack slot), minus -mno-red-zone: it must
    # be the IR attribute that does the work (clang ignores the flag for .ll).
    subprocess.run(["clang", "-c", "--target=x86_64-none-elf", "-ffreestanding",
                    "-fno-builtin", "-mcmodel=kernel", "-Wno-override-module",
                    str(ll), "-o", str(obj)], check=True, timeout=120)
    return obj


needs_toolchain = pytest.mark.skipif(
    shutil.which("clang") is None or shutil.which("objdump") is None,
    reason="clang/objdump not on PATH")


# --- ritz0 -----------------------------------------------------------------

@pytest.mark.integration
def test_ritz0_flag_marks_every_defined_fn(tmp_path, program):
    _assert_all_noredzone(_ritz0(tmp_path, program, "--no-red-zone"), "Ctr_bump")


@pytest.mark.integration
def test_ritz0_default_hosted_emits_no_noredzone(tmp_path, program):
    _assert_none_noredzone(_ritz0(tmp_path, program))


@pytest.mark.integration
def test_ritz0_freestanding_triple_still_marks_every_fn(tmp_path, program):
    _assert_all_noredzone(_ritz0(tmp_path, program, "--target", "x86_64-none-elf"),
                          "Ctr_bump")


@pytest.mark.integration
def test_ritz0_warm_compile_keys_on_the_flag(tmp_path, program):
    """Same source, same output path: off, then on, then off again."""
    _assert_none_noredzone(_ritz0(tmp_path, program))
    assert "noredzone" in _ritz0(tmp_path, program, "--no-red-zone")
    _assert_none_noredzone(_ritz0(tmp_path, program))


@pytest.mark.integration
@needs_toolchain
def test_ritz0_object_never_addresses_below_rsp(tmp_path, program):
    """The control proves the program does use the red zone without the flag,
    so the second assertion is not vacuous."""
    off = _compile_obj(tmp_path, _ritz0(tmp_path, program), "off")
    assert _below_rsp(off), "control: expected red-zone use without --no-red-zone"
    on = _compile_obj(tmp_path, _ritz0(tmp_path, program, "--no-red-zone"), "on")
    assert _below_rsp(on) == []


@pytest.mark.integration
def test_ritz0_llvmlite_attrs_keep_no_builtins(tmp_path, program):
    """noredzone and sspstrong are llvmlite attributes, printed between a
    define's `)` and `!dbg`. The text pass that adds alignstack(16) and
    "no-builtins" (AGAST #1313/#1917) used to need `)` right before `!dbg`,
    so either attribute silently dropped both: with --stack-protector that
    was every harland function."""
    for flags in (("--no-red-zone",), ("--stack-protector",),
                  ("--no-red-zone", "--stack-protector")):
        ir = _ritz0(tmp_path, program, *flags)
        defs = _define_lines(ir)
        for fn in ("leaf", "main", "Ctr_bump"):
            assert 'alignstack(16) "no-builtins"' in defs[fn], (flags, defs[fn])
        assert "no-builtins" not in defs["bare"], (flags, defs["bare"])


def _assert_every_define_noredzone(ir: str) -> None:
    """Every define but a naked one: helpers the compiler writes by hand
    (sret copy/zero, print, platform hooks) included."""
    for name, line in _define_lines(ir).items():
        if " naked" in line:
            continue
        assert _has_noredzone(ir, line), f"{name} lacks noredzone: {line}"


@pytest.mark.integration
def test_ritz0_every_define_carries_noredzone(tmp_path, program):
    _assert_every_define_noredzone(_ritz0(tmp_path, program, "--no-red-zone"))


# --- ritz1 (the gate builds it first, as for test_stack_protector.py) -------

@pytest.mark.integration
def test_ritz1_flag_marks_every_defined_fn(ritz1_bin, tmp_path, program):
    _assert_all_noredzone(_ritz1(ritz1_bin, tmp_path, program, "--no-red-zone"), "Ctr_bump")


@pytest.mark.integration
def test_ritz1_every_define_carries_noredzone(ritz1_bin, tmp_path, program):
    ir = _ritz1(ritz1_bin, tmp_path, program, "--no-red-zone")
    assert "__ritz_sret_copy" in _define_lines(ir), "expected an sret helper"
    _assert_every_define_noredzone(ir)


@pytest.mark.integration
def test_ritz1_default_emits_no_noredzone(ritz1_bin, tmp_path, program):
    _assert_none_noredzone(_ritz1(ritz1_bin, tmp_path, program))


@pytest.mark.integration
def test_ritz1_warm_compile_keys_on_the_flag(ritz1_bin, tmp_path, program):
    """ritz1's sig fast path (AGAST #1807) must not hand back red-zone IR."""
    _assert_none_noredzone(_ritz1(ritz1_bin, tmp_path, program))
    assert "noredzone" in _ritz1(ritz1_bin, tmp_path, program, "--no-red-zone")
    _assert_none_noredzone(_ritz1(ritz1_bin, tmp_path, program))


# --- harland's checker -------------------------------------------------------

@pytest.fixture(scope="module")
def checker():
    spec = importlib.util.spec_from_file_location("harland_check_no_red_zone", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DISASM = """\
ffffffff80100000 <good>:
ffffffff80100000:\tsub    $0x18,%rsp
ffffffff80100004:\tmov    %rdi,0x8(%rsp)
ffffffff80100009:\tmov    -0x8(%rbp),%rax
ffffffff8010000d:\tadd    $0x18,%rsp
ffffffff80100011:\tret

ffffffff80100020 <bad_leaf>:
ffffffff80100020:\tmov    %al,-0x1(%rsp)
ffffffff80100024:\tmovzbl -0x1(%rsp),%edx
ffffffff80100029:\tret

ffffffff80100030 <also_bad>:
ffffffff80100030:\tmovq   $0x0,-0x10(%rsp,%rax,8)
ffffffff80100039:\tret
"""


def test_checker_reports_each_function_below_rsp(checker):
    assert checker.red_zone_functions(DISASM) == {
        "bad_leaf": ["mov    %al,-0x1(%rsp)", "movzbl -0x1(%rsp),%edx"],
        "also_bad": ["movq   $0x0,-0x10(%rsp,%rax,8)"],
    }


def test_checker_passes_clean_code(checker):
    clean = DISASM.split("\nffffffff80100020")[0] + "\n"
    assert checker.red_zone_functions(clean) == {}


@pytest.mark.integration
@needs_toolchain
def test_checker_cli_exit_codes(tmp_path, program):
    off = _compile_obj(tmp_path, _ritz0(tmp_path, program), "off")
    on = _compile_obj(tmp_path, _ritz0(tmp_path, program, "--no-red-zone"), "on")
    bad = subprocess.run(["python3", str(CHECKER), str(off)], capture_output=True, text=True)
    assert bad.returncode == 1 and "red zone" in bad.stdout + bad.stderr, bad
    good = subprocess.run(["python3", str(CHECKER), str(on)], capture_output=True, text=True)
    assert good.returncode == 0, good
