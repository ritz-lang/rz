"""Tests for inline assembly parsing and emission."""

import pytest
from lexer import tokenize
from parser import Parser
from tokens import TokenType
import ritz_ast as rast
from ritz0_inproc import run_ritz0


class TestAsmLexer:
    """Test asm keyword tokenization."""

    def test_asm_keyword(self):
        """Test that 'asm' is recognized as a keyword."""
        tokens = tokenize("asm x86_64:")
        assert tokens[0].type == TokenType.ASM
        assert tokens[1].type == TokenType.IDENT
        assert tokens[1].value == "x86_64"
        assert tokens[2].type == TokenType.COLON


def _asm(source):
    """The first statement of the first fn in `source`, an AsmStmt."""
    module = Parser(tokenize(source)).parse_module()
    stmt = module.items[0].body.stmts[0]
    assert isinstance(stmt, rast.AsmStmt)
    return stmt


class TestAsmParser:
    """An asm body is raw text (LANGUAGE_SPEC §18.6, AGAST #3396)."""

    def test_lines_are_text(self):
        """Each line reaches the template as written: `$`, `%`, parentheses
        and spacing are not re-tokenised, and `$` stays `$`."""
        stmt = _asm("""
fn f(ptr: *u8)
    asm x86_64:
        movq   $3, %rcx
        nopl ({ptr})
        movb $'"', %al
""")
        assert stmt.arch == "x86_64"
        assert stmt.template == "movq   $3, %rcx\nnopl ({ptr})\nmovb $'\"', %al"

    def test_comments_and_indentation_dropped(self):
        """`#` to the end of the line is a comment; deeper indentation and
        blank lines are dropped; the block ends at the enclosing depth."""
        stmt = _asm("""
fn f()
    asm x86_64:
        nop      # a comment with {braces}

            1: decq %rcx
        jnz 1b
    let k: i64 = 1
""")
        assert stmt.template == "nop\n1: decq %rcx\njnz 1b"
        assert stmt.operands == []

    def test_text_operands_are_inputs(self):
        """Every `{name}` no clause names is an input: nothing is guessed
        from mnemonics, and `{{`/`}}` are not operands."""
        stmt = _asm("""
fn f(port: u16, result: u8)
    asm x86_64:
        movw {port}, %dx
        movb %al, {result}
        movq {{literal}}, %rax
""")
        assert [(o.name, o.direction) for o in stmt.operands] == [("port", "in"), ("result", "in")]

    def test_clauses(self):
        """§18.6's syscall example, its clause list over two lines."""
        stmt = _asm("""
fn write1(ret: i64, fd: i64, buf: *u8, n: i64)
    asm x86_64 (inout ret: rax, in fd: rdi,
                in buf: rsi, in n: rdx, clobber rcx, clobber r11):
        syscall
""")
        assert [(o.name, o.direction, o.reg) for o in stmt.operands] == [
            ("ret", "inout", "rax"), ("fd", "in", "rdi"), ("buf", "in", "rsi"), ("n", "in", "rdx")]
        assert stmt.clobbers == ["rcx", "r11"]

    def test_volatile_default(self):
        assert _asm("fn f()\n    asm x86_64:\n        hlt\n").volatile is True


def _ir(tmp_path, source):
    """ritz0's IR for `source`."""
    src = tmp_path / "main.ritz"
    src.write_text(source + "\npub fn main() -> i32\n    0\n")
    ll = tmp_path / "main.ll"
    result = run_ritz0([str(src), "-o", str(ll)], cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    return ll.read_text()


@pytest.mark.integration
class TestAsmLowering:
    """§18.6 "Lowering" for ritz0 alone; the shapes both compilers share are
    test_ritz1_asm_lower.py's IR rows."""

    TAIL = "~{memory},~{dirflag},~{fpsr},~{flags}"

    def test_out_template_and_text_clobbers(self, tmp_path):
        """`out` is `=&r` and returns its type; `{name}` is `${N}` (outputs
        numbered first; `${N}` only before a digit), `$` is `$$`; registers the text names are
        clobbered as their 64-bit register, in encoding order."""
        ir = _ir(tmp_path, """
fn inb(port: u16) -> u8
    var result: u8 = 0
    asm x86_64 (out result):
        movw {port}, %dx
        inb %dx, %al
        movb %al, {result}
        movq $1, %r11
    return result
""")
        assert ('call i8 asm sideeffect "movw $1, %dx\\0Ainb %dx, %al\\0Amovb %al, $0'
                '\\0Amovq $$1, %r11", "=&r,r,~{rax},~{rdx},~{r11},' + self.TAIL + '"') in ir
        assert "store i8" in ir

    def test_wrong_target(self, tmp_path):
        """An `asm x86_64` block on another target is refused at the name."""
        src = tmp_path / "main.ritz"
        src.write_text("fn f()\n    asm x86_64:\n        nop\n")
        result = run_ritz0([str(src), "--target", "aarch64-unknown-linux-gnu",
                            "-o", str(tmp_path / "main.ll")], cwd=str(tmp_path))
        assert result.returncode != 0
        assert ("main.ritz:2:9: asm block is for x86_64, but the target is "
                "aarch64-unknown-linux-gnu") in result.stdout + result.stderr


@pytest.mark.integration
class TestNestedArrayAddressing:
    """Test nested array indexing and address-of operations."""

    def test_nested_array_addr(self):
        """Test taking address of nested array element: @arr[i][j]."""
        import tempfile
        import os

        source = """
var stacks: [4][16]u8

fn test_addr() -> i32
    let ptr: *u8 = @stacks[2][5]
    *ptr = 42
    if stacks[2][5] == 42
        0
    else
        1

fn main() -> i32
    test_addr()
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ritz', delete=False) as f:
            f.write(source)
            src_path = f.name

        try:
            ll_path = src_path.replace('.ritz', '.ll')
            ritz0_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_root = os.path.dirname(ritz0_dir)
            result = run_ritz0([src_path, '-o', ll_path], cwd=project_root)
            assert result.returncode == 0, f"Compilation failed: {result.stderr}"

            # Check the generated IR uses proper GEP for nested access
            with open(ll_path) as f:
                ir = f.read()
            # Should have getelementptr for nested array access
            assert 'getelementptr' in ir

        finally:
            os.unlink(src_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)

    def test_nested_array_read(self):
        """Test reading from nested array: arr[i][j]."""
        import tempfile
        import os

        source = """
var matrix: [3][3]i32

fn init_matrix()
    matrix[0][0] = 1
    matrix[1][1] = 5
    matrix[2][2] = 9

fn sum_diagonal() -> i32
    matrix[0][0] + matrix[1][1] + matrix[2][2]

fn main() -> i32
    init_matrix()
    if sum_diagonal() == 15
        0
    else
        1
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ritz', delete=False) as f:
            f.write(source)
            src_path = f.name

        try:
            ll_path = src_path.replace('.ritz', '.ll')
            ritz0_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            project_root = os.path.dirname(ritz0_dir)
            result = run_ritz0([src_path, '-o', ll_path], cwd=project_root)
            assert result.returncode == 0, f"Compilation failed: {result.stderr}"

        finally:
            os.unlink(src_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)
