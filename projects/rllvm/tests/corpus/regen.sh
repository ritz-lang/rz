#!/bin/bash
# Regenerate the frozen .ll corpus from ../../corpus-src/ with ritz1_selfhosted, and copy
# the two runtime shims. A person runs this after changing a source; CI
# never does. Commit the regenerated text as it comes out.
#
#   RITZ1=<path to ritz1_selfhosted> bash regen.sh
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd ../../../.. && pwd)
RITZ1=${RITZ1:-$ROOT/projects/ritz/ritz1/build/ritz1_selfhosted}
RITZ=$ROOT/projects/ritz
SRC=$ROOT/projects/rllvm/corpus-src   # not under tests/: rz test reads only test/
[ -x "$RITZ1" ] || { echo "regen.sh: no ritz1_selfhosted at $RITZ1" >&2; exit 1; }

# ritz1's sig cache skips a source it thinks unchanged and then writes no .ll;
# a fresh cache, and deleting each output first, make every file regenerate.
export RITZ_CACHE_DIR
RITZ_CACHE_DIR=$(mktemp -d)
trap 'rm -r "$RITZ_CACHE_DIR"' EXIT

# Compile from the source's directory, so its messages name it by basename.
gen() {   # gen <dir> <name> [ritz1 flags...]
    local dir=$1 name=$2
    shift 2
    rm -f "$dir/$name.ll"
    (cd "$SRC/$dir" && "$RITZ1" "$name.ritz" -o "$OLDPWD/$dir/$name.ll" -I "$RITZ" -I . "$@")
    [ -s "$dir/$name.ll" ] || { echo "regen.sh: no $dir/$name.ll" >&2; exit 1; }
}

for name in hello intrin_run intrin asm_run asm simd abi_a abi_b comdat_a comdat_b weak_strong; do
    gen hosted "$name"
done
gen freestanding pic --target x86_64-unknown-none
gen freestanding large --target x86_64-unknown-none
gen freestanding kernel --target x86_64-none-elf --no-red-zone --stack-protector

cp "$RITZ/runtime/ritz_start.x86_64.ll" hosted/shim.ll
cp "$RITZ/runtime/ritz_start.harland.x86_64.ll" freestanding/harland_start.ll
