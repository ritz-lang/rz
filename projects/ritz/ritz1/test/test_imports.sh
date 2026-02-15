#!/bin/bash
# ritz1/test/test_imports.sh - Test ritz1 import handling
#
# Tests various import scenarios to catch regressions.
# Each test creates a minimal .ritz file and tries to compile it.
#
# KNOWN ISSUE: ritz1 has a memory corruption bug causing non-deterministic
# crashes on some import scenarios. Tests marked with "known_issue" may
# fail intermittently until the bug is fixed.

set -e  # Exit on first failure
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LANG_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
RITZ1="$LANG_ROOT/ritz1/build/ritz1"
TEST_DIR="/tmp/ritz1_test_$$"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

declare -i passed=0
declare -i failed=0
declare -i skipped=0

# Setup
mkdir -p "$TEST_DIR/output"

# Use LANG_ROOT for RITZ_PATH (where ritzlib lives)
RITZ_PATH="$LANG_ROOT"

# Test helper
run_test() {
    local name="$1"
    local file="$2"
    local should_pass="$3"  # "pass" or "fail"

    echo -n "Testing: $name... "

    if timeout 10s "$RITZ1" "$file" -o "$TEST_DIR/output/test.ll" -I "$RITZ_PATH" 2>/dev/null; then
        if [ "$should_pass" = "pass" ]; then
            echo -e "${GREEN}PASS${NC}"
            passed=$((passed + 1))
        else
            echo -e "${RED}FAIL (expected failure but passed)${NC}"
            failed=$((failed + 1))
        fi
    else
        if [ "$should_pass" = "fail" ]; then
            echo -e "${GREEN}PASS (expected failure)${NC}"
            passed=$((passed + 1))
        else
            echo -e "${RED}FAIL${NC}"
            failed=$((failed + 1))
        fi
    fi
}

echo "=== ritz1 Import Tests ==="
echo "LANG_ROOT: $LANG_ROOT"
echo "RITZ1: $RITZ1"
echo "RITZ_PATH: $RITZ_PATH"
echo "TEST_DIR: $TEST_DIR"
echo ""

# ============================================================================
# Basic Tests
# ============================================================================

# Test 1: Simple main function (no imports)
cat > "$TEST_DIR/test_basic.ritz" << 'EOF'
fn main() -> i32
    0
EOF
run_test "Basic main (no imports)" "$TEST_DIR/test_basic.ritz" "pass"

# Test 2: Single import (sys)
cat > "$TEST_DIR/test_single_import.ritz" << 'EOF'
import ritzlib.sys

fn main() -> i32
    0
EOF
run_test "Single import (sys)" "$TEST_DIR/test_single_import.ritz" "pass"

# Test 3: Single import (str)
cat > "$TEST_DIR/test_str_import.ritz" << 'EOF'
import ritzlib.str

fn main() -> i32
    0
EOF
run_test "Single import (str)" "$TEST_DIR/test_str_import.ritz" "pass"

# Test 4: Two imports (sys + str)
cat > "$TEST_DIR/test_two_imports.ritz" << 'EOF'
import ritzlib.sys
import ritzlib.str

fn main() -> i32
    0
EOF
run_test "Two imports (sys + str)" "$TEST_DIR/test_two_imports.ritz" "pass"

# ============================================================================
# Struct Tests
# ============================================================================

# Test 5: Simple struct (no imports)
cat > "$TEST_DIR/test_struct.ritz" << 'EOF'
struct MyStruct
    val: i32

fn main() -> i32
    0
EOF
run_test "Simple struct (no imports)" "$TEST_DIR/test_struct.ritz" "pass"

# Test 6: Struct + import
cat > "$TEST_DIR/test_struct_import.ritz" << 'EOF'
import ritzlib.sys

struct MyStruct
    val: i32

fn main() -> i32
    0
EOF
run_test "Struct + single import" "$TEST_DIR/test_struct_import.ritz" "pass"

# Test 7: Generic struct (no imports)
cat > "$TEST_DIR/test_generic_struct.ritz" << 'EOF'
struct MyVec<T>
    data: *T
    len: i64

fn main() -> i32
    0
EOF
run_test "Generic struct (no imports)" "$TEST_DIR/test_generic_struct.ritz" "pass"

# Test 8: Generic struct + import
cat > "$TEST_DIR/test_generic_struct_import.ritz" << 'EOF'
import ritzlib.sys

struct MyVec<T>
    data: *T
    len: i64

fn main() -> i32
    0
EOF
run_test "Generic struct + single import" "$TEST_DIR/test_generic_struct_import.ritz" "pass"

# ============================================================================
# Global Variable Tests
# ============================================================================

# Test 9: Global variable (no imports)
cat > "$TEST_DIR/test_global.ritz" << 'EOF'
var g_count: i32 = 0

fn main() -> i32
    0
EOF
run_test "Global variable (no imports)" "$TEST_DIR/test_global.ritz" "pass"

# Test 10: Global variable + import
cat > "$TEST_DIR/test_global_import.ritz" << 'EOF'
import ritzlib.sys

var g_count: i32 = 0

fn main() -> i32
    0
EOF
run_test "Global variable + import" "$TEST_DIR/test_global_import.ritz" "pass"

# Test 11: Struct-typed global (no imports)
cat > "$TEST_DIR/test_struct_global.ritz" << 'EOF'
struct MyStruct
    val: i32

var g_struct: MyStruct

fn main() -> i32
    0
EOF
run_test "Struct-typed global (no imports)" "$TEST_DIR/test_struct_global.ritz" "pass"

# ============================================================================
# Constant Tests
# ============================================================================

# Test 12: Constant (no imports)
cat > "$TEST_DIR/test_const.ritz" << 'EOF'
const MY_CONST: i64 = 42

fn main() -> i32
    0
EOF
run_test "Constant (no imports)" "$TEST_DIR/test_const.ritz" "pass"

# Test 13: Constant + import
cat > "$TEST_DIR/test_const_import.ritz" << 'EOF'
import ritzlib.sys

const MY_CONST: i64 = 42

fn main() -> i32
    0
EOF
run_test "Constant + import" "$TEST_DIR/test_const_import.ritz" "pass"

# ============================================================================
# Combined Tests (Known Problem Areas)
# ============================================================================

# Test 14: sys + str + const + struct (memory.ritz pattern)
cat > "$TEST_DIR/test_complex.ritz" << 'EOF'
import ritzlib.sys
import ritzlib.str

const MY_CONST: i64 = 42

struct MyStruct
    val: i32

fn main() -> i32
    0
EOF
# This should work now with correct RITZ_PATH
run_test "sys + str + const + struct (memory.ritz pattern)" "$TEST_DIR/test_complex.ritz" "pass"

# ============================================================================
# Generic Function Tests
# ============================================================================

# Test 15: Generic function (no imports)
cat > "$TEST_DIR/test_generic_fn.ritz" << 'EOF'
struct Vec<T>
    data: *T
    len: i64

fn vec_new<T>() -> Vec<T>
    var v: Vec<T>
    v.data = 0 as *T
    v.len = 0
    return v

fn main() -> i32
    0
EOF
run_test "Generic function (no imports)" "$TEST_DIR/test_generic_fn.ritz" "pass"

# Test 16: Generic function + import
cat > "$TEST_DIR/test_generic_fn_import.ritz" << 'EOF'
import ritzlib.sys

struct Vec<T>
    data: *T
    len: i64

fn vec_new<T>() -> Vec<T>
    var v: Vec<T>
    v.data = 0 as *T
    v.len = 0
    return v

fn main() -> i32
    0
EOF
run_test "Generic function + import" "$TEST_DIR/test_generic_fn_import.ritz" "pass"

# ============================================================================
# Array in Struct Tests
# ============================================================================

# Test 17: Struct with array member
cat > "$TEST_DIR/test_struct_array.ritz" << 'EOF'
struct Item
    val: i64

struct Container
    items: [8]Item
    count: i32

fn main() -> i32
    0
EOF
run_test "Struct with array member" "$TEST_DIR/test_struct_array.ritz" "pass"

# Test 18: Struct with array + import
cat > "$TEST_DIR/test_struct_array_import.ritz" << 'EOF'
import ritzlib.sys

struct Item
    val: i64

struct Container
    items: [8]Item
    count: i32

fn main() -> i32
    0
EOF
run_test "Struct with array + import" "$TEST_DIR/test_struct_array_import.ritz" "pass"

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "=== Summary ==="
echo -e "Passed: ${GREEN}$passed${NC}"
echo -e "Failed: ${RED}$failed${NC}"
echo "Skipped: $skipped"
echo ""

# Cleanup
rm -rf "$TEST_DIR"

if [ $failed -gt 0 ]; then
    exit 1
fi
exit 0
