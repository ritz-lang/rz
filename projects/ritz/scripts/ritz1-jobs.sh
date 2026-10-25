#!/bin/sh
# Print the -j level for building ritz1 (AGAST #1802).
#
# RITZ1_JOBS overrides it; otherwise min(nproc, 8).  A cap, not a bare -j or
# nproc: the WSL VM shared by the gate and the task rooms has ~15 GB, and a
# cold -j8 ritz1 bootstrap adds ~3.4 GB at peak.  An empty, zero or
# non-numeric override falls back to the default rather than becoming -j0.
# tools/run_regression_matrix.py:ritz1_make_jobs() mirrors this rule.
j="${RITZ1_JOBS:-}"
case "$j" in
    ''|*[!0-9]*|0*)
        j=$(nproc 2>/dev/null || echo 1)
        [ "$j" -gt 8 ] && j=8
        ;;
esac
echo "$j"
