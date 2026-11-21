#!/bin/bash
# goliath's CLI: put/get/ls over a store kept in a host file (AGAST #2788).
#
# Each command is a separate process, so every check after the first `put`
# also checks that the store file carries the data between runs. The CLI
# must also never report success for work it did not do (AGAST #2460).
set -u
cd "$(dirname "$0")"
BIN=$PWD/build/debug/goliath
[ -x "$BIN" ] || { echo "FAIL: $BIN not built"; exit 1; }
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export GOLIATH_STORE=$TMP/store
fails=0
fail() { echo "FAIL: $*"; fails=$((fails+1)); }
# expect NAME WANT_EXIT(0|nonzero) PATTERN(or '') -- CMD...
expect() {
    local name=$1 want=$2 pat=$3; shift 4
    local out rc
    out=$("$@" 2>&1 </dev/null); rc=$?
    if [ "$want" = 0 ] && [ $rc -ne 0 ]; then
        fail "$name: exit $rc, want 0: $out"; return
    fi
    if [ "$want" = nonzero ] && [ $rc -eq 0 ]; then
        fail "$name: exit 0 for work not done: $out"; return
    fi
    if [ -n "$pat" ] && ! grep -qiE -- "$pat" <<<"$out"; then
        fail "$name: output lacks /$pat/: $out"; return
    fi
    echo "ok: $name"
}

expect help        0       'usage'           -- "$BIN" --help
expect no_args     nonzero 'usage'           -- "$BIN"
expect unknown     nonzero 'unknown command' -- "$BIN" no-such-command-2460
expect put_no_arg  nonzero 'usage'           -- "$BIN" put
expect get_no_arg  nonzero 'usage'           -- "$BIN" get
expect ls_no_arg   nonzero 'usage'           -- "$BIN" ls

# Nothing stored yet: get and ls fail cleanly and don't create the store
ZERO=0000000000000000000000000000000000000000000000000000000000000000
expect get_empty   nonzero 'not found'       -- "$BIN" get $ZERO
expect ls_empty    0       ''                -- "$BIN" ls /
[ -e "$GOLIATH_STORE" ] && fail "get/ls created $GOLIATH_STORE"

# put prints the blob id: the SHA-256 of the file
printf 'hello, goliath\n' > "$TMP/hello.txt"
head -c 3000 /dev/urandom > "$TMP/bin.dat"     # binary, NULs and all
printf '' > "$TMP/empty"
for f in hello.txt bin.dat empty; do
    want=$(sha256sum < "$TMP/$f" | cut -d' ' -f1)
    got=$("$BIN" put "$TMP/$f" 2>&1); rc=$?
    if [ $rc -ne 0 ] || [ "$got" != "$want" ]; then
        fail "put $f: exit $rc, printed '$got', want '$want'"; continue
    fi
    echo "ok: put $f"
    # get, in a later process, writes back exactly the bytes put stored
    if "$BIN" get "$got" > "$TMP/out" && cmp -s "$TMP/$f" "$TMP/out"; then
        echo "ok: get $f"
    else
        fail "get $f: bytes differ from what was put"
    fi
done
[ -s "$GOLIATH_STORE" ] || fail "put left no store file at $GOLIATH_STORE"

# put is content-addressed: the same bytes again give the same id and no
# new blob
HELLO=$(sha256sum < "$TMP/hello.txt" | cut -d' ' -f1)
size_before=$(stat -c %s "$GOLIATH_STORE")
expect put_dedup   0       "^$HELLO\$"       -- "$BIN" put "$TMP/hello.txt"
size_after=$(stat -c %s "$GOLIATH_STORE")
[ "$size_after" -le "$size_before" ] || fail "put_dedup grew the store: $size_before -> $size_after"
expect get_upper   0       'hello, goliath'  -- "$BIN" get "${HELLO^^}"

# ls / lists what put linked there: id, size, name
expect ls_root     0       "^$HELLO +15 +hello\.txt\$" -- "$BIN" ls /
expect ls_root_bin 0       ' 3000 +bin\.dat$' -- "$BIN" ls /
expect ls_root_emp 0       ' 0 +empty$'      -- "$BIN" ls /
n=$("$BIN" ls / | wc -l)
[ "$n" = 3 ] && echo "ok: ls_count" || fail "ls / printed $n lines, want 3"
expect ls_file     0       "^$HELLO +15 +hello\.txt\$" -- "$BIN" ls /hello.txt
expect ls_missing  nonzero 'not found'       -- "$BIN" ls /no-such-file
expect ls_relative nonzero 'absolute'           -- "$BIN" ls hello.txt

# Bad input fails and names the problem
expect put_missing nonzero 'no-such-file'    -- "$BIN" put "$TMP/no-such-file"
expect put_dir     nonzero ''                -- "$BIN" put "$TMP"
expect get_bad_id  nonzero 'blob id'         -- "$BIN" get xyz
expect get_short   nonzero 'blob id'         -- "$BIN" get "${HELLO:1}"
expect get_unknown nonzero 'not found'       -- "$BIN" get $ZERO

# A store file that isn't one (or was damaged) is refused, not half-read,
# and put doesn't overwrite it
cp "$GOLIATH_STORE" "$TMP/good"
printf 'not a goliath store, just some text\n' > "$GOLIATH_STORE"
expect get_corrupt nonzero 'corrupt'         -- "$BIN" get "$HELLO"
expect put_corrupt nonzero 'corrupt'         -- "$BIN" put "$TMP/hello.txt"
grep -q 'not a goliath store' "$GOLIATH_STORE" || fail "put_corrupt overwrote the damaged store"
cp "$TMP/good" "$GOLIATH_STORE"
truncate -s -1 "$GOLIATH_STORE"
expect ls_truncated nonzero 'corrupt'        -- "$BIN" ls /

# Concurrent puts to one store all land (#3882). Each put is a whole-file
# read-modify-write, so without a lock the last rename drops the others'
# blobs and links while every put still exits 0.
export GOLIATH_STORE=$TMP/race/store
mkdir -p "$TMP/race"
N=12
for k in $(seq $N); do printf 'race file %s\n' "$k" > "$TMP/race/f$k"; done
pids=()
for k in $(seq $N); do "$BIN" put "$TMP/race/f$k" > "$TMP/race/out$k" 2>&1 & pids+=($!); done
for k in $(seq $N); do
    wait "${pids[$((k-1))]}" || fail "race put f$k: exit $?: $(cat "$TMP/race/out$k")"
done
n=$("$BIN" ls / 2>&1 | grep -cE ' f[0-9]+$')
[ "$n" = $N ] && echo "ok: race_ls" || fail "after $N concurrent puts ls / shows $n: $("$BIN" ls / 2>&1)"
for k in $(seq $N); do
    id=$(cat "$TMP/race/out$k")
    "$BIN" get "$id" 2>/dev/null | cmp -s - "$TMP/race/f$k" || { fail "race get f$k ($id)"; break; }
done
leftover=$(ls "$TMP/race" | grep -c '\.tmp')
[ "$leftover" = 0 ] && echo "ok: race_no_tmp" || fail "temp files left: $(ls "$TMP/race")"
# Each save writes its own temp file (<store>.tmp.<pid>), not a shared
# <store>.tmp that two writers could interleave into: a squatter there
# doesn't stop a put
mkdir "$GOLIATH_STORE.tmp"
printf 'after the squatter\n' > "$TMP/race/late"
expect put_tmp_taken 0     '^[0-9a-f]{64}$'  -- "$BIN" put "$TMP/race/late"
expect ls_tmp_taken  0     ' late$'          -- "$BIN" ls /late

# Freestanding core (AGAST #1881): the kernel builds goliath, so only the
# hosted glue (hosted.ritz: the default allocator; file_store.ritz: a host
# file; main.ritz: the CLI) may use the hosted ritzlib. The rest takes its
# memory from an Allocator (ritzlib.memory's type, imported alone) and its disk
# from a BlockDevice.
HOSTED_OK="main.ritz hosted.ritz file_store.ritz"
core=0
declare -A seen=() via=()
# closure_walk MODULE IMPORTER marks MODULE and everything it imports as
# reachable from the core, remembering the importer that pulled each one in so
# a violation can print the path.
closure_walk() {
    local mod=$1 from=$2 rel dir file dep
    [ -n "${seen[$mod]+x}" ] && return 0
    seen[$mod]=1; via[$mod]=$from
    case $mod in
        goliath.*)   rel=${mod#goliath.};   dir=src ;;
        ritzlib.*)   rel=${mod#ritzlib.};   dir=../ritz/ritzlib ;;
        cryptosec.*) rel=${mod#cryptosec.}; dir=../cryptosec/lib ;;
        # An unknown package could hide a path to ritzlib.sys, so it is a
        # failure: teach this function the package, don't assume it is safe.
        *) fail "core import closure: cannot resolve $mod (imported by ${from:-?})"; return 0 ;;
    esac
    file="$dir/${rel//.//}.ritz"
    if [ ! -f "$file" ]; then
        fail "core import closure: $mod has no file at $file (imported by ${from:-?})"
        return 0
    fi
    while read -r dep; do
        [ -n "$dep" ] && closure_walk "$dep" "$mod"
    done < <(sed -nE 's/^[[:space:]]*(pub[[:space:]]+)?import[[:space:]]+([A-Za-z_][A-Za-z0-9_.]*).*/\2/p' "$file")
}
for f in src/*.ritz; do
    case " $HOSTED_OK " in *" $(basename "$f") "*) continue;; esac
    core=$((core+1))
    # The Allocator type is ritzlib.memory's (AGAST #4120); importing it alone
    # takes no memory from the global heap.
    hits=$(grep -nE '^import ritzlib\.(sys|memory|io|fs|process)\b|\bsys_[a-z]' "$f" \
        | grep -vE '^[0-9]+:import ritzlib\.memory \{ Allocator \}$')
    [ -z "$hits" ] || fail "$f is goliath core but uses the hosted ritzlib: $hits"
    closure_walk "goliath.$(basename "$f" .ritz)" ""
done
[ "$core" -ge 8 ] && echo "ok: freestanding_core ($core modules)" || fail "freestanding check saw only $core core modules"
# The whole closure, not just direct imports (AGAST #4227): a kernel that links
# goliath links every module the core reaches, e.g. blob_id -> cryptosec.sha256
# -> ritzlib.strview -> ritzlib.memory -> ritzlib.str. Once #4119 made the
# ritzlib core freestanding, none of those paths may reach ritzlib.sys, or the
# kernel links syscall wrappers it never calls.
if [ -n "${seen[ritzlib.sys]+x}" ]; then
    chain=ritzlib.sys p=${via[ritzlib.sys]:-}
    while [ -n "$p" ]; do
        chain="$p -> $chain"
        p=${via[$p]:-}
    done
    fail "core import closure reaches ritzlib.sys: $chain"
elif [ -z "${seen[ritzlib.strview]+x}" ] || [ -z "${seen[ritzlib.memory]+x}" ]; then
    # A vacuous pass would hide a broken walk (a moved ritzlib, a new import
    # spelling) rather than a clean tree: the core is known to reach both.
    fail "core import closure is broken, not clean: reached only ${#seen[@]} modules, no ritzlib.strview/ritzlib.memory"
else
    echo "ok: freestanding_closure (${#seen[@]} modules, no ritzlib.sys)"
fi
# cryptosec's SHA-256 (BlobIds) is part of that core
grep -qE '^import ritzlib\.sys\b' ../cryptosec/lib/sha256.ritz && fail "cryptosec/lib/sha256.ritz imports ritzlib.sys"

[ $fails -eq 0 ] || { echo "$fails goliath CLI check(s) failed"; exit 1; }
