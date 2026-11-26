"""The IR parser: the closed subset round-trips, and every construct outside
it exits 2 naming the file, line and construct (DESIGN.md "LLVM IR subset").

Round trip: `rllvm-ir FILE.ll` prints the module it parsed. clang reads the
original and the printed text to its own canonical form, and the two must be
equal: nothing the parser kept is lost or changed. Printing is also a fixed
point. Metadata is skipped by the parser, so it is dropped from both sides.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from conftest import run

TESTS = Path(__file__).resolve().parent
FIXTURES = TESTS / "fixtures"
CORPUS = TESTS / "corpus"
CORPUS_FILES = sorted(p.relative_to(TESTS).as_posix() for p in CORPUS.rglob("*.ll"))
ROUND_TRIP = ["fixtures/subset.ll", *CORPUS_FILES]

HEAD = 'target triple = "x86_64-unknown-linux-gnu"\n'


def clang_canonical(path: Path, out: Path) -> str:
    subprocess.run(["clang", "-S", "-emit-llvm", "-Xclang", "-disable-llvm-passes",
                    "-Wno-override-module", str(path), "-o", str(out)],
                   check=True, capture_output=True, text=True, timeout=120)
    keep = []
    for line in out.read_text().splitlines():
        if line.startswith(("; ModuleID", "source_filename", "!")):
            continue
        keep.append(re.sub(r", ![\w.]+ !\d+", "", line))
    return "\n".join(keep)


def test_corpus_is_present():
    assert CORPUS_FILES, "no corpus .ll files under tests/corpus"


@pytest.mark.parametrize("rel", ROUND_TRIP)
def test_round_trip_matches_clang(rllvm_ir_bin, rel, tmp_path):
    src = TESTS / rel
    p = run([rllvm_ir_bin, str(src)])
    assert p.returncode == 0, p.stderr
    printed = tmp_path / "printed.ll"
    printed.write_text(p.stdout)
    want = clang_canonical(src, tmp_path / "want.ll")
    got = clang_canonical(printed, tmp_path / "got.ll")
    assert got == want
    again = run([rllvm_ir_bin, str(printed)])
    assert again.returncode == 0, again.stderr
    assert again.stdout == p.stdout, "printing is not a fixed point"


@pytest.mark.parametrize("rel", CORPUS_FILES)
def test_rllvm_parses_every_corpus_file(rllvm_bin, rel):
    p = run([rllvm_bin, "-c", str(TESTS / rel), "-o", "/dev/null"])
    assert p.returncode == 2, p
    assert "unsupported: lowering is not implemented" in p.stderr, p.stderr


def test_metadata_is_skipped(rllvm_ir_bin, tmp_path):
    src = tmp_path / "md.ll"
    src.write_text(HEAD + "define i32 @f() !dbg !3 {\nentry:\n"
                   "  %x = add i32 1, 2, !dbg !4\n  ret i32 %x, !dbg !4\n}\n"
                   "!llvm.module.flags = !{!0}\n!0 = !{i32 2, !\"Dwarf Version\", i32 4}\n"
                   "!3 = distinct !{}\n!4 = !{}\n")
    p = run([rllvm_ir_bin, str(src)])
    assert p.returncode == 0, p.stderr
    assert "!" not in p.stdout
    assert "%x = add i32 1, 2\n" in p.stdout


DECLS = "declare void @g()\n"


def fn(body: str, sig: str = "define void @f()") -> str:
    return f"{HEAD}{DECLS}{sig} {{\nentry:\n{body}\n  ret void\n}}\n"


# (module text, construct). The offending line carries `; <-`.
REJECT = {
    "switch": (fn("  switch i32 0, label %entry [ i32 1, label %entry ] ; <-"), "instruction 'switch'"),
    "invoke": (fn("  invoke void @g() to label %entry unwind label %entry ; <-"), "instruction 'invoke'"),
    "landingpad": (fn("  %l = landingpad { ptr, i32 } cleanup ; <-"), "instruction 'landingpad'"),
    "resume": (fn("  resume { ptr, i32 } undef ; <-"), "instruction 'resume'"),
    "indirectbr": (fn("  indirectbr ptr null, [label %entry] ; <-"), "instruction 'indirectbr'"),
    "catchswitch": (fn("  %c = catchswitch within none [label %entry] unwind to caller ; <-"), "instruction 'catchswitch'"),
    "frem": (fn("  %r = frem double 1.0, 2.0 ; <-"), "instruction 'frem'"),
    "fptoui": (fn("  %r = fptoui double 1.0 to i32 ; <-"), "instruction 'fptoui'"),
    "freeze": (fn("  %r = freeze i32 0 ; <-"), "instruction 'freeze'"),
    "va_arg": (fn("  %r = va_arg ptr null, i32 ; <-"), "instruction 'va_arg'"),
    "unknown instruction": (fn("  %r = frob i32 0 ; <-"), "instruction 'frob'"),
    "atomicrmw nand": (fn("  %r = atomicrmw nand ptr null, i64 1 seq_cst ; <-"), "atomicrmw 'nand'"),
    "atomicrmw max": (fn("  %r = atomicrmw max ptr null, i64 1 seq_cst ; <-"), "atomicrmw 'max'"),
    "atomicrmw acquire": (fn("  %r = atomicrmw add ptr null, i64 1 acquire ; <-"), "ordering 'acquire'"),
    "load monotonic": (fn("  %r = load atomic i64, ptr null monotonic, align 8 ; <-"), "ordering 'monotonic'"),
    "load atomic no align": (fn("  %r = load atomic i64, ptr null seq_cst ; <-"), "atomic load without an alignment"),
    "store release": (fn("  store atomic i64 0, ptr null release, align 8 ; <-"), "ordering 'release'"),
    "fence acquire": (fn("  fence acquire ; <-"), "ordering 'acquire'"),
    "cmpxchg failure": (fn("  %r = cmpxchg ptr null, i64 0, i64 1 seq_cst acquire ; <-"), "ordering 'acquire'"),
    "cmpxchg weak": (fn("  %r = cmpxchg weak ptr null, i64 0, i64 1 seq_cst seq_cst ; <-"), "cmpxchg 'weak'"),
    "syncscope": (fn('  fence syncscope("singlethread") seq_cst ; <-'), "syncscope"),
    "addrspace ptr": (fn("  %r = load i8, ptr addrspace(1) null ; <-"), "address space"),
    "addrspace typed": (fn("  %r = load i8, i8 addrspace(1)* null ; <-"), "address space"),
    "i128": (fn("  %r = add i128 0, 1 ; <-"), "type 'i128'"),
    "x86_fp80": (fn("  %r = fadd x86_fp80 0xK0, 0xK0 ; <-"), "type 'x86_fp80'"),
    "half": (fn("  %r = fadd half 0.0, 0.0 ; <-"), "type 'half'"),
    "i24": (fn("  %r = add i24 0, 1 ; <-"), "type 'i24'"),
    "float vector": (fn("  %r = fadd <4 x float> zeroinitializer, zeroinitializer ; <-"), "type '<4 x float>'"),
    "odd vector": (fn("  %r = add <2 x i32> zeroinitializer, zeroinitializer ; <-"), "type '<2 x i32>'"),
    "typed pointer": (fn("  %r = load i32, i32* null ; <-"), "typed pointer 'i32*'"),
    "opaque": (HEAD + "%T = type opaque ; <-\n", "type 'opaque'"),
    "win64cc define": (HEAD + "define win64cc void @f() { ; <-\nentry:\n  ret void\n}\n", "calling convention 'win64cc'"),
    "win64cc call": (fn("  call win64cc void @g() ; <-"), "calling convention 'win64cc'"),
    "fastcc": (HEAD + "declare fastcc void @f() ; <-\n", "calling convention 'fastcc'"),
    "memcpy": (HEAD + "declare void @llvm.memcpy.p0.p0.i64(ptr, ptr, i64, i1) ; <-\n", "intrinsic 'llvm.memcpy.p0.p0.i64'"),
    "memset": (HEAD + "declare void @llvm.memset.p0.i64(ptr, i8, i64, i1) ; <-\n", "intrinsic 'llvm.memset.p0.i64'"),
    "lifetime": (HEAD + "declare void @llvm.lifetime.start.p0(i64, ptr) ; <-\n", "intrinsic 'llvm.lifetime.start.p0'"),
    "dbg": (HEAD + "declare void @llvm.dbg.declare(metadata, metadata, metadata) ; <-\n", "intrinsic 'llvm.dbg.declare'"),
    "floor": (HEAD + "declare double @llvm.floor.f64(double) ; <-\n", "intrinsic 'llvm.floor.f64'"),
    "bswap.i8": (HEAD + "declare i8 @llvm.bswap.i8(i8) ; <-\n", "intrinsic 'llvm.bswap.i8'"),
    "ctpop.i128 name": (HEAD + "declare i64 @llvm.ctpop.i65(i64) ; <-\n", "intrinsic 'llvm.ctpop.i65'"),
    "undeclared intrinsic call": (fn("  call void @llvm.memset.p0.i64(ptr null, i8 0, i64 1, i1 false) ; <-"), "intrinsic 'llvm.memset.p0.i64'"),
    "x86 avx2": (HEAD + "declare <4 x i64> @llvm.x86.avx2.pshuf.b(<4 x i64>, <4 x i64>) ; <-\n", "intrinsic 'llvm.x86.avx2.pshuf.b'"),
    "target-features": (HEAD + 'define void @f() "target-features"="+sha,+avx2" { ; <-\nentry:\n  ret void\n}\n', "target-features '+avx2'"),
    "target-cpu": (HEAD + 'define void @f() "target-cpu"="skylake" { ; <-\nentry:\n  ret void\n}\n', "target-cpu 'skylake'"),
    "string attribute": (HEAD + 'define void @f() "frame-pointer"="all" { ; <-\nentry:\n  ret void\n}\n', "function attribute '\"frame-pointer\"'"),
    "optnone": (HEAD + "define void @f() optnone { ; <-\nentry:\n  ret void\n}\n", "function attribute 'optnone'"),
    "attribute group": (HEAD + "define void @f() #0 { ; <-\nentry:\n  ret void\n}\n", "attribute group '#0'"),
    "noalias param": (HEAD + "declare void @f(ptr noalias) ; <-\n", "parameter attribute 'noalias'"),
    "zeroext param": (HEAD + "declare void @f(i8 zeroext) ; <-\n", "parameter attribute 'zeroext'"),
    "noundef ret": (HEAD + "declare noundef i32 @f() ; <-\n", "return attribute 'noundef'"),
    "inbounds": (fn("  %r = getelementptr inbounds i8, ptr null, i64 1 ; <-"), "getelementptr 'inbounds'"),
    "nsw": (fn("  %r = add nsw i32 0, 1 ; <-"), "flag 'nsw'"),
    "exact": (fn("  %r = udiv exact i32 4, 2 ; <-"), "flag 'exact'"),
    "fast-math": (fn("  %r = fadd fast double 1.0, 2.0 ; <-"), "flag 'fast'"),
    "tail call": (fn("  tail call void @g() ; <-"), "call marker 'tail'"),
    "poison": (fn("  %r = add i32 poison, 1 ; <-"), "constant 'poison'"),
    "blockaddress": (HEAD + "@p = global ptr blockaddress(@f, %bb) ; <-\n", "constant 'blockaddress'"),
    "thread_local": (HEAD + "@g = thread_local global i32 0 ; <-\n", "'thread_local'"),
    "section": (HEAD + '@g = global i32 0, section ".foo" ; <-\n', "global attribute 'section'"),
    "common": (HEAD + "@g = common global i32 0 ; <-\n", "linkage 'common'"),
    "extern_weak": (HEAD + "@g = extern_weak global i32 ; <-\n", "linkage 'extern_weak'"),
    "linkonce": (HEAD + "define linkonce void @f() { ; <-\nentry:\n  ret void\n}\n", "linkage 'linkonce'"),
    "alias": (HEAD + "@a = global i32 0\n@b = alias i32, ptr @a ; <-\n", "'alias'"),
    "comdat largest": (HEAD + "$c = comdat largest ; <-\n", "comdat 'largest'"),
    "comdat on global": (HEAD + "$g = comdat any\n@g = weak_odr global i32 0, comdat ; <-\n", "comdat on global '@g'"),
    "comdat other name": (HEAD + "$c = comdat any\ndefine linkonce_odr void @f() comdat($c) { ; <-\nentry:\n  ret void\n}\n", "comdat '$c' on function '@f'"),
    "comdat shared": (HEAD + "$f = comdat any\ndefine linkonce_odr void @f() comdat {\nentry:\n  ret void\n}\n"
                      "define linkonce_odr void @g() comdat($f) { ; <-\nentry:\n  ret void\n}\n", "comdat '$f' on function '@g'"),
    "256-bit define": (HEAD + "define void @f(<8 x i32> %v) { ; <-\nentry:\n  ret void\n}\n", "256-bit vector in the signature of '@f'"),
    "256-bit declare": (HEAD + "declare <4 x i64> @f() ; <-\n", "256-bit vector in the signature of '@f'"),
    "256-bit aggregate": (HEAD + "declare void @f({ i64, <8 x i32> }) ; <-\n", "256-bit vector in the signature of '@f'"),
    "256-bit indirect": (fn("  call void null(<8 x i32> zeroinitializer) ; <-"), "256-bit vector in an indirect call"),
    "module asm": (HEAD + 'module asm "nop" ; <-\n', "'module'"),
    "source_filename": (HEAD + 'source_filename = "x.c" ; <-\n', "'source_filename'"),
    "inline asm dialect": (fn('  call void asm sideeffect inteldialect "nop", ""() ; <-'), "inline asm 'inteldialect'"),
    "asm not sideeffect": (fn('  call void asm "nop", ""() ; <-'), "inline asm without 'sideeffect'"),
    "variadic define": (HEAD + "define void @f(...) { ; <-\nentry:\n  ret void\n}\n", "variadic definition '@f'"),
}


@pytest.mark.parametrize("name", sorted(REJECT))
def test_unsupported_construct_exits_2(rllvm_bin, tmp_path, name):
    text, what = REJECT[name]
    line = next(i for i, l in enumerate(text.splitlines(), 1) if "; <-" in l)
    src = tmp_path / "bad.ll"
    src.write_text(text)
    p = run([rllvm_bin, "-c", str(src), "-o", str(tmp_path / "bad.o")])
    assert p.returncode == 2, p
    assert f"rllvm: {src}:{line}: unsupported: {what}\n" == p.stderr


def test_rllvm_ir_rejects_like_rllvm(rllvm_ir_bin, tmp_path):
    src = tmp_path / "bad.ll"
    src.write_text(REJECT["switch"][0])
    p = run([rllvm_ir_bin, str(src)])
    assert p.returncode == 2, p
    assert f"{src}:5: unsupported: instruction 'switch'" in p.stderr


@pytest.mark.parametrize("text, message", [
    (HEAD + "define void @f() {\nentry:\n  ret void\n", "unexpected end of file"),
    (HEAD + "@g = global i32 ; <-\n", "expected a constant"),
    (HEAD + "define void @f() {\nentry:\n  %x = add i32 1 ; <-\n  ret void\n}\n", "expected ','"),
])
def test_malformed_ir_exits_1(rllvm_bin, tmp_path, text, message):
    src = tmp_path / "bad.ll"
    src.write_text(text)
    p = run([rllvm_bin, "-c", str(src)])
    assert p.returncode == 1, p
    assert message in p.stderr and f"{src}:" in p.stderr
