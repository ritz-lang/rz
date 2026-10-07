#!/bin/bash
# Golden stdout for buf_demo (examples/tier5_async/78_buf): ritzlib.buf
# (AGAST #1457).  Pins buf's CURRENT behaviour, quirks included, ahead of the
# StrView / @&String API cleanup (#1478):
#   - every `max_len` counts the NUL, so max 4 yields 3 bytes;
#   - buf_read_quoted returns -1 both for an unterminated string and when
#     max_len runs out (leaving pos inside the string);
#   - buf_skip_while takes a typed `fn(u8) -> bool` since #1671 (it was a
#     placeholder returning 0); here it skips no digits, so still 0;
#   - growbuf_ensure_cap doubles from 64; growbuf_grow sets cap exactly.
# Values were checked by hand against buf.ritz (byte counts, line:col, cap
# doubling), not just captured from a compiler.  If #1478 changes one on
# purpose, update the golden here in the same commit.
#
# Run by scripts/regression.sh once per compiler, with CWD=pkg_dir and
# ./buf_demo linked to that compiler's build.
set -uo pipefail

fail=0

# check <name> <want> <got> <rc>
check() {
    if [[ "$4" != 0 ]]; then
        echo "FAIL: $1: exit $4, want 0" >&2
        fail=1
    elif [[ "$3" != "$2" ]]; then
        echo "FAIL: $1: stdout" >&2
        diff <(echo "$2") <(echo "$3") >&2
        fail=1
    fi
}

tokens_section() { sed -n '/^== tokens ==/,$p'; }

# 1. Empty stdin: the whole program -- API section plus the built-in config.
want=$(cat <<'GOLDEN'
== api ==
from_str len: 12
pos: 0
remaining: 12
eof: 0
peek: 104
peek_at(4): 111
peek_at(-1): 0
peek_at(12): 0
peek_n(5): [hello] (5)
pos after peeks: 0
starts_with(hell): 1
starts_with(help): 0
pos after starts_with: 0
match_str(help): 0
match_str(hello): 1
pos: 5
match_char(';'): 0
match_char(','): 1
skip_whitespace: 1
advance: 119
skip_while(digit): 0
save: 8
skip_until('d'): 3
pos: 11
restore pos: 8
advance_n(100): 4
eof: 1
advance at eof: 0
peek at eof: 0
match_str("") at eof: 1
skip(7) pos: 7
skip(50) pos: 12
interior peek_at(-1): 0
interior peek_at(0): 121
interior peek_at(2): 0
init len: 9
read_while_digit (at 'a'): [] (0)
read_while_alnum: [abc123_x9] (9)
eof (len-bounded): 1
read_while_digit: [2026] (4)
read_while_digit max 3: [10] (2)
pos: 7
read_until(':'): [name] (4)
stops before delim, peek: 58
read_until max 4: [nam] (3)
pos: 3
read_until (no delim): [value] (5)
read_quoted escapes: [a\tb"c\d\nqe] (10)
pos after closing quote: 17
read_quoted (not at quote): -1
pos unchanged: 17
read_quoted unterminated: -1
  partial: [unterminated] (12)
read_quoted max 4: -1
  partial: [abc] (3)
  pos: 4
loc at 4: 2:2
loc at 7: 4:1
loc at 0: 1:1
new: len=0 cap=0 empty=1
new data null: 1
append_byte: len=1 cap=64 empty=0
append 12: len=13 cap=64 empty=0
contents: [xyz0123456789] (13)
get(0): 120
get(12): 57
get(13) (out of range): 0
get(-1) (out of range): 0
ensure_cap(64): 0
  -> len=13 cap=64 empty=0
ensure_cap(65): 0
  -> len=13 cap=128 empty=0
ensure_cap(300): 0
  -> len=13 cap=512 empty=0
grow(100) (smaller): 0
  -> len=13 cap=512 empty=0
grow(1000): 0
  -> len=13 cap=1000 empty=0
contents kept: [xyz0123456789] (13)
+1000 bytes: len=1013 cap=2000 empty=0
get(13 + 999): 108
clear: len=0 cap=2000 empty=1
get(0) after clear: 0
free: len=0 cap=0 empty=1
free data null: 1
with_cap(10): len=0 cap=10 empty=1
with_cap(0): len=0 cap=0 empty=1
with_cap(-5): len=0 cap=0 empty=1
== tokens ==
source: builtin
bytes: 124
1:1 comment [built-in config]
2:1 section [server]
3:1 key [host]
3:8 string [example.org]
4:1 key [port]
4:8 number [8080]
6:1 comment [motd]
7:1 key [motd]
7:8 string [hi\tthere]
8:1 key [name]
8:8 bare [web 01]
9:1 key [id]
9:6 bare [42abc]
10:1 key [oops]
10:5 error expected '=' (got 10)
11:1 error expected key (got 61)
items: 10
end: 12:1
GOLDEN
)
out=$(./buf_demo </dev/null); rc=$?
check "empty stdin (builtin config)" "$want" "$out" "$rc"

# 2. Config on stdin via read_all_fd: CRLF line endings, an escaped quote,
#    a space+tab indent, a trailing comment, a key cut short by '-', a stray
#    quote, and a string left unterminated at EOF.
want=$(cat <<'GOLDEN'
== tokens ==
source: stdin
bytes: 83
1:1 section [db]
2:1 key [user]
2:8 string [ad"min]
3:3 key [port]
3:8 number [5432]
3:13 comment [trailing]
4:1 key [bad]
4:4 error expected '=' (got 45)
5:1 error expected key (got 39)
6:1 key [x]
6:5 string unterminated
items: 7
end: 7:1
GOLDEN
)
out=$(printf '[db]\r\nuser = "ad\\"min"\r\n \tport=5432 # trailing\nbad-key = 1\n\x27open\nx = "never closed\n' | ./buf_demo); rc=$?
check "stdin config" "$want" "$(echo "$out" | tokens_section)" "$rc"

# 3. Input larger than read_all_fd's 4096-byte chunk: 600 lines of
#    `kNNN = NNN\n` (600 x 11 = 6600 bytes) must arrive whole and in order,
#    so the last line is still parsed, at 600:1.
want=$(cat <<'GOLDEN'
source: stdin
bytes: 6600
600:1 key [k599]
600:8 number [599]
items: 600
end: 601:1
GOLDEN
)
out=$(for i in $(seq 0 599); do printf 'k%03d = %03d\n' "$i" "$i"; done | ./buf_demo); rc=$?
check "stdin > 4096 bytes" "$want" "$(echo "$out" | tokens_section | sed -n '2,3p'; echo "$out" | tail -4)" "$rc"

[[ "$fail" == 0 ]] || exit 1
echo "buf_demo: all cases passed"
