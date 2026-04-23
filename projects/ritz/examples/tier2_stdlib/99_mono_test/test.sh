#!/bin/bash
# Smoke test for the monomorphization example — just verify the prints.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

got=$(./mono_test)
[[ "$got" == *"OK: vec_len works"* ]] || fail "expected 'OK: vec_len works' in output, got: $got"

echo "ok - 1 mono_test scenario"
