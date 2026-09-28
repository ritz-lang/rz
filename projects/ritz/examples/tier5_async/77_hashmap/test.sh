#!/bin/bash
# Golden stdout for hashmap_demo (examples/tier5_async/77_hashmap):
# ritzlib.hashmap + ritzlib.hash + ritzlib.eq (AGAST #1458).
#
# The hash values are the FNV-1a 64-bit reference values (fnv1a_str("a") =
# af63dc4c8601ec8c and fnv1a_str("foobar") = 85944171f73967e8 are the
# published test vectors); the rest were computed by an independent Python
# model of FNV-1a and of hashmap.ritz's probe/tombstone/grow rules, not by
# running either compiler.
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./hashmap_demo linked to that compiler's build.
set -uo pipefail

fail=0

# check <name> <want> <got> <rc>
check() {
    set -- "$1" "${2%$'\n'}" "$3" "$4"   # goldens below end in a newline
    if [[ "$4" != 0 ]]; then
        echo "FAIL: $1: exit $4, want 0" >&2
        fail=1
    elif [[ "$3" != "$2" ]]; then
        echo "FAIL: $1: stdout" >&2
        diff <(echo "$2") <(echo "$3") >&2
        fail=1
    fi
}

words_section() { sed -n '/^== words ==/,$p'; }

# 1. Empty stdin: the whole program, counting the built-in sentence.
want_builtin='
== hash ==
fnv1a_init: cbf29ce484222325
fnv1a_str(""): cbf29ce484222325
fnv1a_str("a"): af63dc4c8601ec8c
fnv1a_str("foobar"): 85944171f73967e8
fnv1a_str("hashmap"): a5348588797c432d
fnv1a_byte(init, 255): af64724c8602eb6e
hash_i32(0): 4d25767f9dce13f5
hash_i32(-1): 994f76653e2a3951
hash_i32(305419896): cccfd053e47c3365
hash_i64(0): a8c7f832281a39c5
hash_i64(42): ff3add6b3789daef
hash_i64(-42): eeb07d2ce8108904
hash_u64(1): 89cd31291d2aefa4
hash_u64(hash_i64(42)): 0ab075faa6eaf897
fnv1a_i32/i64/u64 chain: 34493c839c113e9b
== eq ==
eq_i32(3, 3): 1
eq_i32(3, -3): 0
eq_i64(1 << 40, 1 << 40): 1
eq_i64(-1, 1): 0
eq_i64(1, -1): 0
eq_u64(hash a, hash a): 1
eq_u64(hash a, hash b): 0
== map ==
with_cap(100).cap: 128
new.len: 0
new.is_empty: 1
new.cap: 16
after 20 inserts len: 20
after 20 inserts cap: 32
get(49): 7
get(361): 19
contains(50): 0
get(50) (missing): 0
update get(49): 700
update len: 20
remove(49): 1
remove(49) again: 0
contains(49): 0
len after remove: 19
sum of values: 183
reinsert len: 20
get(-5): 55
get(1 << 62): 62
clear len: 0
clear is_empty: 1
clear cap: 32
clear get(0): 0
drop cap: 0
== words ==
source: builtin
words: 30
distinct: 22
cap: 32
the: 6
remove the: 1
remove the again: 0
distinct without the: 21
iterated: 21
a 1
and 1
barks 1
barn 1
brown 1
cat 1
dog 2
fox 2
in 1
jumps 1
lazy 1
naps 1
near 1
old 1
over 1
quick 2
red 1
runs 1
spot 1
sunny 1
warm 1
'
out=$(./hashmap_demo </dev/null); rc=$?
check "empty stdin (builtin text)" "${want_builtin#$'\n'}" "$out" "$rc"

# 2. Text on stdin: case folding, digits, punctuation as separators, and a
#    "the" stop word to remove.
want_text='
== words ==
source: stdin
words: 18
distinct: 13
cap: 32
the: 2
remove the: 1
remove the again: 0
distinct without the: 12
iterated: 12
2nd 1
42 2
again 1
and 1
answer 1
be 2
is 2
not 1
or 1
question 1
that 1
to 2
'
out=$(printf 'To be, or not to be: THAT is the question.\nThe 2nd answer is 42 -- and 42 again!\n' | ./hashmap_demo); rc=$?
check "stdin text" "${want_text#$'\n'}" "$(echo "$out" | words_section)" "$rc"

# 3. 30 distinct words and no "the": the table grows twice (16 -> 32 -> 64),
#    and removing an absent key reports 0.
want_grow='
== words ==
source: stdin
words: 32
distinct: 30
cap: 64
the: 0
remove the: 0
remove the again: 0
distinct without the: 30
iterated: 30
w1 1
w10 1
w11 1
w12 1
w13 1
w14 1
w15 1
w16 1
w17 1
w18 1
w19 1
w2 1
w20 1
w21 1
w22 1
w23 1
w24 1
w25 1
w26 1
w27 1
w28 1
w29 1
w3 1
w30 1
w4 1
w5 1
w6 1
w7 3
w8 1
w9 1
'
out=$( (for i in $(seq 1 30); do printf 'w%d ' "$i"; done; echo w7 W7) | ./hashmap_demo); rc=$?
check "stdin grow" "${want_grow#$'\n'}" "$(echo "$out" | words_section)" "$rc"

[[ "$fail" == 0 ]] || exit 1
echo "hashmap_demo: all cases passed"
