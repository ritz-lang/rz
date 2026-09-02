#!/usr/bin/env bash
# End-to-end proof that Stage 5 turns a real, allowlist-silenced ritz1 vs
# ritz1_selfhosted divergence into a non-zero exit.
#
# WHY THIS EXISTS
# ---------------
# scripts/test-regression-stage5.sh proves the Stage 5 *logic* hermetically in
# under a second, and that is the test you should run routinely.  It does not,
# however, prove that Stage 5 is actually wired into the suite's exit code, nor
# that the allowlist really fails to silence it when the allowlist is consulted
# by the genuine stage-3/stage-4 code paths.  This script proves that end to
# end, by reconstructing the exact CI failure the gate missed.
#
# The real divergence (tier5_async_49_ritzgen under CI's older clang) is not
# reproducible on every box, so we synthesise one instead:
#
#   1. Copy regression.sh, and patch the copy so ritz1_selfhosted
#      unconditionally rejects one example that plainly compiles under both.
#   2. Point the copy at a temporary allowlist = the real list + that example.
#      Stage 4 therefore reports the rejection as a benign "known, allowlisted"
#      SKIP and contributes zero failures -- precisely the situation in which
#      the old gate exited 0.
#   3. Assert the suite now exits 1, and that Stage 5 is what made it red.
#
# Nothing tracked is modified: the patched script and the synthetic allowlist
# are temporary files, removed on exit.  In particular the real
# regression-known-failures-*.txt files are never written to.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# An example that unambiguously compiles under every stage, so that the ONLY
# reason the sets can diverge is the injection below.
VICTIM="tier1_basics_01_hello"

TMP_ALLOW="$(mktemp /tmp/stage5-synthetic-allowlist.XXXXXX.txt)"
PATCHED="$SCRIPT_DIR/.stage5-synthetic-regression.sh"
LOG="$(mktemp /tmp/stage5-synthetic-run.XXXXXX.log)"
cleanup() { rm -f "$PATCHED" "$TMP_ALLOW"; }
trap cleanup EXIT

# --- 1. synthetic allowlist: the real ritz1 list, plus the victim -----------
cat "$SCRIPT_DIR/regression-known-failures-ritz1.txt" > "$TMP_ALLOW"
echo "$VICTIM" >> "$TMP_ALLOW"

# --- 2. patched copy of the suite -------------------------------------------
cp "$SCRIPT_DIR/regression.sh" "$PATCHED"

# Resolve ritz1/ritz1_selfhosted to the synthetic list instead of the real one.
python3 - "$PATCHED" "$TMP_ALLOW" <<'PY'
import sys
path, allowlist = sys.argv[1], sys.argv[2]
s = open(path).read()

old_resolve = '        ritz1|ritz1_selfhosted) echo "$SCRIPT_DIR/regression-known-failures-ritz1.txt" ;;'
new_resolve = '        ritz1|ritz1_selfhosted) echo "%s" ;;' % allowlist
assert s.count(old_resolve) == 1, "allowlist resolution line not found -- update this proof"
s = s.replace(old_resolve, new_resolve)

# Inject the divergence: self-hosted ritz1 rejects the victim outright.
old_compile = '        if ! compile_with "ritz1_selfhosted" "$src" "$bin" 2>/dev/null; then'
new_compile = ('        if [[ "$name" == "%s" ]] || ! compile_with "ritz1_selfhosted" "$src" "$bin" 2>/dev/null; then'
               % "SYNTHETIC_VICTIM")
assert s.count(old_compile) == 1, "stage 4 compile site not found -- update this proof"
s = s.replace(old_compile, new_compile)

open(path, 'w').write(s)
PY
sed -i "s/SYNTHETIC_VICTIM/$VICTIM/" "$PATCHED"
chmod +x "$PATCHED"

# --- 3. run it ---------------------------------------------------------------
echo "Running the suite with a synthetic ritz1/ritz1_selfhosted divergence on:"
echo "  $VICTIM  (rejected by ritz1_selfhosted, and allowlisted so Stage 4 skips it)"
echo ""
cd "$(dirname "$SCRIPT_DIR")" || exit 2
rm -rf .regression
"$PATCHED" > "$LOG" 2>&1
rc=$?

echo "--- relevant output -------------------------------------------------"
grep -E "Stage [345]:|$VICTIM|fixed point|allowlist|regression tests" "$LOG" || true
echo "--- exit code: $rc --------------------------------------------------"
echo "(full log: $LOG)"
echo ""

# --- 4. assert ---------------------------------------------------------------
status=0
check() {
    if eval "$2"; then echo "ok: $1"; else echo "FAIL: $1"; status=1; fi
}

check "suite exits non-zero"                      "[[ $rc -ne 0 ]]"
check "Stage 4 reports the victim as allowlisted" \
      "grep -q '$VICTIM: self-hosted ritz1 compile failed (known, allowlisted)' '$LOG'"
check "Stage 4 itself records zero failures"      "grep -q 'Stage 4: .* 0 failed' '$LOG'"
check "Stage 5 is the stage that failed"          "grep -q 'Stage 5: FAILED' '$LOG'"
check "Stage 5 names the divergent example"       \
      "grep -q '$VICTIM: accepted by ritz1, REJECTED by ritz1_selfhosted' '$LOG'"
check "Stage 5 says the allowlist cannot help"    "grep -q 'NOT allowlistable' '$LOG'"

echo ""
if [[ $status -eq 0 ]]; then
    echo "PROVEN: an allowlist-silenced self-hosting divergence now exits 1."
else
    echo "NOT PROVEN -- Stage 5 did not catch the synthetic divergence."
fi
exit $status
