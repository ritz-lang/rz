#!/usr/bin/env bash
# Run one package through the published builder image and fail on a build
# or test failure, or a run that reports zero tests (AGAST #4825, #4826).
# main.yml's builder-matrix job calls this once per matrix entry.
#
#   run_builder_package.sh <image> <package-rel-path> <out-dir>
#
#   <image>              the builder image ref to run, e.g.
#                        ghcr.io/ritz-lang/rz-builder:main
#   <package-rel-path>   workspace-relative package path, e.g.
#                        projects/buddhafinger
#   <out-dir>            host directory for the container's /out; created
#                        if missing
#
# Mounts <package-rel-path> read-only and runs the image's entrypoint
# (AGAST #4823) on it, which builds and tests with ritz1_selfhosted, the
# image's own compiler, never the default. --network=none: the run needs
# none. --security-opt seccomp=unconfined: Docker's default profile returns
# EPERM for io_uring_setup / io_uring_enter / io_uring_register, and
# ritzlib's tests call them.
#
# The container's own exit status is already 0 only when the build
# succeeded and every test passed (projects/builder/README.md); this script
# adds one more check the image can't make for itself: a package whose
# summary reports zero tests passed is a silently-empty run, not a green
# one, so it fails here even though the container exited 0 (projects/
# builder/summary.py's "No tests found, skipping" parses to passed=0,
# ok=true -- correct for a library with none, but a result this script
# cannot tell apart from the suite not running at all without the count).
#
# Exit: 0 built, tested, at least one test passed; 1 the container's own
# failure, a missing summary.json, or zero tests passed; 2 bad arguments.
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "usage: run_builder_package.sh <image> <package-rel-path> <out-dir>" >&2
    exit 2
fi
image=$1 pkg=$2 out=$3
[[ -f "$pkg/ritz.toml" ]] || {
    echo "run_builder_package: no ritz.toml in '$pkg'" >&2
    exit 2
}

mkdir -p "$out"
docker run --rm --network=none --security-opt seccomp=unconfined \
    -v "$PWD/$pkg:/src/$pkg:ro" \
    -v "$out:/out" \
    "$image" "/src/$pkg"

summary="$out/summary.json"
[[ -f "$summary" ]] || {
    echo "run_builder_package: $pkg: $summary is missing after the run" >&2
    exit 1
}
python3 - "$summary" "$pkg" <<'PY'
import json
import sys

summary_path, pkg = sys.argv[1], sys.argv[2]
summary = json.loads(open(summary_path).read())
if not summary.get("ok"):
    print(f"run_builder_package: {pkg}: run not ok: {json.dumps(summary)}", file=sys.stderr)
    sys.exit(1)
passed = summary.get("test", {}).get("passed", 0)
if passed <= 0:
    print(f"run_builder_package: {pkg}: ran zero tests: {json.dumps(summary)}", file=sys.stderr)
    sys.exit(1)
print(f"run_builder_package: {pkg}: {passed} test(s) passed")
PY
