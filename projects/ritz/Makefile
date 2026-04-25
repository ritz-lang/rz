# 🎭 Ritz Language Build System
#
# Usage:
#   make            - Run all tests
#   make test       - Build and test all examples
#   make unit       - Run Python unit tests only
#   make ritz       - Run .ritz language tests
#   make build      - Build all examples (no tests)
#   make clean      - Remove build artifacts
#   make list       - List all packages
#
# Individual packages:
#   make build-<name>  - Build a specific package
#   make test-<name>   - Build and test a specific package

.PHONY: all test unit ritz ritz1 build clean list help valgrind regression regression-quick check-no-s-strings matrix matrix-full matrix-quick

PYTHON ?= python3
VALGRIND ?= valgrind --error-exitcode=1 --leak-check=full -q

# Set RITZ_PATH for standard library lookup
# This allows 'import ritzlib.sys' to resolve to $(ROOT)/ritzlib/sys.ritz
ROOT := $(shell pwd)
export RITZ_PATH := $(ROOT)

all: test

# Run everything
# AGAST #98: check-no-s-strings runs first so any resurrected s"..." literal
# fails CI before we burn compile cycles on it.
test: check-no-s-strings unit ritz ritz1 examples
	@echo "✓ All tests passed!"

# AGAST #98 guard: ensure no s"..." span-string literals leak back in.
# The prefix was removed after bare "..." was flipped to StrView (same
# { ptr, len } shape), so any new s"..." is either dead syntax or a
# regression. docs/archive/ is excluded (frozen snapshots).
check-no-s-strings:
	@echo "=== Checking no s\"...\" literals remain ==="
	@$(PYTHON) tools/check_no_s_strings.py .

# Python unit tests for ritz0 compiler
unit:
	@echo "=== Running ritz0 unit tests ==="
	@cd ritz0 && $(PYTHON) -m pytest -q

# Run .ritz language tests (test levels)
ritz:
	@echo "=== Running .ritz language tests ==="
	@$(PYTHON) build.py ritz-tests

# Run ritz1 self-hosting lexer tests
ritz1:
	@echo "=== Running ritz1 lexer tests ==="
	@$(PYTHON) build.py ritz1-tests

# Build and test all examples (always runs)
.PHONY: examples
examples:
	@$(PYTHON) build.py test --all

# Build all examples (no tests)
build:
	@$(PYTHON) build.py build --all

# List all packages
list:
	@$(PYTHON) build.py list

# Clean build artifacts
clean:
	@$(PYTHON) build.py clean
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@find . -name "*.ritz.sig" -delete 2>/dev/null || true
	@rm -f /tmp/*.ll /tmp/*.o 2>/dev/null || true

# Pattern rules for individual packages
build-%:
	@$(PYTHON) build.py build $*

test-%:
	@$(PYTHON) build.py test $*

# Run Tier 1 examples through valgrind for memory checking
valgrind: build
	@echo "=== Running valgrind memory checks ==="
	@$(VALGRIND) examples/01_hello/hello
	@$(VALGRIND) examples/03_echo/echo hello world >/dev/null
	@$(VALGRIND) examples/04_true_false/true
	@echo "test" | $(VALGRIND) examples/05_cat/cat >/dev/null
	@printf "line1\nline2\n" | $(VALGRIND) examples/06_head/head -n 1 >/dev/null
	@printf "a b c\n" | $(VALGRIND) examples/07_wc/wc >/dev/null
	@$(VALGRIND) examples/08_seq/seq 5 >/dev/null
	@$(VALGRIND) examples/10_sleep/sleep 0.001
	@echo "✓ All valgrind checks passed!"

# Validation matrix: 33-test regression × {ritz0, ritz1, ritz1_selfhosted}.
# See docs/VALIDATION.md for the full validation workflow.
#
# Three escalating thoroughness levels:
#   matrix-quick — incremental ritz1 build + ritz1-only matrix       (~30-60s)
#   matrix       — alias for matrix-quick (the common pre-commit gate)
#   matrix-full  — incremental ritz1 + selfhost build + full matrix  (~4-5min)
#
# DO NOT add a `clean` step here. Make's dep tracking is correct; if it
# isn't, that's a Makefile bug. See docs/VALIDATION.md "Hard rules".
matrix-quick: | _matrix_ritz1_built
	@$(PYTHON) tools/run_regression_matrix.py --compiler ritz1

matrix: matrix-quick

matrix-full: | _matrix_ritz1_built
	@echo "=== Full matrix (ritz0 + ritz1 + ritz1_selfhosted) ==="
	@echo "    This will incrementally rebuild ritz1_selfhosted (~3 min if ritz1 source changed)."
	@$(PYTHON) tools/run_regression_matrix.py --rebuild

# Internal: ensure ritz1 binary is up-to-date before running the matrix.
.PHONY: _matrix_ritz1_built
_matrix_ritz1_built:
	@$(MAKE) -C ritz1 ritz1 >/dev/null 2>&1 || $(MAKE) -C ritz1 ritz1

# Regression test suite (all tiers)
regression:
	@./scripts/regression.sh

# Quick regression (skip self-hosted bootstrap)
regression-quick:
	@./scripts/regression.sh --quick

help:
	@echo "🎭 Ritz Language Build System"
	@echo ""
	@echo "Targets:"
	@echo "  make          - Run all tests (unit + ritz + ritz1 + examples)"
	@echo "  make test     - Same as above"
	@echo "  make unit     - Run Python unit tests (ritz0)"
	@echo "  make ritz     - Run .ritz language tests (test levels)"
	@echo "  make ritz1    - Run ritz1 self-hosting lexer tests"
	@echo "  make examples - Build and test example packages"
	@echo "  make build    - Build all examples (no tests)"
	@echo "  make list     - List all packages"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make valgrind - Run valgrind memory checks on Tier 1 examples"
	@echo "  make matrix       - Pre-commit gate: incremental ritz1 + ritz1-only matrix (~30-60s)"
	@echo "  make matrix-full  - Pre-push gate: incremental ritz1 + selfhost + full matrix (~4-5min)"
	@echo "  make regression       - Full regression suite (all 4 tiers)"
	@echo "  make regression-quick - Quick regression (skip bootstrap)"
	@echo "  make check-no-s-strings - Guard that no s\"...\" literals leak back in"
	@echo ""
	@echo "  See docs/VALIDATION.md for the full validation workflow."
	@echo ""
	@echo "Individual packages:"
	@echo "  make build-<name>  - Build a specific package"
	@echo "  make test-<name>   - Test a specific package"
	@echo ""
	@echo "Examples:"
	@echo "  make test-hello"
	@echo "  make build-05_cat"
