"""The intrinsics table and inline asm (../razm/DESIGN.md "Intrinsics",
"Inline asm"), at the edges the corpus entries do not pin down alone.

The corpus (test_corpus.py) runs every scalar row against clang
(intrin_run), checks the disassembly of intrin, simd and asm, and runs
asm_run. These cases hold the rules that a whole-file comparison can pass
by accident: the feature gate on the x86 rows, the rotate-versus-funnel
choice, template labels that repeat across blocks, register choice for
unpinned operands, and the template relocations in the large model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import corpus as c
from conftest import run
from test_lower import HEAD, disassembly, function_body, text_relocs

EXIT_UNSUPPORTED = 2


def rllvm_ll(rllvm_bin: str, tmp_path: Path, text: str, *flags: str):
    src = tmp_path / "m.ll"
    src.write_text(HEAD + text)
    out = tmp_path / "m.o"
    return run([rllvm_bin, "-c", *flags, str(src), "-o", str(out)]), out


def run_both(rllvm_bin: str, tmp_path: Path, text: str) -> tuple[c.RunResult, c.RunResult]:
    """`text` built by clang and by rllvm, each linked hello's way and run."""
    src = tmp_path / "t.ll"
    src.write_text(HEAD + text)
    shim = c.clang_compile(c.entry("hosted/shim.ll"), tmp_path / "shim.o")
    extra = c.assemble("hosted", tmp_path / "extra.o")
    results = []
    for tool in (["clang"], [rllvm_bin]):
        name = Path(tool[0]).name
        obj = tmp_path / f"t.{name}.o"
        p = run([*tool, *c.PROFILE_FLAGS["hosted"], str(src), "-o", str(obj)])
        assert p.returncode == 0, p.stderr
        assert c.check_relocations(obj, "hosted") == []
        exe = tmp_path / f"t.{name}"
        link = c.link_hosted([shim, obj, extra], exe)
        assert link.returncode == 0, link.stderr
        results.append(c.run(exe))
    return results[0], results[1]


# --- the table's edges -----------------------------------------------------

SHA_IR = """
declare <4 x i32> @llvm.x86.sha256msg1(<4 x i32>, <4 x i32>)
define void @f(ptr %p) {FEATURES}{
entry:
  %a = load <4 x i32>, ptr %p
  %b = call <4 x i32> @llvm.x86.sha256msg1(<4 x i32> %a, <4 x i32> %a)
  store <4 x i32> %b, ptr %p
  ret void
}
"""


@pytest.mark.parametrize("features, ok", [
    ('"target-features"="+sha" ', True),
    ('"target-features"="+aes" ', False),
    ("", False),
], ids=["sha", "aes-only", "none"])
def test_x86_rows_follow_target_features_not_the_host(rllvm_bin, tmp_path, features, ok):
    p, obj = rllvm_ll(rllvm_bin, tmp_path, SHA_IR.replace("{FEATURES}", features))
    if ok:
        assert p.returncode == 0, p.stderr
        assert "sha256msg1" in disassembly(obj)
    else:
        assert p.returncode == EXIT_UNSUPPORTED, p.stderr
        assert "+sha" in p.stderr


def test_an_intrinsic_outside_the_table_exits_2(rllvm_bin, tmp_path):
    p, _ = rllvm_ll(rllvm_bin, tmp_path, """
declare i64 @llvm.abs.i64(i64, i1)
define i64 @f(i64 %x) {
entry:
  %r = call i64 @llvm.abs.i64(i64 %x, i1 false)
  ret i64 %r
}
""")
    assert p.returncode == EXIT_UNSUPPORTED
    assert "llvm.abs.i64" in p.stderr


FSH_IR = """
declare i32 @llvm.fshl.i32(i32, i32, i32)
declare i32 @llvm.fshr.i32(i32, i32, i32)
define i32 @rot(i32 %x, i32 %n) {
entry:
  %r = call i32 @llvm.fshl.i32(i32 %x, i32 %x, i32 %n)
  ret i32 %r
}
define i32 @rotr(i32 %x, i32 %n) {
entry:
  %r = call i32 @llvm.fshr.i32(i32 %x, i32 %x, i32 %n)
  ret i32 %r
}
define i32 @funnel(i32 %x, i32 %y, i32 %n) {
entry:
  %r = call i32 @llvm.fshl.i32(i32 %x, i32 %y, i32 %n)
  ret i32 %r
}
"""


def test_fsh_is_a_rotate_only_on_one_value(rllvm_bin, tmp_path):
    p, obj = rllvm_ll(rllvm_bin, tmp_path, FSH_IR)
    assert p.returncode == 0, p.stderr
    dis = disassembly(obj)

    def mnemonics(fn: str) -> set[str]:
        return {ln.split()[0] for ln in function_body(dis, fn)}

    assert "rol" in mnemonics("rot") and "shld" not in mnemonics("rot")
    assert "ror" in mnemonics("rotr") and "shrd" not in mnemonics("rotr")
    assert "shld" in mnemonics("funnel") and "rol" not in mnemonics("funnel")


def funnel_ir() -> str:
    """fshl/fshr on distinct operands at each width, counts 0, 1, N-1, N,
    N+1 and 2N-1 (DESIGN "Tests"): ritz emits only rotates, so intrin_run
    never reaches the shld/shrd, mod-16 and combined-byte paths."""
    lines = ["declare void @rt_hex(...)"]
    body = []
    n = 0
    for bits in (8, 16, 32, 64):
        mask = (1 << bits) - 1
        a, b = 0x9C3A5F17E2D48B61 & mask, 0x52E1B7A40C6F3D98 & mask
        for op in ("fshl", "fshr"):
            lines.append(f"declare i{bits} @llvm.{op}.i{bits}(i{bits}, i{bits}, i{bits})")
            for cnt in (0, 1, bits - 1, bits, bits + 1, 2 * bits - 1):
                n += 1
                wide = (f"  %x{n} = zext i{bits} %r{n} to i64" if bits < 64
                        else f"  %x{n} = add i64 %r{n}, 0")
                body += [f"  %a{n} = add i{bits} {a}, 0",
                         f"  %r{n} = call i{bits} @llvm.{op}.i{bits}(i{bits} %a{n}, i{bits} {b}, i{bits} {cnt})",
                         wide, f"  call void (...) @rt_hex(i64 %x{n})"]
    return "\n".join(lines + ["define i32 @main() {", "entry:", *body,
                               "  ret i32 0", "}", ""])


# fptoui.sat.i64 past 2^63 (where the 2^63 split matters) and at the bounds.
SAT_U64_IR = """
declare void @rt_hex(...)
declare i64 @llvm.fptoui.sat.i64.f64(double)
declare i64 @llvm.fptoui.sat.i64.f32(float)
define internal void @d(i64 %bits) {
entry:
  %p = alloca i64
  store i64 %bits, ptr %p
  %f = load double, ptr %p
  %r = call i64 @llvm.fptoui.sat.i64.f64(double %f)
  call void (...) @rt_hex(i64 %r)
  ret void
}
define internal void @s(i32 %bits) {
entry:
  %p = alloca i32
  store i32 %bits, ptr %p
  %f = load float, ptr %p
  %r = call i64 @llvm.fptoui.sat.i64.f32(float %f)
  call void (...) @rt_hex(i64 %r)
  ret void
}
define i32 @main() {
entry:
  call void @d(i64 4890909195324358656)
  call void @d(i64 4890909195324358657)
  call void @d(i64 4895412794951729152)
  call void @d(i64 4895412794951729151)
  call void @d(i64 4895412794951729153)
  call void @s(i32 1593835520)
  call void @s(i32 1593835521)
  call void @s(i32 1602224127)
  call void @s(i32 1602224128)
  ret i32 0
}
"""


@pytest.mark.parametrize("ir", ["funnel", "sat_u64"])
def test_rows_ritz_does_not_reach_run_as_clang(rllvm_bin, tmp_path, ir):
    text = funnel_ir() if ir == "funnel" else SAT_U64_IR
    oracle, ours = run_both(rllvm_bin, tmp_path, text)
    assert oracle.status == 0 and oracle.stdout
    assert ours == oracle


# --- inline asm ------------------------------------------------------------

# Two blocks reuse `1:`, a third uses `1f` before `1:`; an unpinned input
# and an early-clobber output must avoid every pinned and clobbered register.
ASM_IR = r"""
declare void @rt_hex(...)

define internal i64 @count(i64 %n) {
entry:
  %a = call i64 asm sideeffect "1:\0Adecq $0\0Ajnz 1b", "=&r,0,~{memory}"(i64 %n)
  %b = call i64 asm sideeffect "xorl %eax, %eax\0Amovq $1, $0\0A1:\0Aaddq $$2, %rax\0Adecq $0\0Ajnz 1b\0Amovq %rax, $0", "=&r,r,~{rax},~{memory}"(i64 %n)
  %c = call i64 asm sideeffect "movq $1, $0\0Atestq $0, $0\0Ajnz 1f\0Amovq $$99, $0\0A1:", "=&r,r,~{memory}"(i64 %a)
  %ab = add i64 %a, %b
  %r = add i64 %ab, %c
  ret i64 %r
}

define internal i64 @crowd(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e, i64 %f) {
entry:
  %r = call i64 asm sideeffect "movq $1, $0\0Aaddq $2, $0\0Aaddq $3, $0\0Aaddq $4, $0\0Aaddq $5, $0\0Aaddq $6, $0\0Axorq %r8, %r8\0Axorq %r9, %r9\0Axorq %r10, %r10", "=&r,{rax},{rcx},{rdx},{rsi},{rdi},r,~{r8},~{r9},~{r10},~{memory}"(i64 %a, i64 %b, i64 %c, i64 %d, i64 %e, i64 %f)
  ret i64 %r
}

define i32 @main() {
entry:
  %n = call i64 @count(i64 5)
  call void (...) @rt_hex(i64 %n)
  %m = call i64 @crowd(i64 1, i64 2, i64 4, i64 8, i64 16, i64 32)
  call void (...) @rt_hex(i64 %m)
  %s = trunc i64 %m to i32
  ret i32 %s
}
"""


def test_asm_labels_and_unpinned_registers_run_as_clang(rllvm_bin, tmp_path):
    oracle, ours = run_both(rllvm_bin, tmp_path, ASM_IR)
    assert oracle.status == 63 and oracle.stdout.count(b"\n") == 2
    assert ours == oracle


LARGE_ASM_IR = r"""
@g_slot = global i64 0
declare void @rt_hex(...)
define void @f() {
entry:
  call void asm sideeffect "movq g_slot(%rip), %rdi\0Acall rt_hex\0Ajmp rt_hex", "~{rdi},~{memory}"()
  ret void
}
"""


@pytest.mark.parametrize("flags", [[], ["-mcmodel=kernel"], ["-mcmodel=large"]],
                         ids=["small", "kernel", "large"])
def test_template_symbols_are_pc32_and_plt32_in_every_model(rllvm_bin, tmp_path, flags):
    p, obj = rllvm_ll(rllvm_bin, tmp_path, LARGE_ASM_IR, *flags)
    assert p.returncode == 0, p.stderr
    relocs = text_relocs(obj)
    assert relocs["g_slot"] == {c.R_X86_64_PC32}
    assert relocs["rt_hex"] == {c.R_X86_64_PLT32}


def test_a_float_asm_operand_exits_2(rllvm_bin, tmp_path):
    p, _ = rllvm_ll(rllvm_bin, tmp_path, """
define double @f(double %x) {
entry:
  %r = call double asm sideeffect "nop", "=r,0"(double %x)
  ret double %r
}
""")
    assert p.returncode == EXIT_UNSUPPORTED, p.stderr
