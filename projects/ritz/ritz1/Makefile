# Makefile for ritz1 bootstrap compiler
#
# Compilation Model:
# ==================
# Each .ritz file compiles to one .ll file (1:1)
# Imports become external declarations (declare)
# Local definitions become full definitions (define)
# Final binary is linked from all object files
#
# Build flow:
#   ritz0 src/foo.ritz → build/foo.ll → build/foo.o
#   ld build/*.o → ritz1

# Compiler binaries
RITZ0 = python3 ../ritz0/ritz0.py
RITZ1 = build/ritz1
RITZ1_SELFHOSTED = build/ritz1_selfhosted

# Source files - each becomes a separate object file
SRC_DIR = src
SOURCES = \
	tokens_gen \
	nfa \
	regex \
	lexer_nfa \
	lexer_setup_gen \
	ast \
	ast_helpers \
	parser_gen \
	monomorph \
	emitter \
	main

# ritzlib modules needed by ritz1
RITZLIB_DIR = ../ritzlib
RITZLIB_MODULES = sys io str string hash memory gvec drop

# Build artifacts
BUILD_DIR = build
LL_FILES = $(patsubst %,$(BUILD_DIR)/%.ll,$(SOURCES))
OBJ_FILES = $(patsubst %,$(BUILD_DIR)/%.o,$(SOURCES))
RITZLIB_OBJ = $(patsubst %,$(BUILD_DIR)/ritzlib_%.o,$(RITZLIB_MODULES))

# Runtime - entry point that calls main(argc, argv) and handles exit
RUNTIME = ../runtime/ritz_start.x86_64.o

# Compiler flags
LLC_FLAGS = -O2
LD_FLAGS = -dynamic-linker /lib64/ld-linux-x86-64.so.2 -lc

# Environment for import resolution
export RITZ_PATH = $(shell cd .. && pwd)

.PHONY: all clean distclean ritz1 bootstrap verify test stats

# Default target
all: ritz1

# Ensure build directory exists
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# === Pattern rules for module compilation ===

# Compile .ritz to .ll (1:1, with imports as external declarations)
# All modules except main_new use --no-runtime (no _start)
$(BUILD_DIR)/%.ll: $(SRC_DIR)/%.ritz | $(BUILD_DIR)
	@echo "Compiling $< → $@"
	$(RITZ0) $< --no-runtime -o $@

# main is special - it has main() but _start comes from runtime/ritz_start*.o
$(BUILD_DIR)/main.ll: $(SRC_DIR)/main.ritz | $(BUILD_DIR)
	@echo "Compiling $< → $@ (main function, runtime provides _start)"
	$(RITZ0) $< --no-runtime -o $@

# Compile .ll to .o (use clang directly for LLVM IR)
$(BUILD_DIR)/%.o: $(BUILD_DIR)/%.ll
	@echo "Compiling $< → $@"
	clang -c -O2 $< -o $@

# === Compile ritzlib modules ===
$(BUILD_DIR)/ritzlib_%.ll: $(RITZLIB_DIR)/%.ritz | $(BUILD_DIR)
	@echo "Compiling ritzlib/$*.ritz → $@"
	$(RITZ0) $< --no-runtime -o $@

$(BUILD_DIR)/ritzlib_%.o: $(BUILD_DIR)/ritzlib_%.ll
	@echo "Compiling $< → $@"
	clang -c -O2 $< -o $@

# === Build ritz1 from source using ritz0 ===
ritz1: $(RITZ1)

$(RITZ1): $(OBJ_FILES) $(RITZLIB_OBJ) $(RUNTIME)
	@echo "=== Linking ritz1 ==="
	ld $(LD_FLAGS) -o $@ $(RUNTIME) $(OBJ_FILES) $(RITZLIB_OBJ)
	@echo "✓ ritz1 binary created: $(RITZ1)"
	@ls -lh $@

# === Bootstrap: Use ritz1 to compile itself ===
bootstrap: $(RITZ1_SELFHOSTED)
	@echo "✓ Bootstrap complete: $(RITZ1_SELFHOSTED)"
	@ls -lh $(RITZ1_SELFHOSTED)

# Self-hosted compilation uses the same pattern
# Each module is compiled by ritz1 instead of ritz0
SELFHOSTED_LL = $(patsubst %,$(BUILD_DIR)/%_sh.ll,$(SOURCES))
SELFHOSTED_OBJ = $(patsubst %,$(BUILD_DIR)/%_sh.o,$(SOURCES))

$(BUILD_DIR)/%_sh.ll: $(SRC_DIR)/%.ritz $(RITZ1) | $(BUILD_DIR)
	@echo "Self-compiling $< → $@"
	$(RITZ1) $< -o $@

$(BUILD_DIR)/%_sh.o: $(BUILD_DIR)/%_sh.ll
	@echo "Assembling $< → $@"
	llc $(LLC_FLAGS) $< -o $(BUILD_DIR)/$*_sh.s
	clang -c $(BUILD_DIR)/$*_sh.s -o $@

$(RITZ1_SELFHOSTED): $(SELFHOSTED_OBJ) $(RUNTIME)
	@echo "=== Linking self-hosted ritz1 ==="
	ld $(LD_FLAGS) -o $@ $(RUNTIME) $(SELFHOSTED_OBJ)
	@echo "✓ Self-hosted binary created: $(RITZ1_SELFHOSTED)"
	@ls -lh $@

# === Verify bootstrap ===
verify: $(RITZ1) $(RITZ1_SELFHOSTED)
	@echo "=== Verification ==="
	@ls -lh $(RITZ1) $(RITZ1_SELFHOSTED)
	@echo "Testing ritz1..."
	@echo "fn main() -> i32" > /tmp/test_verify.ritz
	@echo "  42" >> /tmp/test_verify.ritz
	$(RITZ1) /tmp/test_verify.ritz -o /tmp/test_verify.ll
	@echo "Testing ritz1_selfhosted..."
	$(RITZ1_SELFHOSTED) /tmp/test_verify.ritz -o /tmp/test_verify_sh.ll
	@echo "✓ Both compilers work"

# === Test ===
test: $(RITZ1)
	@echo "=== Testing ritz1 ==="
	@echo "fn main() -> i32" > /tmp/test_bootstrap.ritz
	@echo "  42" >> /tmp/test_bootstrap.ritz
	$(RITZ1) /tmp/test_bootstrap.ritz -o $(BUILD_DIR)/test_bootstrap.ll
	@echo "✓ Test passed"

# === Statistics ===
stats:
	@echo "=== Build Statistics ==="
	@echo "Source files: $(words $(SOURCES))"
	@for src in $(SOURCES); do \
		wc -l $(SRC_DIR)/$$src.ritz 2>/dev/null || true; \
	done
	@echo ""
	@echo "Binaries:"
	@ls -lh $(RITZ1) $(RITZ1_SELFHOSTED) 2>/dev/null || echo "  (not yet built)"

# === Clean ===
clean:
	@echo "Cleaning build artifacts..."
	rm -f $(BUILD_DIR)/*.ll $(BUILD_DIR)/*.s $(BUILD_DIR)/*.o
	@echo "✓ Build artifacts cleaned"

distclean: clean
	@echo "Removing binaries..."
	rm -f $(RITZ1) $(RITZ1_SELFHOSTED)
	@echo "✓ All artifacts removed"
