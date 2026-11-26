#!/usr/bin/env bash
# Build the builder image from a clean checkout of one commit and test it by
# running it (AGAST #4822).
#
#   bash projects/builder/test.sh [--keep] [--reproducible] [<commit>]
#
# <commit> defaults to HEAD.  The build context is `git archive <commit>`:
# no work-tree changes, no .git, no build products.  Two passes, as the
# Dockerfile's header describes: the bootstrap stage (which checks stage 2 ==
# stage 3 itself), then the runtime image labelled with the commit and
# ritz1_selfhosted's sha256.
#
# Then, in the image:
#   - the labels name the commit and the shipped binary's sha256;
#   - every native tool the survey found runs, and clang is CI's major;
#   - ritz1_selfhosted runs (usage) and compiles a file to IR;
#   - a hello package (outside the image's tree) builds, its [[test]] passes
#     under `rz test`, and its binary prints the expected line;
#   - `rz build --all --compiler ritz1_selfhosted` builds every package the
#     image ships, so the shipped sources are complete;
#   - the tree has no .git, no checkout, no test corpus the build ignores;
#   - the unpacked image size is within the budget in README.md.
#
#   --reproducible  rebuild the bootstrap stage with --no-cache and require
#                   the same ritz1_selfhosted sha256
#   --keep          keep the images (default: remove them when done)
#
# Docker: DOCKER_CONFIG is honoured.  Exit 0 = every check passed.
set -euo pipefail

keep=0 repro=0 rev=HEAD
for a in "$@"; do
    case "$a" in
        --keep) keep=1 ;;
        --reproducible) repro=1 ;;
        -h|--help) sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//;$d'; exit 0 ;;
        -*) echo "test.sh: unknown option $a" >&2; exit 2 ;;
        *) rev="$a" ;;
    esac
done

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
commit="$(git -C "$ROOT" rev-parse --verify "$rev^{commit}")"
LLVM_MAJOR=21   # CI's CLANG_VERSION (.github/workflows/main.yml)
BUDGET_MIB=400  # unpacked; README.md, "Size"

fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }

work="$(mktemp -d)"
boot_tag="rz-builder-bootstrap:${commit:0:12}"
images=()
cleanup() {
    rm -rf "$work"
    if [[ $keep -eq 0 && ${#images[@]} -gt 0 ]]; then
        docker image rm "${images[@]}" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

echo "=== context: git archive ${commit:0:12} ==="
git -C "$ROOT" archive --format=tar "$commit" > "$work/context.tar"

build() { docker build -f projects/builder/Dockerfile "$@" - < "$work/context.tar"; }

echo "=== pass 1: bootstrap stage ==="
build --target bootstrap -t "$boot_tag"
images+=("$boot_tag")
sha="$(docker run --rm "$boot_tag" sha256sum projects/ritz/ritz1/build/ritz1_selfhosted | cut -d' ' -f1)"
echo "ritz1_selfhosted sha256 $sha"

if [[ $repro -eq 1 ]]; then
    echo "=== reproducible: bootstrap again, no cache ==="
    build --no-cache --target bootstrap -t "$boot_tag-again"
    images+=("$boot_tag-again")
    sha2="$(docker run --rm "$boot_tag-again" sha256sum projects/ritz/ritz1/build/ritz1_selfhosted | cut -d' ' -f1)"
    [[ "$sha2" == "$sha" ]] && ok "a no-cache rebuild makes the same ritz1_selfhosted ($sha)" \
        || bad "a no-cache rebuild made ritz1_selfhosted $sha2, the first $sha"
fi

tag="rz-builder:${commit:0:12}-${sha:0:12}"
echo "=== pass 2: runtime image $tag ==="
build --build-arg "RZ_COMMIT=$commit" --build-arg "RITZ1_SHA256=$sha" -t "$tag"
images+=("$tag")

run() { docker run --rm -i "$tag" "$@"; }

echo "=== checks ==="
label() { docker image inspect "$tag" --format "{{ index .Config.Labels \"$1\" }}"; }
[[ "$(label dev.ritz.rz.commit)" == "$commit" ]] && ok "label dev.ritz.rz.commit is $commit" \
    || bad "label dev.ritz.rz.commit is '$(label dev.ritz.rz.commit)', want $commit"
[[ "$(label dev.ritz.ritz1-selfhosted.sha256)" == "$sha" ]] && ok "label dev.ritz.ritz1-selfhosted.sha256 is the shipped binary's" \
    || bad "label dev.ritz.ritz1-selfhosted.sha256 is '$(label dev.ritz.ritz1-selfhosted.sha256)', want $sha"

# Every tool the survey found a build calling (README.md, "Native tools").
for t in clang ld.lld lld-link llvm-ar as ld readelf objcopy ar python3; do
    if out="$(run "$t" --version 2>&1)"; then ok "$t runs: $(head -1 <<<"$out")"; else bad "$t --version: $out"; fi
done
major="$(run clang --version | sed -n 's/.*clang version \([0-9]*\).*/\1/p' | head -1)"
[[ "$major" == "$LLVM_MAJOR" ]] && ok "clang is LLVM $LLVM_MAJOR" || bad "clang is LLVM '$major', want $LLVM_MAJOR"

# ritz1_selfhosted has no --version: its usage line shows the loader and libc
# resolved, and compiling a file shows it works.
usage="$(run projects/ritz/ritz1/build/ritz1_selfhosted 2>&1 || true)"
grep -q '^Usage: ritz1 ' <<<"$usage" && ok "ritz1_selfhosted runs (usage)" || bad "ritz1_selfhosted: $usage"
ir="$(run sh -c 'printf "fn main() -> i32\n    42\n" > /tmp/m.ritz && projects/ritz/ritz1/build/ritz1_selfhosted /tmp/m.ritz -o /tmp/m.ll && grep -c "^define" /tmp/m.ll' 2>&1)" \
    && ok "ritz1_selfhosted compiles a file to IR ($ir definitions)" || bad "ritz1_selfhosted compile: $ir"

# hello: a package outside the image's tree, piped in, built, tested, run.
mkdir -p "$work/hello/src" "$work/hello/test"
cat > "$work/hello/ritz.toml" <<'EOF'
[package]
name = "hello"
version = "0.1.0"
sources = ["src"]

[[bin]]
name = "hello"
entry = "main::main"
EOF
cat > "$work/hello/src/main.ritz" <<'EOF'
import ritzlib.io

fn main() -> i32
    print("Hello from the Ritz builder\n")
    0
EOF
cat > "$work/hello/test/test_hello.ritz" <<'EOF'
[[test]]
fn test_arithmetic() -> i32
    assert 2 + 3 == 5
    0
EOF
hello="$(tar -C "$work" -cf - hello | run sh -c '
    set -e; mkdir -p /work; tar -C /work -xf -
    ./rz build /work/hello --compiler ritz1_selfhosted >&2
    ./rz test /work/hello --compiler ritz1_selfhosted >&2
    /work/hello/build/debug/hello' 2>"$work/hello.log")" || true
if [[ "$hello" == "Hello from the Ritz builder" ]]; then
    ok "hello builds, passes rz test and runs in the container"
else
    bad "hello in the container printed '$hello'"; sed 's/^/     | /' "$work/hello.log"
fi

if run ./rz build --all --compiler ritz1_selfhosted > "$work/all.log" 2>&1; then
    ok "rz build --all under ritz1_selfhosted: $(grep -c '^PKG PASS' "$work/all.log") packages, every one the image ships"
else
    bad "rz build --all under ritz1_selfhosted"; grep -E 'PKG FAIL|✗' "$work/all.log" | sed 's/^/     | /'
fi

# What must not ship.  test/ ships only where a manifest lists it as sources
# (stage_tree.py); a corpus no manifest builds would be in one of these.
# (Debian's own __pycache__ under /usr is its precompiled stdlib: fine.)
stray="$(run sh -c 'find / -xdev \( -name .git -o -path /src -o -path /opt/venv \) -print 2>/dev/null; find /rz \( -name .ritz-cache\* -o -name __pycache__ -o -path "*/ritzlib/tests" -o -path "*/examples/tier*" \) -print 2>/dev/null' || true)"
[[ -z "$stray" ]] && ok "no .git, checkout, caches or ritzlib/example test corpora in the image" \
    || { bad "the image ships what it must not:"; sed 's/^/     | /' <<<"$stray"; }

# The budget is on the unpacked filesystem, measured inside the image:
# `docker image inspect .Size` is the compressed content size under the
# containerd image store and the unpacked size under overlay2, so it would
# mean different things on different hosts.
mib=$(( ($(run du -sxk / | cut -f1) + 1023) / 1024 ))
echo "image $tag: $mib MiB unpacked (budget $BUDGET_MIB MiB); docker reports $(docker image inspect "$tag" --format '{{.Size}}') bytes"
[[ $mib -le $BUDGET_MIB ]] && ok "image size $mib MiB is within the $BUDGET_MIB MiB budget" \
    || bad "image size $mib MiB is over the $BUDGET_MIB MiB budget"

echo
if [[ $fails -eq 0 ]]; then echo "builder image $tag: all checks passed"; exit 0; fi
echo "builder image $tag: $fails check(s) failed"; exit 1
