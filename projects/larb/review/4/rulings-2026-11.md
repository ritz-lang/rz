# LARB rulings: open language decisions, 2026-11-06

Rulings on the groups `rz` sent on 2026-11-06, taken as a whole, at `cc4d6a8`.
Each ruling is also on its AGAST ticket. **None of this is in
`LANGUAGE_SPEC.md` yet**, because that file is compile-gated: each
implementation ticket writes its own spec entry when both compilers do it.

## Summary

| # | Question | Ruling | Sites to migrate | Ticket |
|---|---|---|---|---|
| R1 | `@T` meets `T` (#2227, #2249 slot rule, #2325) | Types don't bend to slots. The only implicit borrow is a place into a `:&` parameter | about 140 | #2335, #2336, #2337, #2338 |
| R1 | `@x` into `@&T` / `:&` | **Aaron's call.** Recommend rejecting | 1155, by tool | #2339 |
| R2 | Lifetimes (#2249) | Still no annotations; a definite reference to a local at `return` is an error | 0 found | #2340 |
| R3 | `"..."` as `*u8` (#2226) | A literal takes `*u8` from any slot; nothing else converts | 1, plus 5 test sites | #2341 |
| R4 | int/bool (#2228) | `bool` is its own type. No truthiness | 136 errors, 39 files | #2342 |
| R5 | `[N]T1` to `[N]T2` (#2303) | Same element type only | 0 | #2343 |
| R6 | `match` (#2245) | Non-exhaustive is an error, everywhere | 2 | #2344 |
| R7 | `asm` (#1825) | Specified below; direction is declared | 11 lines | #1825 |
| R8 | Standard (#1344, #1320) | Start after this merges and #2339 is answered, in two stages | n/a | #1344 |

## How the groups really split

`rz` drew five groups. Measuring moved one boundary:

- **One question, not three:** #2227, the slot half of #2249, and #2325 all ask
  what happens when a value and a slot differ by one level of indirection.
  §13.4's "the destination decides" is itself an implicit conversion. R1 answers
  them together, along with #2293 part 2, #2280, #2281, #2291 and #2313.
- **#2249's lifetime half is separate** (R2).
- **#2226, #2228 and #2303 share a principle:** a conversion that changes the
  representation or loses information must be written out. §7.5 already says so
  for scalars at `let` and `var`. By that principle #1444 (narrowing at `=`,
  arguments and `return`) should go the same way. It wasn't in this batch and
  isn't ruled here or measured.

## The principle behind R1, R3, R4 and R5

**An expression's type comes from the expression, not from where it lands.**
There are four exceptions, and each is a rule you can state in a line:

1. **Literals** have no fixed type until a slot gives them one: `5`, `1.5`,
   `null`, `[1, 2]`, and now `"..."`. A literal that doesn't fit is an error.
2. **A place passed to a `:&` parameter** is borrowed, as if written `@&x`.
3. **Pointer family, same pointee:** `@&T` to `@T`, `@T` or `@&T` to `*T`, and
   `*T` to `@T` or `@&T`. Same representation, nothing lost. `@a` of an array
   also fits `Span<T>`.
4. **Method receivers** auto-ref and auto-deref.

`*T` to `@T` stays free because references carry no non-null guarantee today
(`null` fits `@T`), so the conversion claims nothing new. 196 sites rely on it.

## Method and limits

Everything was measured at `cc4d6a8`, with ritz1 rebuilt from it.

- **Corpus:** a throwaway subclass of `TypeChecker` ran over all 1279 tracked
  `.ritz` files, logging each call argument, condition, `match`, binding,
  `return` and write with the checker's own types. Sites are deduplicated by
  file, line and column. Docs, `bootstrap_ritzlib`, `ritz1_old` and
  `projects/ritz/test` are excluded from the counts.
- **Reach:** 1099 of the 1279 files compiled through ritz0, 179 failed, and 1
  produced no result. 132 of the failures aren't docs or bootstrap copies: ritz 68, harland 50, lexis 24, prism 11, among others. A
  file that fails before the checker has no rows, **so every count here is a
  lower bound**, weakest for harland, lexis and prism. A later room should
  recount from `./rz build`.
- **Types the checker didn't know** are logged as `unknown`, not counted as
  mismatches.
- **Compilers:** 118 small programs, compiled and run on ritz0 and ritz1.
  ritz1_selfhosted wasn't run; the tickets require it.
- **Not read:** #1343 itself, which AGAST search wouldn't return. I read #1344,
  its child. So I can't say these rulings match its three recorded decisions.
  **`rz` should check that.** Nothing here touches ownership decision #1854.

## R1: indirection (#2227, #2249, #2325)

**Rule.** The table gives what each slot takes. "✓" compiles; "✗" is a located
error. `x` is a place of type `T`, `r` is `@T`, `m` is `@&T`, `p` is `*T`.

| Slot | `x` | `@x` | `@&x` | `r` | `m` | `p` |
|---|---|---|---|---|---|---|
| by-value `T` | ✓ | ✗ | ✗ | ✗ write `*r` | ✗ write `*m` | ✗ write `*p` |
| `name:& T` param | ✓ borrowed | see #2339 | ✓ | ✗ | ✓ | ✓ |
| `@T` | ✗ write `@x` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `@&T` | ✗ write `@&x` | see #2339 | ✓ | ✗ | ✓ | ✓ |
| `*T` | ✗ write `@x` | ✓ | ✓ | ✓ | ✓ | ✓ |

- **`name:& T` is an alias of the caller's place.** `c` has type `T` throughout
  the body, so it behaves as the `x` column. `@c` and `@&c` give the caller's
  address. This **changes** the rule merged in `dacbf7f`: `return c` from
  `-> @&C` and `let p: @&C = c` become type errors. Write `@&c`.
- **`@T` is read-only.** Writing through it is an error. `@x` of a `let` binding
  never reaches a mutable slot.
- **Moves.** By-value use of a move-only value through `@T`, `@&T`, `*T` or `:&`
  is "cannot move out of a reference": `*r`, `r.f`, a by-value `self` receiver.
  Raw pointers get no exception. Container code uses an explicit bitwise read:
  `ptr_read<T>`, or `mem_copy` until it exists. The check runs after
  monomorphisation.
- **#2325:** `h:& *U` follows the same rule. A place into `m:& *U` is legal;
  `@&h` has type `@&*U`, and a reference to another pointer type is refused.

**Why it fits.** Implicit deref is what caused the double drops: a bare `t` could
be a reference copy or a referent copy, and only the slot told you. With no
implicit deref, `eat(t)` from `t: @T` is a plain type error, the remaining cases
are written out, and the slot analysis #2231 thought it needed goes away. It
also removes `slot_tails` from both compilers, and with it most of #2309, plus
#2312, #2280, #2281 and #2310 part 2.

**DESIGN_DECISIONS §1.** The bare `:&` call keeps §1.2's `increment(n)`. §1.1's
"`x: T` is a const borrow" was already overtaken by #1854, where a by-value
parameter of a move-only type takes ownership, and §13.2 now states that. So
`read(data)` for a move-only `data` is written `read(@data)`. I treat that as
settled by Aaron's #1854 decision, not reversed here.

**`:= T`.** 16 tracked params use it (nexus 9, angelo 7). ritz1 doesn't parse it
and the spec doesn't list it. Not ruled here.

**Measured behaviour:**

| Shape | ritz0 | ritz1 |
|---|---|---|
| `bump(c)`, struct local into `:&` | 3 | clang error |
| `f(n)`, `f(c.x)`, `f(a[1])` into `n:& i32` | 3 | **SIGSEGV** |
| `f(1 + 2)` into `n:& i32` | refused | **SIGSEGV** |
| `let c`, then `bump(@c)` | **exit 1, a copy changed** | **exit 3, the `let` changed** |
| `val(@&c)` into by-value | runs, mutation lost | clang error |
| `p.x = 3` through `@C` | writes | writes |
| `eat(@r)`, `eat(*p)`, `eat(p.t)`, `var x = p.t`, one Drop value | 2 drops | 2 drops |
| `p.burn()`, by-value self on `@R` | 2 drops | 1 drop |
| `let p: @&C = @&c`, `return @&c`, `W { r: @&c }` | works | works |

**Cost:**

| Change | Sites | Where |
|---|---|---|
| `@x` into by-value (excluding `Span`) | 39 | lexis 30, tempest 8, ritz 1 |
| Reference or pointer, bare, into by-value | 3 | ritz examples and tests |
| Bare value into `@T` | 31 | 17 are `StrView`: make the param by-value |
| Bare value into `@&T` | 15 | `:&` pass-ons: spire 12, angelo 3 |
| Bare `StrView` into `*StrView` | 15 | ritz |
| `:&` assigned to a reference | 1 | tempest |
| Bare array into `Span` | 4 | |
| Writes through `@T` | 32 | ritz 15, ritzunit 14, tome 3 |
| `@x` of a `let` into a mutable slot | 1 | tome test |
| Move through a reference | 0 | generics not measured |

**#2227's 271 is mostly not this class.** `type_checker.py` reads `name:& T` as
by-value `T`, so `f(@x)` and `f(@&x)` into `:&` report `expected T, got @T`. 211
arguments have that shape. I didn't reconcile the two counts line by line. The
checker must learn `Borrow.MUTABLE` before #1823 recounts (#2336).

**Compilers.** ritz0: type errors in the checker path, delete the lending. ritz1:
located errors in place of the clang failures above, and fix the SIGSEGVs first.
#2335 is the highest priority here because those compile silently.

### For Aaron: #2339

1155 call arguments pass `@x` into a mutable slot: 995 into `@&T`, 160 into `:&`.
That's 566 production and 589 test, in 107 files, against 720 that write `@&x`.
Both compilers accept it and the callee mutates.

- **Option 1 (recommended):** `@x` is shared, and mutation needs `@&x` or a bare
  place into `:&`. It's what §3.2 and §13.5 already say, and a reader can see
  mutation at the call site. Each edit is one token at a position the checker
  already knows, so it's a tool run. New §13.5 conflicts it would expose aren't
  measured.
- **Option 2:** `@x` is plain address-of and takes its mutability from the slot.
  No migration, but `@&x` then adds nothing at a call site, and §3.2 has to
  change.

It's Aaron's because of the migration size and because it decides what `@` means.
The other R1 tickets are right under either answer.

## R2: lifetimes (#2249)

**Rule.** No lifetime annotations, as now. §13.5's "a borrow must not outlive its
owner" stays normative. "Escape analysis is not performed" goes, replaced by a
defined check for the definite case. A **local root** is a by-value local or
parameter, reached with no pointer or reference on the path. At `return` or a
tail, through `if` and `match` arms, it's an error to return:

- (a) `@x`, `@&x`, `@x.f` or `@x[i]` with `x` a local root, as `@T`, `@&T` or `*T`;
- (b) a local reference binding initialised from (a), over any number of hops;
- (c) a call returning `@U` or `@&U` that was given a reference to a local root
  with pointee `U`. This catches `return id(@&local)`. Raw `*U` returns are exempt.

Returning a `:&`, `@T` or `@&T` param stays legal: **that half of #2249 is
confirmed.** The caller's value must outlive the result. Nothing tracks a
reference stored in a field or global, or a raw pointer after a cast, and the
spec must say so: this isn't a soundness guarantee.

**Why it fits.** It matches "Rust's rules, minus the lifetimes" as far as a
function can see without annotations. (c) is type-directed because a rule over
all reference arguments would flag tome's `store_get(@key)` family.

**Measured.** `return @c`, `return @&c`, `-> *C` `return @c`, through
`let r = @c`, and `return @c` of a by-value param all compile and dangle on both.
`return id(@&c)` compiles on ritz0 and fails at clang on ritz1.

**Cost.** 857 fns return a reference or pointer: 838 `*T`, 11 `@T`, 8 `@&T`.
(a): 0 sites. (c): 0; the one candidate, `iris/lib/composite/layer.ritz:232`, is
rooted in a param. (b): **not measured**; 318 returns of a pointer-typed local
would need their initialisers followed. A hit is a real bug or a false positive
to look at.

**Compilers.** One pass after type checking: ritz0's move checker and ritz1's
`ownership.ritz`. ritz1's borrow tracking is thin (#2310 part 1).

## R3: string literals (#2226)

**Rule.** Option (a), widened. `"..."` is `StrView` by default and `*u8` in a
`*u8` slot, at every slot. Every string literal is stored NUL-terminated, and the
spec says so. A non-literal `StrView` never fits `*u8`, and `sv as *u8` goes:
write `.ptr` if you know it's terminated. `String` never fits `*u8`. A literal
that doesn't fit its type is an error, in an array element too.

**Why it fits.** It's exception 1 above. Migrating to `c"..."` would touch 248
production sites on `*u8` APIs that #1344 wants moved to `StrView`, and then
those sites would change again. Under this rule they stay as they are.

**Measured.** The literal works at an argument on both but fails at `let`,
`return` and a field on both. `take(sv)` compiles on both with no NUL promise.
`sv as *u8`: ritz0 yes, ritz1 clang error. `var a: [2]u8 = [1, 300]`: silently 44
on both. `let a: u8 = 300`: ritz0 refuses, ritz1 silently 44.

**Cost.** 609 literals need no edit. 1 site to fix:
`mausoleum/test/test_document.ritz:117`. `String` into `*u8`: 5, all ritz0 tests.
`sv as *u8`: 0. Non-literal array elements that narrow: not measured.

**Compilers.** Both gain literal typing at every slot. ritz0 drops the non-literal
`strview.ptr` extraction. ritz1 gains the fit check.

## R4: bool (#2228)

**Rule.** `if`, `while`, `assert`, and `and`, `or`, `not` take `bool`. Bitwise
operators take integers on both sides, so `bool & bool` is an error too. `==` and
`!=` can't compare `bool` with an integer. `bool` never converts implicitly.
`b as i32` stays; `x as bool` goes, write `x != 0`. Precedence doesn't change:
`x & 1 == 1` is a type error with a hint to parenthesise.

**Why more than the ticket's minimum.** Truthiness is an implicit conversion that
only 57 of 34,430 conditions use, none on a pointer, and it's silently wrong:

| Shape | ritz0 | ritz1 |
|---|---|---|
| `2 and 1` as a condition | false | true |
| `let b: bool = 2` | false | true |
| `256 as bool` | false | true |
| `if p` | clang error | compiles |

**Cost.** 136 checker errors in 39 files: 57 conditions (36 calls, 6 integer
literals), 8 bitwise, 23 compares in ritzlib tests, 39 bool-as-int. Plus 16
`and`/`or` on integers and 1 `x as bool`. Different from the ticket's 135 in
shape, because this counts with real types, not a regex.

**Compilers.** ritz0: turn the checks on. ritz1: its "accept when unsure" habit
(#1364) can't apply to conditions, so its inference needs to get there first.

## R5: arrays (#2303)

**Rule.** Option B, stricter: a non-literal `[N]T1` fits `[N]T2` only if the
element types are the same, so `[N]u32` into `[N]i32` is refused too. That
reverses #2287's relaxation. Literals still take the slot's element type.

**Why it fits.** It's a hidden O(N) loop that truncates, which §7.5 would reject
one element at a time.

**Cost.** 574 array flows, 0 non-literal between different element types. ritz0's
conversion fired 133 times, on shapes that match literals; the hook can't see the
expression, so that's read from the checker log. No sites to migrate.

**Compilers.** ritz0 refuses. ritz1 already does, but says "unlowerable": it needs
the located message.

## R6: match (#2245)

**Rule.** Every `match` must cover its scrutinee, as a statement or a value, or
it's an error naming what's missing. Covered means an unguarded `_` or binding;
every variant of an enum; `true` and `false`; or every member of a union. Integers
and strings need a catch-all. A guarded arm never counts.

**Why outright.** `DESIGN_DECISIONS.md` §9 already says so, marked "Finalized",
and the spec never picked it up. The gap is also wider than #2245 says:

| Shape, `f(5)` matches no arm | ritz0 | ritz1 |
|---|---|---|
| value `match` | 2, runs the last arm | 0 |
| enum missing a variant | 1 | 0 |
| arms that `return` | 2 | 0 |
| statement | nothing | nothing |

Requiring a catch-all only for divergence would leave the first two wrong.

**Cost.** 537 matches: 418 exhaustive enums, 19 generic enums, 85 catch-all, 14
`TypePattern` in one test file (not classified), and **2 to fix**:
`lexis/lib/dom/tag.ritz:555`, missing 9 `Tag` variants, and
`ritz0/test/test_diff_match_ctor_tail_phi.ritz:82`. Where the checker didn't know
the scrutinee's type I classified by pattern names, so an imported bare variant
could read as a catch-all.

**Compilers.** One shared check. ritz1 must also parse `true =>`. With #2237, the
`ret <T> 0` fallback can then become `unreachable`.

## R7: asm (#1825)

```
asm_stmt    := 'asm' IDENT asm_clauses? ':' NEWLINE INDENT asm_line+ DEDENT
asm_clauses := '(' asm_clause (',' asm_clause)* ')'
asm_clause  := ('in' | 'out' | 'inout') IDENT (':' REGISTER)?
             | 'clobber' REGISTER
```

```
fn inb(port: u16) -> u8
    var result: u8 = 0
    asm x86_64 (out result):
        movw {port}, %dx
        inb %dx, %al
        movb %al, {result}
    return result

fn write1(fd: i64, buf: *u8, n: i64) -> i64
    var ret: i64 = 1
    asm x86_64 (inout ret: rax, in fd: rdi, in buf: rsi, in n: rdx, clobber rcx, clobber r11):
        syscall
    return ret
```

- **Arch.** The name must match the target, or it's a compile error.
- **Lines** are raw text to the end of the line, not tokens. x86_64 is AT&T syntax.
  A line starting with `#` is a comment. `{{` is a literal brace, as in `print`.
- **Operands.** `{name}` is a local, parameter or global. No expressions. Integers
  and pointers only, and the Ritz type sets the register width.
- **Direction is declared, never inferred.** An operand is an input unless a
  clause says `out` (written) or `inout` (read and written). Those need a mutable
  place. ritz0's regexes over mnemonics go: they're not a rule anyone can state.
- **Registers.** `name: rax` pins one; otherwise any general register.
- **Clobbers.** Each general register named in the template is clobbered
  automatically. That's ritz0's existing behaviour, and it's textual and errs safe.
  `clobber` adds the implicit ones. Memory and flags are always clobbered, and a
  block is never removed or moved across a memory access.
- **`[[naked]]`** blocks take no clauses (§17.5).

**Cost.** 67 blocks in 20 files, all x86_64 AT&T. 11 lines rely on output sniffing
(harland 9, indium 2) and need `(out result)`. The rest are unchanged. Much of
harland passes a pointer and stores by hand to avoid outputs; that can be
simplified later. Direction declarations and pinned registers are what let
step 3 move ritz1's syscall shims into ritzlib.

**Compilers.** ritz0 needs the clauses and a raw-line parser. ritz1 has no `asm`
and implements this form directly (#1619). Blocked by #1455 and #1619 for
implementation only.

## R8: the standard (#1344, #1320)

**#1344: start after this merges and #2339 is answered.** The rulings are what it
would say about conversions, borrowing and `match`, so writing it first means
writing it twice. It doesn't need the implementation, though:

1. **Now:** the idiom questions and the `STYLE.md` consolidation, which don't wait
   for a compiler.
2. **As #2335–#2344 land:** each writes its rule into `LANGUAGE_SPEC.md` with
   compile-gated blocks, and that rule moves from ADVISORY to ENFORCED. The
   standard is done when they are. `no-compile` blocks shouldn't run ahead of them.

"Who frees what" also waits on #2159.

**#1320: not needed as written.** Rooms merge by fast-forward, so `pr.yml` doesn't
run, and #1838 proposes deleting it. The doc gate already runs before merge:
`run-gate.sh` runs `ci_local.py`, which runs the `bootstrap` job from `main.yml`,
which runs `make check-doc-examples`. Close it when #1838 lands. **The live gap is
#1319:** the gate compiles on ritz0 only, so a block ritz1 rejects still passes.
That should land before stage 2.

## Suggested order

1. **#2335:** ritz1 segfaults on legal code.
2. **#2344, #2342, #2341:** each ends a silent divergence, at low cost.
3. **#2336, then #2337, then #2340:** the indirection rule and what depends on it.
4. **#2338, #2343.** #2339 when Aaron answers.
