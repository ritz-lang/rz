"""Tests for inline assembly parsing and emission."""

import pytest
from lexer import tokenize, set_reritz_mode
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
            result = subprocess.run(
                ['python3', 'ritz0/ritz0.py', src_path, '-o', ll_path],
                capture_output=True,
                text=True,
                cwd='/home/aaron/dev/ritz-lang/ritz-amd64'
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
