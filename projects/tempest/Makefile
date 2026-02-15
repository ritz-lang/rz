# Tempest Browser - Build System
#
# TDD-focused build system using ritz0 and ritzunit.

# Paths to ritz ecosystem
RITZ_ROOT ?= $(HOME)/dev/ritz-lang
RITZ_PATH = $(RITZ_ROOT)/ritz
RITZUNIT_PATH = $(RITZ_ROOT)/ritzunit
RITZLIB_PATH = $(RITZ_PATH)/ritzlib

# Compilers and tools
RITZ0 = python3 $(RITZ_PATH)/ritz0/ritz0.py
LIST_DEPS = python3 $(RITZ_PATH)/ritz0/list_deps.py
RUNTIME = $(RITZ_PATH)/runtime/ritz_start.x86_64.o

# Use RERITZ syntax mode (e.g., [[test]] instead of @test)
export RITZ_SYNTAX=reritz

# Build directories
BUILD_DIR = build
BIN_DIR = $(BUILD_DIR)/bin
LL_DIR = $(BUILD_DIR)/ll

# Source files
BROWSER_SOURCES = src/main.ritz
TAB_SOURCES = src/tab_process.ritz
LIB_SOURCES = $(wildcard lib/*.ritz)
TEST_SOURCES = $(wildcard tests/*.ritz)

# Output binaries
BROWSER_BIN = $(BIN_DIR)/tempest
TAB_BIN = $(BIN_DIR)/tempest-tab
TEST_BIN = $(BUILD_DIR)/tests

.PHONY: all clean build test check dirs test-verbose test-list

all: build

# Create build directories
dirs:
	@mkdir -p $(BUILD_DIR) $(BIN_DIR) $(LL_DIR)

# Build browser binary (placeholder - full build needs more deps)
build: dirs
	@echo "Building Tempest browser..."
	@echo "(Full build requires Prism, Iris, etc. - using check for now)"
	$(MAKE) check

# Run tests (main TDD entry point)
test: dirs
	@echo "=== Building Tempest Tests ==="
	@./scripts/build_tests.sh
	@echo ""
	@echo "=== Running Tests ==="
	@$(BUILD_DIR)/tempest_tests

# Verbose test output
test-verbose: dirs
	@./scripts/build_tests.sh
	@$(BUILD_DIR)/tempest_tests -v

# List tests without running
test-list: dirs
	@./scripts/build_tests.sh
	@$(BUILD_DIR)/tempest_tests -l

# Type check without building
check: dirs
	@echo "Type checking..."
	@for f in $(LIB_SOURCES); do \
		echo "  Checking $$f"; \
		$(RITZ0) "$$f" -o /dev/null --no-runtime 2>&1 || exit 1; \
	done
	@echo "Type check complete."

# Clean build artifacts
clean:
	rm -rf $(BUILD_DIR)

# Show help
help:
	@echo "Tempest Browser Build System"
	@echo ""
	@echo "TDD Targets:"
	@echo "  test          - Build and run all tests"
	@echo "  test-verbose  - Run tests with verbose output"
	@echo "  test-list     - List all tests without running"
	@echo ""
	@echo "Build Targets:"
	@echo "  all           - Build everything (default)"
	@echo "  build         - Build browser binaries"
	@echo "  check         - Type check without building"
	@echo "  clean         - Remove build artifacts"
	@echo "  help          - Show this help"
	@echo ""
	@echo "Environment:"
	@echo "  RITZ_ROOT     - Path to ritz-lang projects (default: ~/dev/ritz-lang)"
