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

[ $fails -eq 0 ] || { echo "$fails goliath CLI check(s) failed"; exit 1; }
