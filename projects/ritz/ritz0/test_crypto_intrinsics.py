"""Tests for AES-NI and SHA-NI hardware crypto intrinsics (ritz#119)."""

import os
import subprocess
import sys
import tempfile
import pytest
from pathlib import Path


def has_cpu_feature(feature: str) -> bool:
    """Check if CPU supports a given feature (Linux-specific)."""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('flags'):
                    return feature in line.split()
    except FileNotFoundError:
        pass
    return False


def compile_ritz_to_ll(source_path: str, output_ll: str) -> tuple[bool, str]:
    """Compile a .ritz file to LLVM IR (.ll)."""
    ritz0_py = Path(__file__).parent / 'ritz0.py'
    result = subprocess.run(
        [sys.executable, str(ritz0_py), source_path, '-o', output_ll],
        capture_output=True,
        text=True
    )
    return result.returncode == 0, result.stderr


def compile_ll_to_exe(ll_path: str, exe_path: str, extra_flags: list = None) -> tuple[bool, str]:
    """Compile LLVM IR to executable with clang."""
    cmd = ['clang', ll_path, '-o', exe_path, '-nostdlib', '-g']
    if extra_flags:
        cmd.extend(extra_flags)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


class TestAesNiIntrinsics:
    """Test AES-NI intrinsics."""

    @pytest.mark.skipif(not has_cpu_feature('aes'), reason="CPU doesn't support AES-NI")
    def test_aesni_compile_and_run(self):
        """Test that AES-NI intrinsics compile and execute correctly."""
        test_file = Path(__file__).parent / 'test' / 'test_aesni.ritz'
        assert test_file.exists(), f"Test file not found: {test_file}"

        # Use the test runner
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / 'ritz0.py'),
             str(test_file), '--test'],
            capture_output=True,
            text=True
        )
        # Check output for success
        assert '6 passed, 0 failed' in result.stdout or result.returncode == 0

    def test_aesni_generates_correct_intrinsics(self):
        """Test that AES-NI generates correct LLVM intrinsic calls."""
        source = '''
fn test_aesenc() -> i32
    var state: [4]i32
    var key: [4]i32
    state[0] = 1 as i32
    key[0] = 2 as i32
    let s: v4i32 = simd_loadu(@state[0])
    let k: v4i32 = simd_loadu(@key[0])
    let result: v4i32 = aesenc(s, k)
    var out: [4]i32
    simd_storeu(@out[0], result)
    0

fn main() -> i32
    test_aesenc()
'''
        with tempfile.NamedTemporaryFile(suffix='.ritz', mode='w', delete=False) as f:
            f.write(source)
            source_path = f.name

        try:
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as ll_file:
                ll_path = ll_file.name

            success, error = compile_ritz_to_ll(source_path, ll_path)
            assert success, f"Compilation failed: {error}"

            # Check that the LLVM IR contains the aesenc intrinsic
            with open(ll_path, 'r') as f:
                ir_content = f.read()

            assert 'llvm.x86.aesni.aesenc' in ir_content, \
                "LLVM IR should contain aesenc intrinsic"
        finally:
            os.unlink(source_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)


class TestShaNiIntrinsics:
    """Test SHA-NI intrinsics."""

    def test_shani_generates_correct_intrinsics(self):
        """Test that SHA-NI generates correct LLVM intrinsic calls."""
        source = '''
fn test_sha256rnds2() -> i32
    var cdgh: [4]i32
    var abef: [4]i32
    var wk: [4]i32
    cdgh[0] = 1 as i32
    abef[0] = 2 as i32
    wk[0] = 3 as i32
    let c: v4i32 = simd_loadu(@cdgh[0])
    let a: v4i32 = simd_loadu(@abef[0])
    let w: v4i32 = simd_loadu(@wk[0])
    let result: v4i32 = sha256rnds2(c, a, w)
    var out: [4]i32
    simd_storeu(@out[0], result)
    0

fn main() -> i32
    test_sha256rnds2()
'''
        with tempfile.NamedTemporaryFile(suffix='.ritz', mode='w', delete=False) as f:
            f.write(source)
            source_path = f.name

        try:
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as ll_file:
                ll_path = ll_file.name

            success, error = compile_ritz_to_ll(source_path, ll_path)
            assert success, f"Compilation failed: {error}"

            # Check that the LLVM IR contains the sha256rnds2 intrinsic
            with open(ll_path, 'r') as f:
                ir_content = f.read()

            assert 'llvm.x86.sha256rnds2' in ir_content, \
                "LLVM IR should contain sha256rnds2 intrinsic"
        finally:
            os.unlink(source_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)

    def test_sha256msg1_generates_intrinsic(self):
        """Test that sha256msg1 generates correct LLVM intrinsic."""
        source = '''
fn test_sha256msg1() -> i32
    var w0: [4]i32
    var w1: [4]i32
    w0[0] = 1 as i32
    w1[0] = 2 as i32
    let v0: v4i32 = simd_loadu(@w0[0])
    let v1: v4i32 = simd_loadu(@w1[0])
    let result: v4i32 = sha256msg1(v0, v1)
    var out: [4]i32
    simd_storeu(@out[0], result)
    0

fn main() -> i32
    test_sha256msg1()
'''
        with tempfile.NamedTemporaryFile(suffix='.ritz', mode='w', delete=False) as f:
            f.write(source)
            source_path = f.name

        try:
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as ll_file:
                ll_path = ll_file.name

            success, error = compile_ritz_to_ll(source_path, ll_path)
            assert success, f"Compilation failed: {error}"

            with open(ll_path, 'r') as f:
                ir_content = f.read()

            assert 'llvm.x86.sha256msg1' in ir_content, \
                "LLVM IR should contain sha256msg1 intrinsic"
        finally:
            os.unlink(source_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)

    def test_sha256msg2_generates_intrinsic(self):
        """Test that sha256msg2 generates correct LLVM intrinsic."""
        source = '''
fn test_sha256msg2() -> i32
    var w0: [4]i32
    var w1: [4]i32
    w0[0] = 1 as i32
    w1[0] = 2 as i32
    let v0: v4i32 = simd_loadu(@w0[0])
    let v1: v4i32 = simd_loadu(@w1[0])
    let result: v4i32 = sha256msg2(v0, v1)
    var out: [4]i32
    simd_storeu(@out[0], result)
    0

fn main() -> i32
    test_sha256msg2()
'''
        with tempfile.NamedTemporaryFile(suffix='.ritz', mode='w', delete=False) as f:
            f.write(source)
            source_path = f.name

        try:
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as ll_file:
                ll_path = ll_file.name

            success, error = compile_ritz_to_ll(source_path, ll_path)
            assert success, f"Compilation failed: {error}"

            with open(ll_path, 'r') as f:
                ir_content = f.read()

            assert 'llvm.x86.sha256msg2' in ir_content, \
                "LLVM IR should contain sha256msg2 intrinsic"
        finally:
            os.unlink(source_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)

    @pytest.mark.skipif(not has_cpu_feature('sha_ni'), reason="CPU doesn't support SHA-NI")
    def test_shani_compile_and_run(self):
        """Test that SHA-NI intrinsics execute correctly (requires SHA-NI support)."""
        test_file = Path(__file__).parent / 'test' / 'test_shani.ritz'
        assert test_file.exists(), f"Test file not found: {test_file}"

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / 'ritz0.py'),
             str(test_file), '--test'],
            capture_output=True,
            text=True
        )
        assert '4 passed, 0 failed' in result.stdout or result.returncode == 0


class TestCryptoIntrinsicErrors:
    """Test error handling for crypto intrinsics."""

    def test_aesenc_wrong_arg_count(self):
        """Test that aesenc with wrong number of args fails."""
        source = '''
fn test() -> i32
    var state: [4]i32
    let s: v4i32 = simd_loadu(@state[0])
    let result: v4i32 = aesenc(s)
    0

fn main() -> i32
    0
'''
        with tempfile.NamedTemporaryFile(suffix='.ritz', mode='w', delete=False) as f:
            f.write(source)
            source_path = f.name

        try:
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as ll_file:
                ll_path = ll_file.name

            success, error = compile_ritz_to_ll(source_path, ll_path)
            assert not success, "Should fail with wrong argument count"
            assert 'aesenc' in error.lower() or 'arguments' in error.lower()
        finally:
            os.unlink(source_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)

    def test_sha256rnds2_wrong_arg_count(self):
        """Test that sha256rnds2 with wrong number of args fails."""
        source = '''
fn test() -> i32
    var state: [4]i32
    let s: v4i32 = simd_loadu(@state[0])
    let result: v4i32 = sha256rnds2(s, s)
    0

fn main() -> i32
    0
'''
        with tempfile.NamedTemporaryFile(suffix='.ritz', mode='w', delete=False) as f:
            f.write(source)
            source_path = f.name

        try:
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as ll_file:
                ll_path = ll_file.name

            success, error = compile_ritz_to_ll(source_path, ll_path)
            assert not success, "Should fail with wrong argument count"
            assert 'sha256rnds2' in error.lower() or 'arguments' in error.lower()
        finally:
            os.unlink(source_path)
            if os.path.exists(ll_path):
                os.unlink(ll_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
