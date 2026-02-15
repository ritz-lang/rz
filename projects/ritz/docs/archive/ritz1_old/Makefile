# 🎭 ritz1 Makefile - Build the self-hosting Ritz compiler
#
# Usage:
#   make              - Build ritz1 (uses ritz1 if available, else ritz0)
#   make bootstrap    - Build ritz1 using ritz0 (bootstrap compiler)
#   make self         - Build ritz1 using itself (self-hosting)
#   make test         - Run ritz1 test suite
#   make clean        - Remove build artifacts
#   make valgrind     - Run with valgrind memory checking
#
# Override compiler:
#   make RITZC=ritz0  - Force use of ritz0 bootstrap compiler
#   make RITZC=ritz1  - Force use of ritz1 self-hosting compiler

.PHONY: all build bootstrap self test clean valgrind help

PYTHON ?= python3
LLC ?= llc
LD ?= ld
VALGRIND ?= valgrind --error-exitcode=1 --leak-check=full -q

# Paths
ROOT := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))/..
RITZ0 := $(PYTHON) $(ROOT)/ritz0/ritz0.py
RITZ1 := ./ritz1
SRC := src
OUT := ritz1

# Compiler selection: use ritz1 if it exists, otherwise ritz0
# Can be overridden with RITZC=ritz0 or RITZC=ritz1
ifeq ($(RITZC),ritz0)
  COMPILER := $(RITZ0)
  COMPILER_NAME := ritz0 (bootstrap)
else ifeq ($(RITZC),ritz1)
  COMPILER := $(RITZ1)
  COMPILER_NAME := ritz1 (self-hosting)
else
  # Auto-detect: prefer ritz1 if it exists and is executable
  ifeq ($(shell test -x $(RITZ1) && echo yes),yes)
    COMPILER := $(RITZ1)
    COMPILER_NAME := ritz1 (self-hosting)
  else
    COMPILER := $(RITZ0)
    COMPILER_NAME := ritz0 (bootstrap)
  endif
endif

# Source files in dependency order
# Note: Order matters for multi-file compilation
#
# main.ritz uses: lexer, parser, arena (mem.ritz), emitter
# Type system files (types.ritz, symbols.ritz) are imported by emitter and checker.
# With the import system, these are resolved automatically from emitter.ritz.
SOURCES := \
	$(SRC)/types.ritz \
	$(SRC)/mem.ritz \
	$(SRC)/utf8.ritz \
	$(SRC)/nfa.ritz \
	$(SRC)/regex.ritz \
	$(SRC)/tokens.ritz \
	$(SRC)/token_dsl.ritz \
	$(SRC)/lexer.ritz \
	$(SRC)/ritz_tokens.ritz \
	$(SRC)/parser.ritz \
	$(SRC)/emitter.ritz \
	$(SRC)/main.ritz

# Build outputs
LL_FILE := $(OUT).ll
OBJ_FILE := $(OUT).o

all: build

build: $(OUT)

# Default build - uses auto-detected compiler
# Both ritz0 and ritz1 use -o flag for output
$(OUT): $(SOURCES)
	@echo "=== Compiling ritz1 with $(COMPILER_NAME) ==="
	$(COMPILER) --lib $(SOURCES) -o $(LL_FILE)
	@if [ ! -s $(LL_FILE) ]; then \
		echo "Error: Compiler produced no output ($(LL_FILE) is empty or missing)"; \
		echo "The compiler ran but didn't generate LLVM IR."; \
		exit 1; \
	fi
	@echo "=== Assembling $(LL_FILE) -> $(OBJ_FILE) ==="
	$(LLC) -O2 -filetype=obj $(LL_FILE) -o $(OBJ_FILE)
	@echo "=== Linking $(OUT) ==="
	$(LD) -o $(OUT) $(OBJ_FILE) -e _start
	@echo "✓ Built $(OUT) using $(COMPILER_NAME)"

# Bootstrap: explicitly use ritz0
bootstrap: clean
	@$(MAKE) RITZC=ritz0

# Self-hosting: rebuild ritz1 using itself
# 1. Save the current binary as ritz1.prev
# 2. Compile new ritz1 using the saved binary
# 3. Keep ritz1.prev for comparison/rollback
self:
	@if [ ! -x $(RITZ1) ]; then \
		echo "Error: ritz1 binary not found. Run 'make bootstrap' first."; \
		exit 1; \
	fi
	@echo "=== Self-hosting: rebuilding ritz1 with itself ==="
	@cp $(RITZ1) $(RITZ1).prev
	@rm -f $(LL_FILE) $(OBJ_FILE) $(OUT)
	@$(MAKE) RITZC=ritz1 RITZ1=./ritz1.prev
	@echo "✓ Self-hosted build complete (ritz1.prev kept for comparison)"

test:
	@echo "=== Running ritz1 test suite ==="
	$(PYTHON) $(ROOT)/build.py ritz1-tests

valgrind: $(OUT)
	@echo "=== Running valgrind on ritz1 ==="
	@echo 'fn main() -> i32' > /tmp/valgrind_test.ritz
	@echo '  return 0' >> /tmp/valgrind_test.ritz
	$(VALGRIND) ./$(OUT) /tmp/valgrind_test.ritz -o /tmp/valgrind_test.ll
	@rm -f /tmp/valgrind_test.ritz /tmp/valgrind_test.ll
	@echo "✓ valgrind check passed"

clean:
	rm -f $(OUT) $(OUT).prev $(LL_FILE) $(OBJ_FILE)
	@echo "✓ Cleaned ritz1 build artifacts"

help:
	@echo "🎭 ritz1 - Self-hosting Ritz Compiler"
	@echo ""
	@echo "Build targets:"
	@echo "  make            - Build ritz1 (auto-selects compiler)"
	@echo "  make bootstrap  - Build using ritz0 (Python bootstrap compiler)"
	@echo "  make self       - Rebuild ritz1 using itself (saves old as ritz1.prev)"
	@echo ""
	@echo "Other targets:"
	@echo "  make test       - Run ritz1 test suite (142 tests)"
	@echo "  make valgrind   - Run binary with valgrind memory check"
	@echo "  make clean      - Remove build artifacts"
	@echo ""
	@echo "Compiler override:"
	@echo "  make RITZC=ritz0  - Force ritz0 bootstrap compiler"
	@echo "  make RITZC=ritz1  - Force ritz1 self-hosting compiler"
	@echo ""
	@echo "Output files:"
	@echo "  ritz1         - The compiled binary"
	@echo "  ritz1.ll      - LLVM IR intermediate"
	@echo "  ritz1.o       - Object file"
	@echo ""
	@echo "Current compiler: $(COMPILER_NAME)"
