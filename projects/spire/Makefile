# Spire Makefile
#
# Build and test the Spire web framework
#
# Usage:
#   make build      - Build the library
#   make test       - Run all tests
#   make test-v     - Run tests verbose
#   make clean      - Clean build artifacts

# Compiler settings
RITZ0 = python3 ritz/ritz0/ritz0.py
RITZ1 = ./ritz/ritz1_bin
LIST_DEPS = python3 ritz/ritz0/list_deps.py
RUNTIME = ritz/runtime/ritz_start.x86_64.o

# Directories
BUILD_DIR = build
TEST_BUILD_DIR = build/test

# Colors for output
GREEN = \033[0;32m
YELLOW = \033[0;33m
RED = \033[0;31m
NC = \033[0m

.PHONY: all build test test-v test-f clean help submodules

all: build

# Initialize/update submodules
submodules:
	@echo "$(YELLOW)Updating submodules...$(NC)"
	git submodule update --init --recursive

# Build the library (compile to .ll files)
build: submodules
	@echo "$(YELLOW)Building Spire...$(NC)"
	@mkdir -p $(BUILD_DIR)
	@for f in lib/*.ritz lib/**/*.ritz; do \
		if [ -f "$$f" ]; then \
			basename=$$(basename "$$f" .ritz); \
			echo "  Compiling $$f"; \
			$(RITZ0) "$$f" -o "$(BUILD_DIR)/$$basename.ll" --no-runtime 2>/dev/null || true; \
		fi \
	done
	@echo "$(GREEN)Build complete$(NC)"

# Build test binary
build-tests: submodules
	@echo "$(YELLOW)Building tests...$(NC)"
	@mkdir -p $(TEST_BUILD_DIR)
	@./scripts/build_tests.sh
	@echo "$(GREEN)Test build complete$(NC)"

# Run all tests
test: build-tests
	@echo "$(YELLOW)Running tests...$(NC)"
	@if [ -f $(TEST_BUILD_DIR)/tests ]; then \
		$(TEST_BUILD_DIR)/tests; \
	else \
		echo "$(RED)Test binary not found. Run 'make build-tests' first.$(NC)"; \
		exit 1; \
	fi

# Run tests verbose
test-v: build-tests
	@$(TEST_BUILD_DIR)/tests -v

# Run tests with filter
# Usage: make test-f FILTER=router
test-f: build-tests
	@$(TEST_BUILD_DIR)/tests -f $(FILTER)

# Run tests quiet
test-q: build-tests
	@$(TEST_BUILD_DIR)/tests -q

# List available tests
test-list: build-tests
	@$(TEST_BUILD_DIR)/tests -l

# Clean build artifacts
clean:
	@echo "$(YELLOW)Cleaning...$(NC)"
	rm -rf $(BUILD_DIR)
	@echo "$(GREEN)Clean complete$(NC)"

# Show help
help:
	@echo "Spire Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  make build       - Build the library"
	@echo "  make test        - Run all tests"
	@echo "  make test-v      - Run tests verbose"
	@echo "  make test-q      - Run tests quiet (failures only)"
	@echo "  make test-list   - List available tests"
	@echo "  make test-f FILTER=<pattern> - Run tests matching pattern"
	@echo "  make clean       - Clean build artifacts"
	@echo "  make submodules  - Update git submodules"
	@echo "  make help        - Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make test-f FILTER=router  # Run router tests"
	@echo "  make test-f FILTER=http    # Run HTTP tests"

# Development helpers
.PHONY: dev watch

# Quick dev cycle - build and test
dev: clean build test

# Count lines of code
loc:
	@echo "Lines of code in Spire:"
	@find lib -name "*.ritz" -exec wc -l {} + | tail -1
	@echo ""
	@echo "Lines of test code:"
	@find test -name "*.ritz" -exec wc -l {} + 2>/dev/null | tail -1 || echo "  0 total"
