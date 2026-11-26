#!/usr/bin/env bash
# Stage 2 == stage 3: ritz1_selfhosted rebuilds itself byte for byte (AGAST #4822).
#
#   bash projects/builder/check_fixed_point.sh [<ritz1 dir>]   # default projects/ritz/ritz1
#
# stage 1 is build/ritz1 (ritz0 compiled it), stage 2 is build/ritz1_selfhosted
# (stage 1 compiled it), both from `make -C projects/ritz ritz1-bootstrap`.
# Stage 3 is what stage 2 makes of the same sources.  The bootstrap has
# reached its fixed point when stage 3 is the same file as stage 2.
#
# Stage 3 is built by ritz1's own Makefile, so it gets exactly the module
# list, ritzlib objects, link order and flags that stage 2 got: in a copy of
# build/ with the stage-2 IR and objects removed, and RITZ1 pointed at stage
# 2.  build/ itself is left as it was.  Exit 0 identical, 1 different, 2 setup.
set -euo pipefail

dir="${1:-projects/ritz/ritz1}"
cd "$dir" || { echo "check_fixed_point: no directory $dir" >&2; exit 2; }
stage2=build/ritz1_selfhosted
[[ -x "$stage2" ]] || { echo "check_fixed_point: $dir/$stage2 missing; run make -C projects/ritz ritz1-bootstrap" >&2; exit 2; }

b3=build-stage3
rm -rf "$b3"
trap 'rm -rf "$b3"' EXIT
cp -a build "$b3"
# Only the ritz1-compiled half is rebuilt: ritzlib's objects come from ritz0
# through the artifact store in both stages, and the runtime shim is shared.
find "$b3" -maxdepth 1 \( -name '*_sh.ll' -o -name '*_sh.o' -o -name '*_sh.d' -o -name 'ritz1_selfhosted' \) -delete

echo "=== stage 3: ritz1 built by ritz1_selfhosted ==="
# clang warns once per module about the target triple; show make's output
# only when it fails.
if ! make -s -j"$(nproc)" BUILD_DIR="$b3" RITZ1="$stage2" RITZ1_SELFHOSTED="$b3/ritz1_stage3" \
        "$b3/ritz1_stage3" > "$b3/stage3.log" 2>&1; then
    tail -40 "$b3/stage3.log" >&2
    echo "check_fixed_point: building stage 3 failed" >&2
    exit 2
fi

s2="$(sha256sum < "$stage2" | cut -d' ' -f1)"
s3="$(sha256sum < "$b3/ritz1_stage3" | cut -d' ' -f1)"
n="$(find "$b3" -maxdepth 1 -name '*_sh.ll' | wc -l)"
echo "stage 2 $s2"
echo "stage 3 $s3"
if [[ "$s2" != "$s3" ]]; then
    for ll in "$b3"/*_sh.ll; do
        cmp -s "$ll" "build/${ll##*/}" || echo "  differs: ${ll##*/}"
    done
    echo "✗ stage 2 != stage 3: ritz1_selfhosted does not rebuild itself ($n modules)" >&2
    exit 1
fi
echo "✓ stage 2 == stage 3 ($n modules)"
