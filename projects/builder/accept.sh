#!/bin/bash
# Host `./rz` versus the builder image, one package at a time (AGAST #4823).
#
#   bash projects/builder/accept.sh <image>
#
# <image> is the tag test.sh printed (`rz-builder:<commit12>-<sha12>`).
# For each package below, the host runs `./rz build` and `./rz test` with
# `--compiler ritz1_selfhosted` and `RITZ1` pointing at that binary, and the
# container runs the image entrypoint on the same sources mounted read-only.
# The two must agree on pass/fail and on the test counts. The container
# writes bins, objects, logs and summary.json under a fresh directory, gets
# no network, and must not modify the mount.
#
#   hosted:        ritzlib's tests, sage, rzsh (its Linux bin), tome
#   freestanding:  indium's hello, the one PIC userspace bin
#   build only:    harland's kernel ELF (no QEMU in the image)
#
# The host compiler is projects/ritz/ritz1/build/ritz1_selfhosted. If it is
# missing, it is copied out of the image (glibc forward-compatible).
# Exit 0 when every case agrees.
set -euo pipefail

ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
cd "$ROOT"
SUMMARY="$ROOT/projects/builder/summary.py"
tag=${1:-}
if [[ -z $tag || $tag == -h || $tag == --help ]]; then
    sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'
    exit 2
fi
docker image inspect "$tag" >/dev/null

RITZ1=$ROOT/projects/ritz/ritz1/build/ritz1_selfhosted
if [[ ! -x $RITZ1 ]]; then
    echo "=== copying ritz1_selfhosted out of $tag ==="
    mkdir -p "$(dirname "$RITZ1")"
    cid=$(docker create --entrypoint true "$tag")
    docker cp "$cid:/rz/projects/ritz/ritz1/build/ritz1_selfhosted" "$RITZ1"
    docker rm "$cid" >/dev/null
    chmod +x "$RITZ1"
fi
# Same unversioned LLVM names the image puts first on PATH (llvm-ar-21 is
# not what find_llvm_tool looks up).
export PATH="/usr/lib/llvm-21/bin:${PATH}"
export RITZ1

fails=0
ok()  { echo "ok   - $1"; }
bad() { echo "FAIL - $1"; fails=$((fails + 1)); }

work=$(mktemp -d)
cleanup() {
    if [[ -n ${work:-} && -d $work ]]; then
        rm -rf "$work" 2>/dev/null || true
        if [[ -d $work && -n ${tag:-} ]]; then
            docker run --rm --network=none --user 0 --entrypoint rm \
                -v "$work:/cleanup" "$tag" -rf /cleanup >/dev/null 2>&1 || true
            rm -rf "$work" 2>/dev/null || true
        fi
    fi
    return 0
}
trap cleanup EXIT

fingerprint() {
    find "$1" -type f ! -path '*/build/*' ! -path '*/.git/*' -print0 \
        | sort -z | xargs -0 sha256sum
}

# host_rz <pkg> <build-only 0|1> <logdir>
# Prints nothing. Writes build.log, test.log, build.rc, test.rc, counts.json.
host_rz() {
    local pkg=$1 build_only=$2 dir=$3
    mkdir -p "$dir"
    set +e
    ./rz build "$pkg" --compiler ritz1_selfhosted >"$dir/build.log" 2>&1
    echo $? >"$dir/build.rc"
    if [[ $build_only -eq 0 && $(cat "$dir/build.rc") -eq 0 ]]; then
        ./rz test "$pkg" --compiler ritz1_selfhosted >"$dir/test.log" 2>&1
        echo $? >"$dir/test.rc"
        python3 "$SUMMARY" parse-test "$dir/test.log" "$(cat "$dir/test.rc")" \
            >"$dir/counts.json"
    else
        : >"$dir/test.log"
        echo skipped >"$dir/test.rc"
        echo '{"skipped": true}' >"$dir/counts.json"
    fi
    set -e
}

# container_run <pkg-arg> <build-only 0|1> <outdir> [mount-src] [mount-dest]
container_run() {
    local pkg=$1 build_only=$2 out=$3
    mkdir -p "$out"
    # seccomp=unconfined: Docker's default profile returns EPERM for
    # io_uring_setup / io_uring_enter / io_uring_register. ritzlib's tests
    # call them, and the host kernel allows them.
    local -a args=(docker run --rm --network=none --security-opt seccomp=unconfined -v "$out:/out")
    if [[ $# -ge 5 ]]; then
        args+=(-v "$4:$5:ro")
    fi
    args+=("$tag")
    if [[ $build_only -eq 1 ]]; then
        args+=(--build-only)
    fi
    args+=("$pkg")
    set +e
    "${args[@]}" >"$out/entrypoint.log" 2>&1
    echo $? >"$out/entrypoint.rc"
    set -e
}

# compare <name> <hostdir> <outdir> <build-only>
compare() {
    local name=$1 host=$2 out=$3 build_only=$4
    local hrc
    hrc=$(cat "$host/build.rc")
    if [[ ! -f $out/summary.json ]]; then
        bad "$name: no summary.json (entrypoint $(cat "$out/entrypoint.rc"))"
        sed 's/^/     | /' "$out/entrypoint.log" | tail -40
        return
    fi
    # build.exit lives one level down; pull it with python.
    local hb cb
    hb=$hrc
    cb=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["build"]["exit"])' "$out/summary.json")
    if [[ $hb == "$cb" ]]; then
        ok "$name: build exit $hb on the host and in the container"
    else
        bad "$name: build exit host $hb, container $cb"
        tail -20 "$host/build.log" | sed 's/^/     host | /'
        tail -20 "$out/build.log" | sed 's/^/     box  | /'
    fi
    if [[ $build_only -eq 1 ]]; then
        return
    fi
    local htc ctc
    htc=$(cat "$host/test.rc")
    ctc=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))["test"]; print("skipped" if d.get("skipped") else d.get("exit"))' "$out/summary.json")
    if [[ $htc == "$ctc" ]]; then
        ok "$name: test exit $htc on the host and in the container"
    else
        bad "$name: test exit host $htc, container $ctc"
    fi
    python3 - "$host/counts.json" "$out/summary.json" "$name" <<'PY' || fails=$((fails + 1))
import json, sys
host = json.load(open(sys.argv[1]))
box = json.load(open(sys.argv[2]))["test"]
name = sys.argv[3]
keys = ("files", "files_passed", "passed", "failed")
if host.get("skipped") or box.get("skipped"):
    if host.get("skipped") and box.get("skipped"):
        print(f"ok   - {name}: tests skipped on both sides")
        sys.exit(0)
    print(f"FAIL - {name}: test counts missing host={host} container={box}")
    sys.exit(1)
if any(host.get(k) != box.get(k) for k in keys):
    print(f"FAIL - {name}: counts host={ {k: host.get(k) for k in keys} } container={ {k: box.get(k) for k in keys} }")
    sys.exit(1)
print(f"ok   - {name}: {host['passed']} tests, {host['files_passed']}/{host['files']} files, {host['failed']} failed")
PY
}

# elf_kind <path> prints EXEC or DYN or missing
elf_kind() {
    if [[ ! -f $1 ]]; then
        echo missing
        return
    fi
    readelf -h "$1" | sed -n 's/^ *Type: *\([A-Z]*\).*/\1/p' | head -1
}

stage_indium_pic() {
    local dest=$1
    mkdir -p "$dest/user"
    cp "$ROOT/projects/indium/user/hello.ritz" "$dest/user/hello.ritz"
    cp "$ROOT/projects/indium/user/linker_pie.ld" "$dest/user/linker_pie.ld"
    cat >"$dest/ritz.toml" <<'EOF'
[package]
name = "indium-hello"
version = "0.1.0"
description = "One indium PIC userspace bin, for the builder acceptance"
sources = ["user"]

[[bin]]
name = "hello"
entry = "hello::main"
target = "x86_64-unknown-none"
target_os = "harland"
sources = ["user"]
freestanding = true
link_runtime = true

[bin.hello.linker]
script = "user/linker_pie.ld"

[bin.hello.flags]
pic = true
EOF
}

# run_mounted <name> <rel-under-root> <build-only>
run_mounted() {
    local name=$1 rel=$2 build_only=$3
    local src=$ROOT/$rel
    local mout=$work/$name/out
    echo "=== $name: host ./rz, then the container on a read-only mount ==="
    local before after
    before=$(fingerprint "$src")
    host_rz "$src" "$build_only" "$work/$name/host"
    container_run "/src/$rel" "$build_only" "$mout" "$src" "/src/$rel"
    after=$(fingerprint "$src")
    if [[ $before == "$after" ]]; then
        ok "$name: the read-only source mount was not modified"
    else
        bad "$name: the source mount changed"
    fi
    compare "$name" "$work/$name/host" "$mout" "$build_only"
    # The entrypoint's own exit is the verdict, and it must match summary.ok.
    local want have
    have=$(cat "$mout/entrypoint.rc")
    want=$(python3 -c 'import json,sys; print(0 if json.load(open(sys.argv[1]))["ok"] else 1)' "$mout/summary.json" 2>/dev/null || echo missing)
    if [[ -f $mout/summary.json && $have == "$want" ]]; then
        ok "$name: entrypoint exit $have matches summary.ok"
    else
        bad "$name: entrypoint exit $have, summary wants $want"
    fi
}

run_mounted ritzlib "projects/ritz/ritzlib/tests" 0
run_mounted sage "projects/sage" 0
run_mounted rzsh "projects/rzsh" 0
run_mounted tome "projects/tome" 0

echo "=== rzsh: the Linux bin is a hosted ELF, in the container output ==="
if [[ -f $work/rzsh/out/bin/rzsh.linux ]] && readelf -l "$work/rzsh/out/bin/rzsh.linux" | grep -q 'ld-linux'; then
    ok "rzsh.linux in /out requests the Linux loader"
else
    bad "rzsh.linux missing from /out or it has no Linux interpreter"
    ls -l "$work/rzsh/out/bin" 2>/dev/null | sed 's/^/     | /' || true
fi

echo "=== indium: one PIC userspace bin ==="
mkdir -p "$work/indium-src/projects"
stage_indium_pic "$work/indium-src/projects/indium-hello"
# The mount path contains projects/, so the copy lands at projects/indium-hello
# beside the image's libraries. This package is not in the repo, so the
# steps below match run_mounted without joining ROOT.
indium_src=$work/indium-src/projects/indium-hello
echo "=== indium-hello: host ./rz, then the container ==="
before=$(fingerprint "$indium_src")
host_rz "$indium_src" 0 "$work/indium-hello/host"
container_run "/src/projects/indium-hello" 0 "$work/indium-hello/out" \
    "$indium_src" "/src/projects/indium-hello"
after=$(fingerprint "$indium_src")
[[ $before == "$after" ]] && ok "indium-hello: the read-only source mount was not modified" \
    || bad "indium-hello: the source mount changed"
compare indium-hello "$work/indium-hello/host" "$work/indium-hello/out" 0
host_kind=$(elf_kind "$indium_src/build/debug/hello.elf")
box_kind=$(elf_kind "$work/indium-hello/out/bin/hello.elf")
if [[ $host_kind == DYN && $box_kind == DYN ]]; then
    ok "indium hello.elf is a PIC (DYN) ELF on the host and in the container"
else
    bad "indium hello.elf type host=$host_kind container=$box_kind, want DYN"
fi
have=$(cat "$work/indium-hello/out/entrypoint.rc")
want=$(python3 -c 'import json,sys; print(0 if json.load(open(sys.argv[1]))["ok"] else 1)' \
    "$work/indium-hello/out/summary.json" 2>/dev/null || echo missing)
[[ -f $work/indium-hello/out/summary.json && $have == "$want" ]] \
    && ok "indium-hello: entrypoint exit $have matches summary.ok" \
    || bad "indium-hello: entrypoint exit $have, summary wants $want"

echo "=== harland: kernel ELF, build only, in-tree path ==="
host_rz "$ROOT/projects/harland" 1 "$work/harland/host"
container_run "projects/harland" 1 "$work/harland/out"
compare harland "$work/harland/host" "$work/harland/out" 1
host_kind=$(elf_kind "$ROOT/projects/harland/build/debug/harland.elf")
box_kind=$(elf_kind "$work/harland/out/bin/harland.elf")
if [[ $host_kind == EXEC || $host_kind == DYN ]] && [[ $box_kind == "$host_kind" ]]; then
    ok "harland.elf is a $host_kind ELF on the host and in the container"
else
    bad "harland.elf type host=$host_kind container=$box_kind"
fi
have=$(cat "$work/harland/out/entrypoint.rc")
want=$(python3 -c 'import json,sys; print(0 if json.load(open(sys.argv[1]))["ok"] else 1)' \
    "$work/harland/out/summary.json" 2>/dev/null || echo missing)
[[ -f $work/harland/out/summary.json && $have == "$want" ]] \
    && ok "harland: entrypoint exit $have matches summary.ok" \
    || bad "harland: entrypoint exit $have, summary wants $want"

echo
if [[ $fails -eq 0 ]]; then
    echo "builder acceptance ($tag): every case agrees"
    exit 0
fi
echo "builder acceptance ($tag): $fails check(s) failed"
exit 1
