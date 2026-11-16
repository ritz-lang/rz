#!/bin/bash
# Golden stdout for json_walk (examples/tier5_async/79_ritzlib_json):
# ritzlib.json (AGAST #1459).  Pins json's CURRENT behaviour, quirks included:
#   - json_parse2 reports every failure as code 1 (JSON_ERR_UNEXPECTED_CHAR);
#     pos is where the parser stopped (end of input for "[1, 2" and "\"open");
#   - numbers are integers: -1.25 parses as -125, -0012 as -12;
#   - input after the first value is ignored: "[1] x" parses as [1];
#   - an unknown escape copies the character: "\/" decodes to "/".
# Byte counts, tallies, paths and error positions were checked by hand
# against json.ritz, not just captured from a compiler.  If a fix to
# json.ritz changes one on purpose, update the golden here in the same commit.
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./json_walk linked to that compiler's build.
set -uo pipefail

fail=0

# check <name> <want> <got> <want_rc> <rc>
check() {
    if [[ "$5" != "$4" ]]; then
        echo "FAIL: $1: exit $5, want $4" >&2
        fail=1
    elif [[ "$3" != "$2" ]]; then
        echo "FAIL: $1: stdout" >&2
        diff <(echo "$2") <(echo "$3") >&2
        fail=1
    fi
}

doc_section() { sed '/^== lookup ==/,$d'; }

# 1. Empty stdin: the whole program -- built-in doc walked and re-emitted,
#    typed lookups and accessor defaults, malformed inputs, message table.
want=$(cat <<'GOLDEN'
== doc ==
source: builtin
bytes: 189
$ object {6}
.name string |ritz| "ritz"
.version number 3
.stable bool 0
.tags array [2]
.tags[0] string |compiler| "compiler"
.tags[1] string |self-hosted| "self-hosted"
.owner null is_null=1
.meta object {5}
.meta.tier number 5
.meta.ratio number -125
.meta.quote string |say "hi"<9>now| "say \"hi\"\tnow"
.meta.empty array [0]
.meta.none object {0}
count null: 1
count bool: 1
count number: 3
count string: 4
count array: 2
count object: 3
emit: {"name": "ritz", "version": 3, "stable": false, "tags": ["compiler", "self-hosted"], "owner": null, "meta": {"tier": 5, "ratio": -125, "quote": "say \"hi\"\tnow", "empty": [], "none": {}}}
roundtrip: identical
== lookup ==
name: ritz
version: 3
stable: 0
tags len: 2
tags[1]: self-hosted
tags[2] (out of range): (null)
tags[2] is_null: 1
tags[2] == null: 1
tags[-1]: (null)
owner is_null: 1
name is_null: 0
meta object_len: 5
meta.tier: 5
meta.ratio (-1.25): -125
meta.quote: say "hi"<9>now
meta.empty array_len: 0
meta.none object_len: 0
missing == null: 1
missing is_null: 1
missing number: 0
missing bool: 0
missing string: (null)
name.x (field of string): (null)
name as number: 0
version as string: (null)
version as bool: 0
meta array_len: 0
tags object_len: 0
root[0]: 1
== errors ==
missing colon: error: code=1 pos=5 msg=unexpected character
  legacy: ok=0 pos=5 error=JSON parse error
  failed: 1
unclosed array: error: code=1 pos=5 msg=unexpected character
  legacy: ok=0 pos=5 error=JSON parse error
  failed: 1
unterminated string: error: code=1 pos=5 msg=unexpected character
  legacy: ok=0 pos=5 error=JSON parse error
  failed: 1
bad literal: error: code=1 pos=6 msg=unexpected character
  legacy: ok=0 pos=6 error=JSON parse error
  failed: 1
empty input: error: code=1 pos=0 msg=unexpected character
  legacy: ok=0 pos=0 error=JSON parse error
  failed: 1
trailing input (accepted): ok [1]
  legacy: ok=1
  failed: 0
message 0: unknown error
message 1: unexpected character
message 2: unterminated string
message 3: expected ':'
message 4: expected ']'
message 5: expected '}'
message 6: out of memory
message 7: unknown error
GOLDEN
)
out=$(./json_walk </dev/null); rc=$?
check "empty stdin (builtin doc)" "$want" "$out" 0 "$rc"

# 2. A document on stdin: newlines and indentation, every escape json.ritz
#    decodes (\n \t \" \\) plus an unknown one (\/), a leading-zero negative
#    number, and nested/empty objects.  Emission normalises the layout and
#    re-parsing the emitted text gives the same text back.
want=$(cat <<'GOLDEN'
== doc ==
source: stdin
bytes: 77
$ object {3}
.k array [3]
.k[0] bool 1
.k[1] null is_null=1
.k[2] string |a<10>b<9>"q" \ /| "a\nb\t\"q\" \\ /"
.n number -12
.o object {1}
.o.x object {0}
count null: 1
count bool: 1
count number: 1
count string: 1
count array: 1
count object: 3
emit: {"k": [true, null, "a\nb\t\"q\" \\ /"], "n": -12, "o": {"x": {}}}
roundtrip: identical
GOLDEN
)
out=$(printf '{\n  "k": [true, null, "a\\nb\\t\\"q\\" \\\\ \\/"],\n  "n": -0012,\n  "o": {"x": {}}\n}\n' | ./json_walk); rc=$?
check "stdin doc" "$want" "$(echo "$out" | doc_section)" 0 "$rc"

# 3. Malformed stdin: the Result's Err is reported and the program exits 1
#    before the lookup and error sections.  `{"a" 1}` stops at the '1' (pos 5).
want=$(cat <<'GOLDEN'
== doc ==
source: stdin
bytes: 7
error: code=1 pos=5 msg=unexpected character
GOLDEN
)
out=$(printf '{"a" 1}' | ./json_walk); rc=$?
check "malformed stdin" "$want" "$out" 1 "$rc"

# 4. Input larger than vec_read_all_fd's 4096-byte chunk: [1, 2, ..., 1000, 0]
#    is 4896 bytes and must arrive whole -- 1001 elements, the last one 0.
want=$(cat <<'GOLDEN'
bytes: 4896
$ array [1001]
[999] number 1000
[1000] number 0
count number: 1001
count array: 1
index len == null: 1
index len+100 == null: 1
roundtrip: identical
GOLDEN
)
out=$(for i in $(seq 1 1000); do printf '%d, ' "$i"; done | { printf '['; cat; printf '0]'; } | ./json_walk); rc=$?
check "stdin > 4096 bytes" "$want" "$(echo "$out" | sed -n '/^bytes:/p;/^\$ /p;/^\[999\] /p;/^\[1000\] /p;/^count/p;/^index/p;/^roundtrip/p')" 0 "$rc"

[[ "$fail" == 0 ]] || exit 1
echo "json_walk: all cases passed"
