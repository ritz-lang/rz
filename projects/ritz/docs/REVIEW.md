# Reviewing a Ritz diff

The checklist a reviewer (or `/ritz-review`, or you before you commit) applies to
a diff. The idioms are in [`RITZ_NOT_C.md`](RITZ_NOT_C.md) and the rules they cite
in [`STANDARD.md`](STANDARD.md).

`c"strings"` are only for C interop, where the callee can't take a length and
needs NUL termination; null termination is unsafe and heavily discouraged
wherever a safer API exists. If the only API for something takes NUL-terminated
`*u8`, the fix is a `StrView` API in ritzlib, not a `c""` at the call site.

Each item is marked:

- **ENFORCED** (and the tool): a gate fails on it. The review still reads the
  diff, because a ratchet counts and doesn't judge.
- **JUDGE**: no tool catches it. The reviewer does.

A finding cites the item and the line: `A1 ritzlib/foo.ritz:42`. Any A item is a
reject unless the diff justifies it in a comment at the site.

## Part A: C in Ritz clothing

Look at **added** lines (`+` in the diff); code the diff only moves is not a
finding.

| # | Signal in the diff | Ritz form | Status |
|---|---|---|---|
| A1 | `c"` outside an interop boundary. Reject unless the diff says which callee needs the NUL and why no `StrView` API exists | `"..."` (a `StrView`); add the `StrView` API to ritzlib | ENFORCED: `make tools-ratchets` pins each project's `c"` count down-only (`tools/test_standard_callers.py`), and the compilers refuse a `c"` in a `StrView` slot. Whether a site is a real boundary: JUDGE (S-TEXT-1) |
| A2 | a call of a `*_cstr(` helper (`eprints_cstr`, `eq_cstr`, `starts_with_cstr`) | the `StrView` form (`eprints`, `.eq`, `.starts_with`) | ENFORCED where the helper is `standard-exempt`: the callers pin in `tools/test_standard_callers.py`. JUDGE otherwise (S-TEXT-1) |
| A3 | `strcmp`, `strlen`, `memcmp`, `memcpy` or a hand-rolled NUL scan in app code | `StrView`/`Span` methods, `String`, `Vec` | JUDGE (S-TEXT-1, S-OWN-2) |
| A4 | a new Ritz API with a `*u8` text parameter, or a pointer + length pair | `StrView` / `Span<T>` | JUDGE; counted by `standard_report.py` (`raw-ptr-param`, `ptr-len-param`) (S-PTR-1, S-PTR-2) |
| A5 | `-> i32` (or `i64`) returning a status, `0`/`-1` or a raw errno | `Result<T, E>` with a named error enum | ENFORCED in the modules pinned under `tools/test_standard_pins/` (`status-return`, `make tools-unit`); JUDGE elsewhere (S-RESULT-1, S-RESULT-2) |
| A6 | an out-parameter (`*T`, `@&T`, `:&`) carrying a result beside a status | return a struct, `Option` or `Result` | ENFORCED in the pinned modules (`out-param`); JUDGE elsewhere (S-RESULT-3) |
| A7 | `!= 0` / `== 0` on a bool, an integer as a condition, `-> i32` for yes/no | `bool` | ENFORCED: the compilers refuse a bool/integer mix and a non-bool condition (S-BOOL-1, S-BOOL-3). A predicate returning `i32`: ENFORCED in the pinned modules (`bool-return`), JUDGE elsewhere (S-BOOL-2) |
| A8 | `null` returned or tested for "nothing here" | `Option<T>` | JUDGE; counted by `standard_report.py` (`null-return`) (S-OPTION-1) |
| A9 | `malloc`/`free` outside an owning type; cleanup repeated before each `return` | an owning type with `Drop`; `defer` | JUDGE; counted (`raw-alloc`) (S-OWN-2, S-OWN-4) |
| A10 | a raw `sys_*` call in app code | the ritzlib wrapper (`fs`, `fd`, `process`, `time`) | ENFORCED where the `sys_*` fn is `standard-exempt`: the callers pin. JUDGE otherwise (S-RESULT-2) |
| A11 | a `switch`-style table. Three shapes: a `match` arm for a case an earlier `return` already handled (a dead arm); one condition re-tested in several checks in a row (`(op == Eq or op == Ne) and ...` three times); `_ =>` giving a real output in a table from an enum to output (`_ => "add i64 "`) | each case is handled in one place; test the shared condition once and nest the checks under it; list every variant, with the ones that have no output giving an error. A `_` that means "none of these" (`false`, `None`, `pass`) is fine | JUDGE (S-MATCH-3) |

## Part B: the change as a whole

| # | Check | Status |
|---|---|---|
| B1 | A new public API has a test that calls it | JUDGE |
| B2 | No new `standard-exempt`, allowlist or `known-failures/` entry without a stated reason | ENFORCED for the form: an exemption without a key and a reason counts as `exempt-malformed` (pinned at 0 in `tools/test_standard_pins/`), and a known failure must cite its AGAST ticket (`tools/known_failures.py`). Whether the reason holds: JUDGE |
| B3 | Pins move down only. A diff that raises a pin is a reject, except a callers pin raised by the commit that newly exempts that API, naming it | ENFORCED upward by the ratchets (`make tools-ratchets`, `make tools-unit`); the pin edit in the diff: JUDGE |
| B4 | No follow-on tickets: the diff finishes its job, adjacent fixes included | JUDGE |

## Output

One line per finding (`<item> <file>:<line>: <what>; <Ritz form>`), then a
verdict: **ACCEPT** (no findings), or **REJECT** with the findings that block.
An item marked JUDGE that you decided to let through is listed with the reason.
