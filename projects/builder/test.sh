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
#   - pytest runs (a package's test.sh may call it);
#   - ritz1_selfhosted runs (usage) and compiles a file to IR;
#   - the entrypoint builds and tests a hello package mounted read-only,
#     writes /out, and the binary prints the expected line;
#   - a package that does not compile exits non-zero, with summary.json ok false;
#   - with the commit's tree mounted as RZ_ROOT, an in-tree package outside
#     projects/ builds with the image's compiler and the mount is unchanged;
#   - no package argument exits 2;
#   - `rz build --all --compiler ritz1_selfhosted` builds every package the
#     image ships, so the shipped sources are complete;
#   - the tree has no .git, no checkout, no test corpus the build ignores;
#   - the unpacked image size is within the budget in README.md.
#
# RITZ1_JOBS, when set, is the bootstrap's make -j (see ritz1-jobs.sh).
# Unset keeps that script's cap. It is not the image default.
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
    # A root container can leave root-owned files on a bind mount. Remove
    # what we can, then ask a root container to remove the rest. The trap
    # must not turn a green run into exit 1.
    if [[ -n ${work:-} && -d $work ]]; then
        rm -rf "$work" 2>/dev/null || true
        if [[ -d $work ]]; then
            local cleaner=${tag:-${boot_tag:-}}
            if [[ -n $cleaner ]]; then
                docker run --rm --network=none --user 0 --entrypoint rm \
                    -v "$work:/cleanup" "$cleaner" -rf /cleanup >/dev/null 2>&1 || true
            fi
            rm -rf "$work" 2>/dev/null || true
        fi
    fi
    if [[ $keep -eq 0 && ${#images[@]} -gt 0 ]]; then
        docker image rm "${images[@]}" >/dev/null 2>&1 || true
    fi
    return 0
}
trap cleanup EXIT

echo "=== context: git archive ${commit:0:12} ==="
git -C "$ROOT" archive --format=tar "$commit" > "$work/context.tar"

build() {
    local -a jobs=()
    # Only when the caller set it. An empty build-arg would still be the cap,
    # but leaving it off keeps the Dockerfile's own default in the cache key.
    if [[ -n ${RITZ1_JOBS:-} ]]; then
        jobs+=(--build-arg "RITZ1_JOBS=${RITZ1_JOBS}")
    fi
    docker build -f projects/builder/Dockerfile "${jobs[@]}" "$@" - < "$work/context.tar"
}

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

# The image ENTRYPOINT is rz-builder. These probes name the program.
# A relative path is resolved from WORKDIR /rz; a bare name is PATH.
run() { docker run --rm --network=none --entrypoint "$1" "$tag" "${@:2}"; }

echo "=== checks ==="
label() { docker image inspect "$tag" --format "{{ index .Config.Labels \"$1\" }}"; }
[[ "$(label dev.ritz.rz.commit)" == "$commit" ]] && ok "label dev.ritz.rz.commit is $commit" \
    || bad "label dev.ritz.rz.commit is '$(label dev.ritz.rz.commit)', want $commit"
[[ "$(label dev.ritz.ritz1-selfhosted.sha256)" == "$sha" ]] && ok "label dev.ritz.ritz1-selfhosted.sha256 is the shipped binary's" \
    || bad "label dev.ritz.ritz1-selfhosted.sha256 is '$(label dev.ritz.ritz1-selfhosted.sha256)', want $sha"

# Every tool the survey found a build calling (README.md, "Native tools").
for t in clang ld.lld lld-link llvm-ar as ld readelf objcopy ar nm objdump python3; do
    if out="$(run "$t" --version 2>&1)"; then ok "$t runs: $(head -1 <<<"$out")"; else bad "$t --version: $out"; fi
done
# rllvm's and razm's test.sh run `python3 -m pytest` (AGAST #4847).
if out="$(run python3 -m pytest --version 2>&1)"; then ok "pytest runs: $(head -1 <<<"$out")"; else bad "python3 -m pytest --version: $out"; fi
major="$(run clang --version | sed -n 's/.*clang version \([0-9]*\).*/\1/p' | head -1)"
[[ "$major" == "$LLVM_MAJOR" ]] && ok "clang is LLVM $LLVM_MAJOR" || bad "clang is LLVM '$major', want $LLVM_MAJOR"

# ritz1_selfhosted has no --version: its usage line shows the loader and libc
# resolved, and compiling a file shows it works.
usage="$(run projects/ritz/ritz1/build/ritz1_selfhosted 2>&1 || true)"
grep -q '^Usage: ritz1 ' <<<"$usage" && ok "ritz1_selfhosted runs (usage)" || bad "ritz1_selfhosted: $usage"
ir="$(run sh -c 'printf "fn main() -> i32\n    42\n" > /tmp/m.ritz && projects/ritz/ritz1/build/ritz1_selfhosted /tmp/m.ritz -o /tmp/m.ll && grep -c "^define" /tmp/m.ll' 2>&1)" \
    && ok "ritz1_selfhosted compiles a file to IR ($ir definitions)" || bad "ritz1_selfhosted compile: $ir"

# hello: a package outside the image's tree, mounted read-only. The
# entrypoint builds and tests it and writes /out. The mount must not change.
mkdir -p "$work/hello/src" "$work/hello/test" "$work/hello-out"
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
hello_before=$(find "$work/hello" -type f -print0 | sort -z | xargs -0 sha256sum)
set +e
# seccomp=unconfined: the default profile rejects io_uring_* with EPERM.
docker run --rm --network=none --security-opt seccomp=unconfined \
    -v "$work/hello:/src/projects/hello:ro" \
    -v "$work/hello-out:/out" \
    "$tag" /src/projects/hello >"$work/hello-entry.log" 2>&1
hello_rc=$?
set -e
hello_after=$(find "$work/hello" -type f -print0 | sort -z | xargs -0 sha256sum)
hello_ok=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("ok"))' \
    "$work/hello-out/summary.json" 2>/dev/null || echo missing)
hello_passed=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["test"].get("passed"))' \
    "$work/hello-out/summary.json" 2>/dev/null || echo missing)
if [[ $hello_rc -eq 0 && $hello_ok == True && $hello_passed == 1 && $hello_before == "$hello_after" ]]; then
    ok "hello: entrypoint builds and tests a read-only mount, summary ok, 1 test"
else
    bad "hello entrypoint rc=$hello_rc ok=$hello_ok tests=$hello_passed mount-unchanged=$([[ $hello_before == "$hello_after" ]] && echo yes || echo no)"
    sed 's/^/     | /' "$work/hello-entry.log" | tail -30
fi
hello_bin=$(docker run --rm --network=none --security-opt seccomp=unconfined \
    --entrypoint /out/bin/hello \
    -v "$work/hello-out:/out:ro" "$tag" 2>"$work/hello-bin.log" || true)
if [[ $hello_bin == "Hello from the Ritz builder" ]]; then
    ok "hello binary from /out prints the expected line"
else
    bad "hello binary printed '$hello_bin'"; sed 's/^/     | /' "$work/hello-bin.log"
fi

# A package that does not compile: non-zero exit, summary.json ok false.
mkdir -p "$work/bad/src" "$work/bad-out"
cat > "$work/bad/ritz.toml" <<'EOF'
[package]
name = "bad"
version = "0.1.0"
sources = ["src"]

[[bin]]
name = "bad"
entry = "main::main"
EOF
cat > "$work/bad/src/main.ritz" <<'EOF'
fn main() -> i32
    this is not ritz
EOF
set +e
docker run --rm --network=none --security-opt seccomp=unconfined \
    -v "$work/bad:/src/projects/bad:ro" \
    -v "$work/bad-out:/out" \
    "$tag" /src/projects/bad >"$work/bad-entry.log" 2>&1
bad_rc=$?
set -e
bad_ok=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("ok"))' \
    "$work/bad-out/summary.json" 2>/dev/null || echo missing)
if [[ $bad_rc -ne 0 && $bad_ok == False ]]; then
    ok "a package that does not compile exits $bad_rc and summary ok is false"
else
    bad "bad package rc=$bad_rc summary ok=$bad_ok, want non-zero and false"
    sed 's/^/     | /' "$work/bad-entry.log" | tail -20
fi

# main.yml's builder-matrix form (AGAST #4847): the commit's whole tree
# mounted read-only as RZ_ROOT, an in-tree package outside projects/, built
# only (it has no tests), by the image's own compiler, which the checkout
# lacks. The mount must not change.
mkdir -p "$work/ws" "$work/ws-out"
tar -C "$work/ws" -xf "$work/context.tar"
ws_pkg=bench/regressions/2026-05-04/s2_module_init
ws_before=$(find "$work/ws" -type f -print0 | sort -z | xargs -0 sha256sum)
set +e
docker run --rm --network=none --security-opt seccomp=unconfined \
    -e RZ_ROOT=/ws -v "$work/ws:/ws:ro" -v "$work/ws-out:/out" \
    "$tag" --build-only "$ws_pkg" >"$work/ws-entry.log" 2>&1
ws_rc=$?
set -e
ws_after=$(find "$work/ws" -type f -print0 | sort -z | xargs -0 sha256sum)
ws_ritz1=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("ritz1_sha256"))' \
    "$work/ws-out/summary.json" 2>/dev/null || echo missing)
if [[ $ws_rc -eq 0 && $ws_ritz1 == "$sha" && $ws_before == "$ws_after" ]]; then
    ok "a mounted workspace (RZ_ROOT): $ws_pkg builds with the image's ritz1_selfhosted, mount unchanged"
else
    bad "mounted workspace rc=$ws_rc ritz1=$ws_ritz1 (want $sha) mount-unchanged=$([[ $ws_before == "$ws_after" ]] && echo yes || echo no)"
    sed 's/^/     | /' "$work/ws-entry.log" | tail -30
fi

set +e
docker run --rm --network=none --security-opt seccomp=unconfined \
    "$tag" >"$work/usage.log" 2>&1
usage_rc=$?
set -e
[[ $usage_rc -eq 2 ]] && ok "no package argument exits 2" \
    || bad "no package argument exited $usage_rc, want 2"

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
