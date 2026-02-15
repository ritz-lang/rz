#!/bin/bash
#
# Install ritz-lint as a pre-commit hook
#
# Usage:
#   cd your-project
#   $RITZ_PATH/larb/tools/ritz-lint/install-hook.sh
#

set -e

# Find the git root
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$GIT_ROOT" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Check RITZ_PATH
if [ -z "$RITZ_PATH" ]; then
    echo "Error: RITZ_PATH not set"
    echo "Set it to your ritz-lang directory:"
    echo "  export RITZ_PATH=~/dev/ritz-lang"
    exit 1
fi

HOOK_PATH="$GIT_ROOT/.git/hooks/pre-commit"
LINT_PATH="$RITZ_PATH/larb/tools/ritz-lint/ritz_lint.py"

# Check if lint script exists
if [ ! -f "$LINT_PATH" ]; then
    echo "Error: ritz-lint not found at $LINT_PATH"
    exit 1
fi

# Create pre-commit hook
cat > "$HOOK_PATH" << 'HOOK'
#!/bin/bash
#
# Ritz pre-commit hook
# Runs ritz-lint on staged .ritz files
#

set -e

# Get staged .ritz files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.ritz$' || true)

if [ -z "$STAGED_FILES" ]; then
    # No .ritz files staged, skip
    exit 0
fi

echo "Running ritz-lint on staged files..."

# Check RITZ_PATH
if [ -z "$RITZ_PATH" ]; then
    echo "Warning: RITZ_PATH not set, skipping lint"
    exit 0
fi

LINT_PATH="$RITZ_PATH/larb/tools/ritz-lint/ritz_lint.py"

if [ ! -f "$LINT_PATH" ]; then
    echo "Warning: ritz-lint not found, skipping"
    exit 0
fi

# Run lint on each file
FAILED=0
for FILE in $STAGED_FILES; do
    if [ -f "$FILE" ]; then
        echo "  Checking $FILE..."
        if ! python3 "$LINT_PATH" "$FILE" --no-color; then
            FAILED=1
        fi
    fi
done

if [ $FAILED -ne 0 ]; then
    echo ""
    echo "Lint errors found. Fix them before committing."
    echo "To bypass (not recommended): git commit --no-verify"
    exit 1
fi

echo "Lint passed!"
HOOK

chmod +x "$HOOK_PATH"

echo "Pre-commit hook installed at $HOOK_PATH"
echo ""
echo "The hook will run ritz-lint on staged .ritz files before each commit."
echo "To bypass (not recommended): git commit --no-verify"
