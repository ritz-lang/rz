"""Tests for inline assembly parsing and emission."""

import pytest
from lexer import tokenize
from parser import Parser
from tokens import TokenType
import ritz_ast as rast


class TestAsmLexer:
    """Test asm keyword tokenization."""

    def test_asm_keyword(self):
        """Test that 'asm' is recognized as a keyword."""
        tokens = tokenize("asm x86_64:")
        assert tokens[0].type == TokenType.ASM
        assert tokens[1].type == TokenType.IDENT
        assert tokens[1].value == "x86_64"
        assert tokens[2].type == TokenType.COLON


class TestAsmParser:
    """Test asm statement parsing."""

    def test_simple_asm(self):
        """Test parsing a simple asm block."""
        source = """
fn test()
    asm x86_64:
        nop
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn = module.items[0]
        assert isinstance(fn, rast.FnDef)
        assert len(fn.body.stmts) == 1

        asm_stmt = fn.body.stmts[0]
        assert isinstance(asm_stmt, rast.AsmStmt)
        assert asm_stmt.arch == "x86_64"
        assert "nop" in asm_stmt.template

    def test_asm_with_operands(self):
        """Test parsing asm with {operand} placeholders."""
        source = """
fn outb(port: u16, value: u8)
    asm x86_64:
        mov dx, {port}
        mov al, {value}
        out dx, al
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn = module.items[0]
        asm_stmt = fn.body.stmts[0]
        assert isinstance(asm_stmt, rast.AsmStmt)
        assert asm_stmt.arch == "x86_64"
        assert "{port}" in asm_stmt.template
        assert "{value}" in asm_stmt.template
        assert len(asm_stmt.operands) == 2

        # Check operands
        op_names = [op.name for op in asm_stmt.operands]
        assert "port" in op_names
        assert "value" in op_names

    def test_asm_multiline(self):
        """Test parsing multiline asm blocks."""
        source = """
fn cpuid()
    asm x86_64:
        push rbx
        mov eax, 0
        cpuid
        pop rbx
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn = module.items[0]
        asm_stmt = fn.body.stmts[0]
        assert isinstance(asm_stmt, rast.AsmStmt)

        # Template should contain all instructions
        assert "push" in asm_stmt.template
        assert "cpuid" in asm_stmt.template
        assert "pop" in asm_stmt.template

    def test_asm_aarch64(self):
        """Test parsing ARM64 asm."""
        source = """
fn nop()
    asm aarch64:
        nop
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn = module.items[0]
        asm_stmt = fn.body.stmts[0]
        assert asm_stmt.arch == "aarch64"

    def test_asm_volatile_default(self):
        """Test that asm is volatile by default."""
        source = """
fn test()
    asm x86_64:
        hlt
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn = module.items[0]
        asm_stmt = fn.body.stmts[0]
        assert asm_stmt.volatile == True

    def test_asm_local_labels(self):
        """Test parsing asm with local labels (e.g., .spin, .loop)."""
        source = """
fn halt()
    asm x86_64:
        cli
        .spin:
        hlt
        jmp .spin
"""
        tokens = tokenize(source)
        parser = Parser(tokens)
        module = parser.parse_module()

        fn = module.items[0]
        asm_stmt = fn.body.stmts[0]
        assert isinstance(asm_stmt, rast.AsmStmt)

        # Labels should be preserved without extra spaces
        assert ".spin:" in asm_stmt.template
        assert "jmp .spin" in asm_stmt.template
        # Should NOT have "jmp . spin" (with space after dot)
        assert ". spin" not in asm_stmt.template


class TestAsmIntegration:
    """Integration tests for asm compilation."""

    def test_asm_compiles_to_llvm(self):
        """Test that asm statements produce valid LLVM IR."""
        import subprocess
        import tempfile
        import os

        source = """
fn outb(port: u16, value: u8)
    asm x86_64:
        mov dx, {port}
        out dx, al

fn main() -> i32
    outb(0x3F8, 65)
    0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ritz', delete=False) as f:
            f.write(source)
            src_path = f.name

        try:
            ll_path = src_path.replace('.ritz', '.ll')
            # Get the directory containing this test file (ritz0/)
            ritz0_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(ritz0_dir)
            result = subprocess.run(
                ['python3', 'ritz0/ritz0.py', src_path, '-o', ll_path],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            assert result.returncode == 0, f"Compilation failed: {result.stderr}"

            # Check the generated IR contains inline asm
            with open(ll_path) as f:
                ir = f.read()
            assert 'asm sideeffect' in ir
            assert 'mov dx' in ir

        finally:
            os.unlink(src_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestAsmOutputOperands:
    """Test asm output operand detection and code generation."""

    def test_asm_output_operand(self):
        """Test that asm output operands are properly detected and stored back."""
        import subprocess
        import tempfile
        import os

        source = """
fn inb(port: u16) -> u8
    var result: u8 = 0
    asm x86_64:
        movw {port}, %dx
        inb %dx, %al
        movb %al, {result}
    return result

fn main() -> i32
    let x: u8 = inb(0x3F8)
    0
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ritz', delete=False) as f:
            f.write(source)
            src_path = f.name

        try:
            ll_path = src_path.replace('.ritz', '.ll')
            ritz0_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(ritz0_dir)
            result = subprocess.run(
                ['python3', 'ritz0/ritz0.py', src_path, '-o', ll_path],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            assert result.returncode == 0, f"Compilation failed: {result.stderr}"

            # Check the generated IR
            with open(ll_path) as f:
                ir = f.read()
            # Should have an output constraint (=r)
            assert '=r' in ir, "Missing output constraint"
            # The asm should return a value (call i8 asm)
            assert 'call i8 asm' in ir, "Asm should return i8 for output operand"
            # Should store the result back
            assert 'store i8' in ir, "Missing store of output value"

        finally:
            os.unlink(src_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)


class TestNestedArrayAddressing:
    """Test nested array indexing and address-of operations."""

    def test_nested_array_addr(self):
        """Test taking address of nested array element: @arr[i][j]."""
        import subprocess
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
            ritz0_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(ritz0_dir)
            result = subprocess.run(
                ['python3', 'ritz0/ritz0.py', src_path, '-o', ll_path],
                capture_output=True,
                text=True,
                cwd=project_root
            )
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
        import subprocess
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
            ritz0_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(ritz0_dir)
            result = subprocess.run(
                ['python3', 'ritz0/ritz0.py', src_path, '-o', ll_path],
                capture_output=True,
                text=True,
                cwd=project_root
            )
            assert result.returncode == 0, f"Compilation failed: {result.stderr}"

        finally:
            os.unlink(src_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)
