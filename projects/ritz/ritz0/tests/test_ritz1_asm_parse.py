"""ritz1 lexes and parses `asm` blocks (LANGUAGE_SPEC §18.6, LARB R50, AGAST #3394).

Step 1 of #1619 for ritz1: the front end only.

* `asm` is a keyword, so `let asm = 1` is refused where ritz0 refuses it.
* An `asm` body is text, not Ritz: each indented line reaches the parser
  whole (lexer.ritz asm body mode), so `$3`, `%rcx`, `(%rax)`, a quote
  and `{{`/`}}` all survive.  A `#` comment is dropped.
* The clauses, `(in|out|inout NAME (: REG)? | clobber REG, ...)`, parse.
* Every §18.6 error that needs no types is reported, located (ERRORS).

Lowering is step 2 (#3395, test_ritz1_asm_lower.py): each ACCEPT row now
compiles to IR, so a block that failed to parse, or a check that fired on a
good block, fails the row.

ritz0 is a column of both (AGAST #3396); the errors that need types are in
test_ritz1_asm_lower.py.
"""

import pytest

from test_cryptosec_ritz1_shapes import _emit
from test_ref_into_value import _assert_refused

pytestmark = pytest.mark.integration

COMPILERS = ["ritz1", "ritz1_selfhosted"]

MAIN = "\npub fn main() -> i32\n    0\n"

# Blocks that parse and pass every front-end check, and so compile.
ACCEPT = {
    # Every kind of text the Ritz lexer would refuse or mangle, a comment,
    # a blank line, a deeper line, a numeric label, and statements after
    # the block at both its own depth and the enclosing one.
    "text": """\
fn wipe(ptr: *u8, len: i64, c: bool) -> i64
    if c
        asm x86_64:
            nopl ({ptr})      # a compiler barrier: { is not an operand here
            movq $3, %rcx

                1: decq %rcx
            jnz 1b
            movb $'"', %al
            movq {{literal}}, %rax
        let k: i64 = 1
    else
        return 2
    len
"""
    + MAIN,
    # §18.6's syscall example: every clause form.
    "clauses": """\
fn write1(fd: i64, buf: *u8, n: i64) -> i64
    var ret: i64 = 1
    asm x86_64 (inout ret: rax, in fd: rdi, in buf: rsi, in n: rdx, clobber rcx, clobber r11):
        syscall
    return ret
"""
    + MAIN,
    # An unpinned clause operand named in the text; a list over two lines.
    "unpinned": """\
fn inb(port: u16) -> u8
    var result: u8 = 0
    asm x86_64 (out result,
                 in port: rdx):
        inb %dx, %al
        movb %al, {result}
    return result
"""
    + MAIN,
    # A [[naked]] fn of bare asm; the file's last line has no newline.
    "naked_eof": MAIN
    + """
[[naked]]
fn naked_add(a: i32, b: i32) -> i32
    asm x86_64:
        movl %edi, %eax
        addl %esi, %eax
        retq""",
}

# One error each, located at `^`.
ERRORS = {
    "keyword": ("fn f()\n    let ^asm = 1\n", "unexpected 'asm'"),
    "arch": (
        "fn f()\n    asm ^arm64:\n        nop\n",
        "unknown asm architecture 'arm64' (known: x86_64)",
    ),
    "clause_word": (
        "fn f(x: i64)\n    asm x86_64 (^frob x):\n        nop {x}\n",
        "unknown asm clause 'frob' (in, out, inout or clobber)",
    ),
    "two_clauses": (
        "fn f(x: i64)\n    var y: i64 = x\n    asm x86_64 (in y, out ^y):\n        nop {y}\n",
        "'y' is named in two asm clauses",
    ),
    "not_in_text": (
        "fn f(x: i64)\n    asm x86_64 (in ^x):\n        nop\n",
        "asm operand 'x' is in a clause but not in the text: write {name} or pin it to a register",
    ),
    "pinned_twice": (
        "fn f(x: i64, y: i64)\n    asm x86_64 (in x: rax, in y: ^rax):\n        nop\n",
        "asm register 'rax' is pinned twice",
    ),
    "not_gpr": (
        "fn f(x: i64)\n    asm x86_64 (in x: ^xmm0):\n        nop\n",
        "'xmm0' is not a general register (rax, rbx, rcx, rdx, rsi, rdi, r8-r15)",
    ),
    "pin_rsp": (
        "fn f(x: i64)\n    asm x86_64 (in x: ^rsp):\n        nop\n",
        "asm can't pin or clobber 'rsp'",
    ),
    "clobber_rbp": (
        "fn f()\n    asm x86_64 (clobber ^rbp):\n        nop\n",
        "asm can't pin or clobber 'rbp'",
    ),
    "clobber_pinned": (
        "fn f()\n    asm x86_64 (clobber r11: ^rax):\n        nop\n",
        "'clobber' takes one register, not 'r11: ...'",
    ),
    "brace_open": (
        "fn f(x: i64)\n    asm x86_64:\n        movq ^{x, %rax\n",
        "'{' in asm is not closed (write '{{' for a literal '{')",
    ),
    "brace_non_name": (
        "fn f(x: i64)\n    asm x86_64:\n        movq ^{x + 1}, %rax\n",
        "'{' in asm must be followed by a name and '}' (write '{{' for a literal '{')",
    ),
    # On a deeper line: its extra indentation is dropped, so it starts the text.
    "named_label": (
        "fn f()\n    asm x86_64:\n        nop\n            ^again: jmp again\n",
        "named label 'again' in asm: use a numeric local label (1:, jumped to as 1b or 1f)",
    ),
    "naked_clause": (
        "[[naked]]\nfn f(x: i64)\n    asm x86_64 (^in x: rdi):\n        retq\n",
        "an asm block in a [[naked]] fn takes no clauses",
    ),
    "naked_name": (
        "[[naked]]\nfn f(x: i64)\n    asm x86_64:\n        movq ^{x}, %rax\n",
        "an asm block in a [[naked]] fn takes no {name}: 'x' has no frame to live in",
    ),
    "naked_body": (
        "[[naked]]\nfn f() -> i32\n    ^0\n",
        "a [[naked]] fn body may contain only asm blocks",
    ),
}


@pytest.mark.parametrize("compiler", ["ritz0"] + COMPILERS)
@pytest.mark.parametrize("case", sorted(ACCEPT))
def test_asm_block_parses(tmp_path, compiler, case):
    path = tmp_path / "main.ritz"
    path.write_text(ACCEPT[case])
    comp = _emit(compiler, path, tmp_path / "main.ll", tmp_path)
    assert comp.returncode == 0, f"{compiler} refused {case}:\n{comp.stdout + comp.stderr}"


@pytest.mark.parametrize("compiler", ["ritz0"] + COMPILERS)
@pytest.mark.parametrize("case", sorted(ERRORS))
def test_asm_front_end_error(tmp_path, compiler, case):
    marked, message = ERRORS[case]
    _assert_refused(compiler, tmp_path, case, marked + MAIN, message)
