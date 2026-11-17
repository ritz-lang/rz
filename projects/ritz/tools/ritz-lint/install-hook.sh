#!/bin/bash
#
# Install ritz-lint as a pre-commit hook
#
# Usage:
#   cd your-project
#   <ritz-lang checkout>/projects/ritz/tools/ritz-lint/install-hook.sh
#
# The hook calls the ritz_lint.py that sits next to this script (AGAST #1838:
# there used to be a second copy under projects/larb, and both installers
# pointed at that one through $RITZ_PATH).
#

set -e

# Find the git root
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$GIT_ROOT" ]; then
    echo "Error: Not in a git repository"
    exit 1
fi

HOOK_PATH="$GIT_ROOT/.git/hooks/pre-commit"
LINT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ritz_lint.py"

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

LINT_PATH="@LINT_PATH@"

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

# The heredoc is quoted (no expansion in the hook body), so fill in the
# linter's absolute path here.
sed -i "s|@LINT_PATH@|$LINT_PATH|" "$HOOK_PATH"
chmod +x "$HOOK_PATH"

echo "Pre-commit hook installed at $HOOK_PATH"
echo ""
echo "The hook will run ritz-lint on staged .ritz files before each commit."
echo "To bypass (not recommended): git commit --no-verify"
