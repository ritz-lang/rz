"""ritz1 lowers `asm` blocks to LLVM inline asm (LANGUAGE_SPEC §18.6, LARB R50, AGAST #3395).

Step 2 of #1619 for ritz1; #3394 parsed and checked the blocks.

* RUN: each program's exit code is what its block computes, so an operand
  that reaches the wrong register, the wrong width, the wrong number or the
  wrong place afterwards changes the answer, or doesn't assemble.  The
  expected code is written out; ritz0 runs every row too (AGAST #3396).
* IR: the shapes §18.6 fixes: the template's escaping, the constraint list
  and the clobbers, `[[naked]]`'s define.
* ERRORS: the typed errors §18.6 lists, each located at the operand.

test_asm.ritz's no-clause blocks run in the regression matrix on every
compiler. cryptosec's `mem_zero` barrier ran them in test_cryptosec_ritz1_shapes.py and
test_cryptosec_mem_zero_o2.py until #1864 replaced it with secure_zero.
"""

import re

import pytest

import subprocess

from test_cryptosec_ritz1_shapes import RITZ_START, _emit, _run
from test_ref_into_value import _assert_refused

pytestmark = [pytest.mark.integration, pytest.mark.batched]

COMPILERS = ["ritz0", "ritz1", "ritz1_selfhosted"]

# Rows a compiler doesn't pass yet: (row, compiler) -> AGAST ticket.
GAPS = {
    # ritz0 emits its naked fns its own way (emitter_llvmlite.py).
    ("naked", "ritz0"): None,
}

# name: (program, exit code)
RUN = {
    # §18.6's inb, with a register a user program may read: `out` of a u8,
    # a u16 input as `%dx`-sized, a text-named register clobbered.
    "out_u8_from_u16": ("""\
fn low(port: u16) -> u8
    var result: u8 = 0
    asm x86_64 (out result):
        movw {port}, %dx
        movb %dl, {result}
    return result

pub fn main() -> i32
    low(0x1234) as i32
""", 0x34),
    # §18.6's write1: pinned inout and ins, clobbers; the syscall's result
    # (bytes written) comes back in `ret`.
    "syscall_write1": ("""\
fn write1(fd: i64, buf: *u8, n: i64) -> i64
    var ret: i64 = 1
    asm x86_64 (inout ret: rax, in fd: rdi, in buf: rsi, in n: rdx, clobber rcx, clobber r11):
        syscall
    return ret

pub fn main() -> i32
    write1(1, c"hey", 3) as i32
""", 3),
    # An unpinned inout: read, then written, in one register of its width.
    "inout_i32": ("""\
pub fn main() -> i32
    var x: i32 = 37
    asm x86_64 (inout x):
        addl $5, {x}
    x
""", 42),
    # An inout pinned to a register the text names (#3425): the register is
    # the output, not a clobber, so its tie (the input value) survives.
    # Out of line at -O2 (test_asm_block_runs_o2) is where the tie was lost.
    "inout_pinned_text_named": ("""\
[[noinline]]
fn bump(x: i64) -> i64
    var r: i64 = x
    asm x86_64 (inout r: rax):
        addq $1, %rax
    r

pub fn main() -> i32
    bump(41) as i32
""", 42),
    # Two outputs: a literal struct, each field stored to its own place.
    "two_outputs": ("""\
pub fn main() -> i32
    var a: i64 = 0
    var b: i64 = 0
    asm x86_64 (out a, out b):
        movq $3, {a}
        movq $4, {b}
    (a * 10 + b) as i32
""", 34),
    # Inputs, an inout and an out together: numbering is outputs first.
    "mixed_numbering": ("""\
pub fn main() -> i32
    let k: i64 = 100
    var acc: i64 = 5
    var res: i64 = 0
    asm x86_64 (inout acc, out res):
        addq {k}, {acc}
        movq {acc}, {res}
        addq $1, {res}
    (res - acc) as i32 + (acc - 100) as i32
""", 6),
    # A pointer in and a pointer out; the block writes memory through one.
    "pointers": ("""\
pub fn main() -> i32
    var cell: i64 = 0
    let p: *i64 = @cell
    var q: *i64 = null
    asm x86_64 (out q):
        movq $9, ({p})
        movq {p}, {q}
    *q as i32
""", 9),
    # A global `var` written by `out`, and a const read as an input.
    "global_out_const_in": ("""\
const SEVEN: i64 = 7
var g: i64 = 0

pub fn main() -> i32
    asm x86_64 (out g):
        movq {SEVEN}, {g}
        addq $1, {g}
    g as i32
""", 8),
    # A numeric local label and `{{`/`}}`-free text with literal `$`s.
    "labels_and_dollars": ("""\
pub fn main() -> i32
    var n: i64 = 0
    asm x86_64 (out n):
        movq $3, %rcx
        xorq {n}, {n}
        1:
        addq $2, {n}
        decq %rcx
        jnz 1b
    n as i32
""", 6),
    # No clause: `{r}` is an input whatever the mnemonic says.  ritz0 used to
    # guess that `movq ..., {r}` writes `r` (#3396); direction is declared.
    "unsniffed": ("""\
pub fn main() -> i32
    var r: i64 = 7
    asm x86_64:
        movq $42, {r}
    r as i32
""", 7),
    # [[naked]]: no frame, the args in the convention's registers, its own ret.
    "naked": ("""\
[[naked]]
fn naked_add(a: i32, b: i32) -> i32
    asm x86_64:
        movl %edi, %eax
        addl %esi, %eax
        retq

[[naked]]
fn naked_42() -> i32
    asm x86_64:
        movl $42, %eax
        retq

pub fn main() -> i32
    naked_add(10, 32) - naked_42() + 7
""", 7),
}

# name: (program, regexes the emitted IR must match)
IR = {
    # cryptosec's barrier: ritz0's shape plus the dirflag/fpsr/flags §18.6 adds.
    "barrier": ("""\
fn wipe(ptr: *u8)
    asm x86_64:
        nopl ({ptr})

pub fn main() -> i32
    0
""", [r'call void asm sideeffect "nopl \(\$0\)", "r,~\{memory\},~\{dirflag\},~\{fpsr\},~\{flags\}"\(ptr %[.\w]+\)']),
    # `$` -> `$$`, lines joined by \0A, braces undoubled, `"` escaped, every
    # text register clobbered as its 64-bit name.
    "template": ("""\
pub fn main() -> i32
    asm x86_64:
        movq $3, %rcx
        movb $'"', %al
        xorl %r9d, %r9d
        # a {{brace}} pair
        nop {{}}
    0
""", [r'asm sideeffect "movq \$\$3, %rcx\\0Amovb \$\$\'\\22\', %al\\0Axorl %r9d, %r9d\\0Anop \{\}", '
      r'"~\{rax\},~\{rcx\},~\{r9\},~\{memory\},~\{dirflag\},~\{fpsr\},~\{flags\}"\(\)']),
    # outputs `=&r` / `={reg}`, inputs `r` / `{reg}`, an inout tied by number;
    # a {name} followed by a digit is `${N}`.
    "constraints": ("""\
fn f(fd: i64, x: i32) -> i64
    var ret: i64 = 1
    var y: i32 = x
    asm x86_64 (inout ret: rax, out y, in fd: rdi, clobber r11):
        movl {x}, {y}
        leaq {x}1, %r8
    ret + y as i64

pub fn main() -> i32
    0
""", [r'= call \{ i64, i32 \} asm sideeffect "movl \$4, \$1\\0Aleaq \$\{4\}1, %r8", '
      r'"=\{rax\},=&r,0,\{rdi\},r,~\{r8\},~\{r11\},~\{memory\},~\{dirflag\},~\{fpsr\},~\{flags\}"'
      r'\(i64 %[.\w]+, i64 %[.\w]+, i32 %[.\w]+\)',
      r'extractvalue \{ i64, i32 \} %[.\w]+, 0',
      r'extractvalue \{ i64, i32 \} %[.\w]+, 1']),
    # A register pinned to an output is not also clobbered, though the text
    # names it (#3425): `={rax},0,~{rax}` lets LLVM drop the tie.  One pinned
    # to an input only is still clobbered.
    "pinned_output_not_clobbered": ("""\
fn f(x: i64, y: i64) -> i64
    var r: i64 = x
    var o: i64 = 0
    asm x86_64 (inout r: rax, out o: rdx, in y: rdi):
        addq %rdi, %rax
        movq %rax, %rdx
        movl %ecx, %ecx
    r + o

pub fn main() -> i32
    0
""", [r'"=\{rax\},=\{rdx\},0,\{rdi\},~\{rcx\},~\{rdi\},~\{memory\},~\{dirflag\},~\{fpsr\},~\{flags\}"']),
    # The stack registers the text names are never clobbers.
    "stack_regs": ("""\
pub fn main() -> i32
    asm x86_64:
        movq %rsp, %rax
        movl %ebp, %ecx
    0
""", [r'"movq %rsp, %rax\\0Amovl %ebp, %ecx", "~\{rax\},~\{rcx\},~\{memory\},'
      r'~\{dirflag\},~\{fpsr\},~\{flags\}"']),
    # [[naked]]: no prologue, no frame, the blocks then `unreachable`.
    "naked": ("""\
[[naked]]
fn bare(a: i64) -> i64
    asm x86_64:
        movq %rdi, %rax
    asm x86_64:
        retq

pub fn main() -> i32
    0
""", [r'define internal i64 @bare\(i64 %a\.arg\) naked noinline \{\nentry:\n'
      r'  call void asm sideeffect "movq %rdi, %rax", "~\{rax\},~\{rdi\},~\{memory\},~\{dirflag\},~\{fpsr\},~\{flags\}"\(\)\n'
      r'  call void asm sideeffect "retq", "~\{memory\},~\{dirflag\},~\{fpsr\},~\{flags\}"\(\)\n'
      r'  unreachable\n\}']),
}

MAIN = "\npub fn main() -> i32\n    0\n"

# One error each, located at `^` (§18.6 "Errors": the ones that need types).
ERRORS = {
    "not_in_scope": (
        "fn f()\n    asm x86_64:\n        movq {^nope}, %rax\n",
        "asm operand 'nope' is not a local, a parameter or a global",
    ),
    "not_in_scope_clause": (
        "fn f()\n    asm x86_64 (out ^nope: rax):\n        nop\n",
        "asm operand 'nope' is not a local, a parameter or a global",
    ),
    "bool": (
        "fn f(b: bool)\n    asm x86_64:\n        movq {^b}, %rax\n",
        "asm operand 'b' must be an integer or a pointer",
    ),
    "struct": (
        "struct P\n    x: i64\n\nfn f()\n    var p = P { x: 1 }\n    asm x86_64 (in ^p: rdi):\n        nop\n",
        "asm operand 'p' must be an integer or a pointer",
    ),
    "float": (
        "fn f(x: f64)\n    asm x86_64:\n        movq {^x}, %rax\n",
        "asm operand 'x' must be an integer or a pointer",
    ),
    "out_let": (
        "fn f() -> i64\n    let x: i64 = 1\n    asm x86_64 (out ^x):\n        movq $2, {x}\n    x\n",
        "asm 'out' operand 'x' is a `let` binding, not an assignable place: declare it `var`",
    ),
    "inout_const": (
        "const K: i64 = 1\n\nfn f()\n    asm x86_64 (inout ^K: rax):\n        nop\n",
        "asm 'inout' operand 'K' is a const, not an assignable place",
    ),
    # §13.5: an out operand is an assignment of its place.
    "out_borrowed": (
        "fn f() -> i64\n    var x: i64 = 1\n    let r: @i64 = @x\n    asm x86_64 (out ^x):\n"
        "        movq $2, {x}\n    *r\n",
        "cannot assign to `x` - `x` is already borrowed as immutable",
    ),
}


def _as_ritz1_prints(text):
    """ritz0's IR as ritz1 prints the same thing: llvmlite quotes value
    names (`%".5"`), writes `{i64, i32}` without inner spaces and keeps
    typed pointers (`i8*`)."""
    text = re.sub(r'%"([.\w]+)"', r'%\1', text)
    text = re.sub(r'\{((?:i\d+|ptr)(?:, (?:i\d+|ptr))*)\}', r'{ \1 }', text)
    return re.sub(r'\bi\d+\*', 'ptr', text)


def _params(table):
    for compiler in COMPILERS:
        for name in sorted(table):
            gap = GAPS.get((name, compiler), 0)
            if gap is None and table is IR:
                continue
            marks = [pytest.mark.xfail(strict=True, reason=f"AGAST #{gap}")] if gap else []
            yield pytest.param(compiler, name, id=f"{compiler}-{name}", marks=marks)


@pytest.mark.parametrize("compiler,name", list(_params(RUN)))
def test_asm_block_runs(compiler, tmp_path, name):
    src, want = RUN[name]
    assert _run(compiler, tmp_path, name, src) == want


# Rows whose miscompile only shows once LLVM optimises: also linked at -O2.
RUN_O2 = ["inout_pinned_text_named"]


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("name", RUN_O2)
def test_asm_block_runs_o2(compiler, tmp_path, name):
    src, want = RUN[name]
    path = tmp_path / "main.ritz"
    path.write_text(src)
    ll = tmp_path / "main.ll"
    comp = _emit(compiler, path, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    exe = tmp_path / "main"
    # ritz0's IR defines its own `_start`; ritz1's links the runtime's.
    start = [] if compiler == "ritz0" else [str(RITZ_START)]
    link = subprocess.run(["clang", "-O2", "-Wno-override-module", *start, str(ll), "-o", str(exe),
                           "-nostdlib", "-no-pie"], check=False, capture_output=True, text=True, timeout=300)
    assert link.returncode == 0, link.stderr[-2000:]
    assert subprocess.run([str(exe)], check=False, timeout=60).returncode == want


@pytest.mark.parametrize("compiler,name", list(_params(IR)))
def test_asm_block_ir(compiler, tmp_path, name):
    src, patterns = IR[name]
    path = tmp_path / "main.ritz"
    path.write_text(src)
    ll = tmp_path / "main.ll"
    comp = _emit(compiler, path, ll, tmp_path)
    assert comp.returncode == 0 and ll.exists(), comp.stdout + comp.stderr
    text = ll.read_text()
    if compiler == "ritz0":
        text = _as_ritz1_prints(text)
    for pat in patterns:
        assert re.search(pat, text), f"{compiler}: {name}: no /{pat}/ in\n{text}"


@pytest.mark.parametrize("compiler", COMPILERS)
@pytest.mark.parametrize("case", sorted(ERRORS))
def test_asm_typed_error(tmp_path, compiler, case):
    marked, message = ERRORS[case]
    _assert_refused(compiler, tmp_path, case, marked + MAIN, message)
