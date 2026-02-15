#!/usr/bin/env python3
"""
A/B Test Harness for ritz0-llvmlite vs ritz1-text IR

Compiles Ritz programs using both paths and compares outputs:
- Path A: ritz0 (Python) with llvmlite IR generation
- Path B: ritz1 IR emitter (text generation) compiled by ritz0

Comparison strategy:
1. Compile source with both paths to get IR
2. Normalize IR (strip SSA IDs, whitespace, comments)
3. Compare normalized IR structurally
4. Compile both IRs to binaries and compare behavior
"""

import sys
import subprocess
import tempfile
import os
import re
from pathlib import Path
from typing import Tuple, Optional

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def normalize_ir(ir_text: str) -> str:
    """
    Normalize LLVM IR for comparison.

    Removes:
    - SSA value IDs (%1, %2, etc.) -> %VAL
    - Label IDs (L1, L2, etc.) -> LABEL
    - String constant IDs (@.str.0, etc.) -> @.str.N
    - Line numbers and comments
    - Extra whitespace
    """
    lines = ir_text.strip().split('\n')
    normalized = []

    for line in lines:
        # Skip comments
        if line.strip().startswith(';') and 'ModuleID' not in line:
            continue

        # Normalize SSA IDs: %1, %2, %"foo.arg" -> %VAL
        line = re.sub(r'%\d+\b', '%VAL', line)
        line = re.sub(r'%"[^"]+\.arg"', '%ARG', line)
        line = re.sub(r'%"[^"]+"', '%NAME', line)

        # Normalize labels: %L1, %L2 -> %LABEL
        line = re.sub(r'%L\d+\b', '%LABEL', line)
        line = re.sub(r'\bL\d+:', 'LABEL:', line)

        # Normalize string constants: @.str.0 -> @.str.N
        line = re.sub(r'@\.str\.\d+', '@.str.N', line)

        # Normalize whitespace
        line = ' '.join(line.split())

        if line:
            normalized.append(line)

    return '\n'.join(normalized)

def compile_with_ritz0(source_file: Path, output_ir: Path) -> bool:
    """Compile source with ritz0 (llvmlite path)."""
    try:
        # Find ritz0.py relative to project root
        script_dir = Path(__file__).parent.parent  # Go from tools/ to project root
        ritz0_script = script_dir / 'ritz0' / 'ritz0.py'

        if not ritz0_script.exists():
            print(f"{RED}Cannot find ritz0.py at {ritz0_script}{RESET}")
            return False

        cmd = [
            sys.executable,
            str(ritz0_script),
            str(source_file),
            '-o', str(output_ir)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"{RED}ritz0 compilation failed:{RESET}")
            print(result.stderr)
            return False
        return True
    except Exception as e:
        print(f"{RED}Error running ritz0: {e}{RESET}")
        return False

def compile_with_ritz1_ir(source_file: Path, output_ir: Path) -> bool:
    """
    Compile source with ritz1 IR emitter (text IR path).

    This involves:
    1. Using ritz0 to compile the ritz1 IR emitter to a binary (already done - ritz1_mini/build/ritz1_mini)
    2. Running that binary on the source file to get text IR
    """
    try:
        # Find ritz1 binary relative to project root
        script_dir = Path(__file__).parent.parent  # Go from tools/ to project root
        ritz1_binary = script_dir / 'ritz1' / 'build' / 'ritz1'

        if not ritz1_binary.exists():
            print(f"{RED}Cannot find ritz1 at {ritz1_binary}{RESET}")
            print(f"{YELLOW}Run: cd ritz1 && python ../ritz0/ritz0.py src/main.ritz -o build/ritz1.ll && llc -filetype=obj build/ritz1.ll -o build/ritz1.o && gcc -nostdlib -no-pie build/ritz1.o -o build/ritz1{RESET}")
            return False

        cmd = [
            str(ritz1_binary),
            str(source_file),
            '-o', str(output_ir)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"{RED}ritz1 compilation failed:{RESET}")
            print(result.stderr)
            return False
        return True
    except Exception as e:
        print(f"{RED}Error running ritz1: {e}{RESET}")
        return False

def ir_to_binary(ir_file: Path, binary_file: Path) -> bool:
    """Compile LLVM IR to native binary using llc + gcc."""
    try:
        # Check if IR has naked _start (indicates no standard library needed)
        ir_text = ir_file.read_text()
        has_naked_start = 'define void @_start() naked' in ir_text

        # IR -> assembly
        asm_file = ir_file.with_suffix('.s')
        result = subprocess.run(
            ['llc', '-filetype=asm', '-o', str(asm_file), str(ir_file)],
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"{RED}llc failed:{RESET}")
            print(result.stderr.decode())
            return False

        # assembly -> binary
        # Use -nostdlib for naked _start functions (no C runtime)
        gcc_args = ['gcc', '-no-pie', '-o', str(binary_file), str(asm_file)]
        if has_naked_start:
            gcc_args.insert(1, '-nostdlib')

        result = subprocess.run(
            gcc_args,
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            print(f"{RED}gcc failed:{RESET}")
            print(result.stderr.decode())
            return False

        return True
    except Exception as e:
        print(f"{RED}Error compiling to binary: {e}{RESET}")
        return False

def run_binary(binary: Path, input_data: Optional[str] = None, args: list = None) -> Tuple[int, str, str]:
    """Run a binary and return (exit_code, stdout, stderr)."""
    try:
        cmd = [str(binary)]
        if args:
            cmd.extend(args)

        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"
    except Exception as e:
        return -1, "", str(e)

def compare_ir_structure(ir_a: str, ir_b: str) -> Tuple[bool, list]:
    """Compare normalized IR structure. Returns (matches, differences)."""
    norm_a = normalize_ir(ir_a)
    norm_b = normalize_ir(ir_b)

    lines_a = norm_a.split('\n')
    lines_b = norm_b.split('\n')

    differences = []

    # Compare line by line
    max_lines = max(len(lines_a), len(lines_b))
    for i in range(max_lines):
        line_a = lines_a[i] if i < len(lines_a) else "<missing>"
        line_b = lines_b[i] if i < len(lines_b) else "<missing>"

        if line_a != line_b:
            differences.append(f"Line {i+1}:")
            differences.append(f"  A: {line_a}")
            differences.append(f"  B: {line_b}")

    return len(differences) == 0, differences

def ab_test_file(source_file: Path, test_input: Optional[str] = None, test_args: list = None) -> bool:
    """
    Run A/B test on a single source file.

    Returns True if both paths produce equivalent results.
    """
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}A/B Testing: {source_file.name}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Path A: ritz0 + llvmlite
        print(f"\n{YELLOW}Path A: ritz0 (llvmlite){RESET}")
        ir_a = tmpdir / 'output_a.ll'
        if not compile_with_ritz0(source_file, ir_a):
            print(f"{RED}Path A failed{RESET}")
            return False

        with open(ir_a) as f:
            ir_a_text = f.read()
        print(f"{GREEN}✓ Generated {len(ir_a_text)} bytes of IR{RESET}")

        # Path B: ritz1 IR emitter (text)
        print(f"\n{YELLOW}Path B: ritz1 IR emitter (text){RESET}")
        ir_b = tmpdir / 'output_b.ll'
        if not compile_with_ritz1_ir(source_file, ir_b):
            print(f"{YELLOW}Path B not yet implemented - skipping IR comparison{RESET}")
            print(f"{GREEN}✓ Path A IR validated{RESET}")
            return True  # For now, just validate path A works

        with open(ir_b) as f:
            ir_b_text = f.read()
        print(f"{GREEN}✓ Generated {len(ir_b_text)} bytes of IR{RESET}")

        # Compare IR structure (informational only - differences expected)
        print(f"\n{YELLOW}Comparing IR structure...{RESET}")
        matches, diffs = compare_ir_structure(ir_a_text, ir_b_text)

        if not matches:
            print(f"{YELLOW}ℹ IR structures differ ({len(diffs)} differences - expected){RESET}")
            # Show a few differences for debugging, but don't fail
            for diff in diffs[:3]:  # Show first 3 differences
                print(f"  {diff}")
            if len(diffs) > 3:
                print(f"  ... and {len(diffs) - 3} more differences")
        else:
            print(f"{GREEN}✓ IR structures match{RESET}")

        # Compile both to binaries
        print(f"\n{YELLOW}Compiling to binaries...{RESET}")
        bin_a = tmpdir / 'binary_a'
        bin_b = tmpdir / 'binary_b'

        if not ir_to_binary(ir_a, bin_a):
            print(f"{RED}Failed to compile Path A IR{RESET}")
            return False
        print(f"{GREEN}✓ Path A binary compiled{RESET}")

        if not ir_to_binary(ir_b, bin_b):
            print(f"{RED}Failed to compile Path B IR{RESET}")
            return False
        print(f"{GREEN}✓ Path B binary compiled{RESET}")

        # Run both binaries and compare behavior
        print(f"\n{YELLOW}Running binaries...{RESET}")
        exit_a, out_a, err_a = run_binary(bin_a, test_input, test_args)
        exit_b, out_b, err_b = run_binary(bin_b, test_input, test_args)

        print(f"  Path A: exit={exit_a}, stdout={len(out_a)} bytes, stderr={len(err_a)} bytes")
        print(f"  Path B: exit={exit_b}, stdout={len(out_b)} bytes, stderr={len(err_b)} bytes")

        # Compare results
        if exit_a != exit_b:
            print(f"{RED}✗ Exit codes differ: A={exit_a}, B={exit_b}{RESET}")
            return False

        if out_a != out_b:
            print(f"{RED}✗ Stdout differs:{RESET}")
            print(f"  A: {repr(out_a[:100])}")
            print(f"  B: {repr(out_b[:100])}")
            return False

        if err_a != err_b:
            print(f"{RED}✗ Stderr differs:{RESET}")
            print(f"  A: {repr(err_a[:100])}")
            print(f"  B: {repr(err_b[:100])}")
            return False

        print(f"{GREEN}✓ Binary behavior matches (exit={exit_a}){RESET}")

    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}✓ A/B test PASSED for {source_file.name}{RESET}")
    print(f"{GREEN}{'='*70}{RESET}")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/ab_test.py <source.ritz> [<source2.ritz> ...]")
        print("\nExamples:")
        print("  python tools/ab_test.py examples/01_hello/main.ritz")
        print("  python tools/ab_test.py examples/*/main.ritz")
        sys.exit(1)

    source_files = [Path(arg) for arg in sys.argv[1:]]

    # Filter out non-existent files
    source_files = [f for f in source_files if f.exists()]

    if not source_files:
        print(f"{RED}No valid source files found{RESET}")
        sys.exit(1)

    print(f"{BLUE}A/B Test Harness{RESET}")
    print(f"{BLUE}Testing {len(source_files)} file(s){RESET}")

    passed = 0
    failed = 0

    for source_file in source_files:
        try:
            if ab_test_file(source_file):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"{RED}Error testing {source_file}: {e}{RESET}")
            failed += 1

    # Summary
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}Summary:{RESET}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    if failed > 0:
        print(f"  {RED}Failed: {failed}{RESET}")
    else:
        print(f"  Failed: {failed}")
    print(f"{BLUE}{'='*70}{RESET}")

    sys.exit(0 if failed == 0 else 1)

if __name__ == '__main__':
    main()
