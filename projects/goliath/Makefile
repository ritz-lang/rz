# Goliath Makefile
#
# Build and test the Goliath content-addressable filesystem.
#
# Requires RITZ_PATH environment variable pointing to ritz-lang projects directory.
# Example: export RITZ_PATH=~/dev/ritz-lang

# Configuration
RITZ_PATH ?= $(HOME)/dev/ritz-lang
RITZ0 = python3 $(RITZ_PATH)/ritz/ritz0/ritz0.py
LIST_DEPS = python3 $(RITZ_PATH)/ritz/ritz0/list_deps.py
RUNTIME = $(RITZ_PATH)/ritz/runtime/ritz_start.x86_64.o

# Build directories
BUILD_DIR = build
TEST_BUILD_DIR = $(BUILD_DIR)/test

# Source files
SRC_FILES = $(wildcard src/*.ritz)
TEST_FILES = $(wildcard test/*.ritz)

# Default target
.PHONY: all
all: build

# Build the library (compile to LLVM IR)
.PHONY: build
build: $(BUILD_DIR)/goliath.ll
	@echo "Build complete: $(BUILD_DIR)/goliath.ll"

$(BUILD_DIR)/goliath.ll: $(SRC_FILES) | $(BUILD_DIR)
	@echo "Compiling goliath library..."
	$(RITZ0) src/main.ritz -o $@ --no-runtime

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(TEST_BUILD_DIR):
	mkdir -p $(TEST_BUILD_DIR)

# Build and run tests
.PHONY: test
test: build-tests
	@echo ""
	@echo "Running tests..."
	./$(TEST_BUILD_DIR)/tests

.PHONY: test-verbose
test-verbose: build-tests
	./$(TEST_BUILD_DIR)/tests -v

.PHONY: test-filter
test-filter: build-tests
	./$(TEST_BUILD_DIR)/tests -f $(FILTER)

.PHONY: test-list
test-list: build-tests
	./$(TEST_BUILD_DIR)/tests -l

# Build test binary
.PHONY: build-tests
build-tests: $(TEST_BUILD_DIR)/tests
	@echo "Test binary ready: $(TEST_BUILD_DIR)/tests"

$(TEST_BUILD_DIR)/tests: $(SRC_FILES) $(TEST_FILES) | $(TEST_BUILD_DIR)
	@echo "Building test binary..."
	./build_tests.sh

# Clean build artifacts
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR)

# Check environment
.PHONY: check-env
check-env:
	@echo "RITZ_PATH: $(RITZ_PATH)"
	@echo "RITZ0: $(RITZ0)"
	@test -f "$(RITZ0)" || (echo "ERROR: ritz0 not found at $(RITZ0)" && exit 1)
	@test -f "$(RUNTIME)" || (echo "ERROR: runtime not found at $(RUNTIME)" && exit 1)
	@echo "Environment OK"

# Help
.PHONY: help
help:
	@echo "Goliath Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  build        - Compile library to LLVM IR"
	@echo "  test         - Build and run all tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  test-filter  - Run tests matching FILTER=<pattern>"
	@echo "  test-list    - List all tests without running"
	@echo "  clean        - Remove build artifacts"
	@echo "  check-env    - Verify RITZ_PATH and tools"
	@echo ""
	@echo "Environment:"
	@echo "  RITZ_PATH    - Path to ritz-lang projects (default: ~/dev/ritz-lang)"
