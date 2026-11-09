# LARB rulings: open language decisions, November 2026

Two batches: R1-R8 of 2026-11-06, then [R9-R13 of 2026-11-07](#second-batch-2026-11-07).

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
4. **Method receivers** auto-ref and auto-deref. R9 widens this one to field access
   and indexing: operators that see through a reference, not conversions.

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

# Second batch, 2026-11-07

Rulings on the groups `rz` sent on 2026-11-07, at `6e1d06e`, with `ritz1` and
`ritz1_selfhosted` rebuilt from it. #2387 merged while this was being written; its
`for` rows were re-run on ritz0 at `1fac612`. Each ruling is on its ticket. As before,
**none of this is in `LANGUAGE_SPEC.md`**: each implementation ticket writes its
own entry.

| # | Question | Ruling | Sites to migrate | Tickets |
|---|---|---|---|---|
| R9 | `*p`, and `[]` through a pointer (#2347, #2175, #2329, #2330, #2331) | `*p` is a place. `p[i]` means `(*p)[i]` when the pointee is indexable. Every binding has one address | 0 | #2175, #2329, #2330, #2331, #2440, #2441 |
| R10 | By-value `self` (#2393) | It's a by-value parameter, no exception | 1 (#2396) | #2393 |
| R11 | A `for` through a Vec element (#2425) | Option 1 now, then a narrow option 3 through §13.5. Option 2 is out | 0 | #2438, #2439 |
| R12 | Names (#2407, #2350, #2386) | A local can't take the name of a const, global or variant | 3 | #2407, #2386 |
| R13 | `match` arm order (#2349) | First match wins, and every arm must be reachable | 0 | #2349 |

## How the groups really split

- **Group A was two questions and a stranger.** #2347, #2175, #2329, #2330 and #2331
  are one: what `*`, `[]` and `.` mean through a pointer (R9). #2393 is a separate
  one about by-value parameters (R10). #2425 isn't about places: it's a reference
  outliving what it points at, so it's §13.5's (R11).
- **Group B is one rule.** #2407, #2350's question and #2386 all ask what a name
  means when a local and a module value share it (R12).
- **Group C is wider than #2349**, and R12 and R13 close one hazard from two sides:
  a misspelt const in a pattern is a binding, so it's a catch-all.

## Method and limits

- **Probes:** 147 small programs, compiled and run on ritz0, ritz1 and
  ritz1_selfhosted. Most carry an expected value worked out from the program, not
  from a compiler. Rows exploring an open question carry none.
- **Corpus:** a throwaway walk over ritz0's AST. Of 1283 tracked `.ritz` files, 1128
  are kept (docs, `archive`, `bootstrap_ritzlib`, `ritz1_old` and `projects/ritz/test`
  are out) and 1098 parse. **Every count is a lower bound.** A text scan of the 30
  that don't parse found only spire's `(*buf)[i]`.
- **It's syntactic, unlike batch one's checker log.** Types come from annotations, so
  `let p = @a` isn't followed. A method counts as mutating if any method of that name
  takes `@&`, `:&` or `*T`. Imports are resolved by path suffix, so a missed import
  could hide a global or variant clash. Consts are checked tree-wide, so that can't
  hide one.
- **Every zero was tested:** a control file with each shape fires each counter. That
  caught a wrong struct-field read. A separate count of 210 catch-alls after full
  coverage was also wrong: bare `None` read as a binding. Fixed, it's 84 catch-alls
  (#2344 found 85) and one candidate, which reading showed was false.
- **Not measured:** what copying `self` costs ritz1's speed; where a callee writes
  through a `*T` to a `let` (R9, the gate has to show it); `mk().mbump(2)`, below.

## R9: places (#2347, #2175, #2329, #2330, #2331)

**Rule.**

1. **`*p` is a place:** the pointee, not a copy. Only reading it by value copies, and
   for a move-only type that's "cannot move out of a reference" (R1). `(*p).m()`
   means `p.m()`. A by-value `self` method copies the pointee, as any by-value use does.
2. **`[]` sees through one level to anything indexable.** `p[i]` means `(*p)[i]` when
   `p` is a `*T`, `@T` or `@&T` and `T` is an array, Vec, Span or String. It's a
   place in every position: read, store, `+=`, `@`, `@&`, `.f`. Writes follow §3.2,
   so `@T` refuses them.
3. **A raw buffer stays one.** `*T` with `T` not indexable: `p[i]` is `*(p + i)`.
4. **A reference isn't a buffer.** `@T` or `@&T` with `T` not indexable is an error.
5. **One level.** `(*q)[1]` for `q: @*[3]i32`, `(*pp)[1]` for `pp: **[3]i32`.
6. **Stride `T`, everywhere.** `p[i] = <whole [N]T>` is a type error. `p[lo..hi]`
   stays refused, as on a plain array.
7. **Every binding has one address**, `let` included. `@x` is that address, every time.
   A write through a `*T` reaches a `let`: §3.2 and #2371 say that's unchecked.

**#2347's three questions.** (1) Legal, and `(*p)[i]` is too. 306a1d3's read path
stands. (2) No: the store refusal was an accident of ritz0's stride bug. (3) Stride `T`.

**Why it fits.** R1 is about slots: a type doesn't bend to where a value lands. `.`
and `[]` are operators reading their own operand, as receivers do, so they widen
exception 4 and add no conversion. `*p` is already a place everywhere except
receivers: 1780 parsed sites use `(*p).f`. The rule does give up one thing: `p[i]` isn't
`*(p + i)` for a pointer to an array, where `p + i` strides `[N]T` and walks rows.
`*[N]T` says "one array of N", not "a buffer of arrays", and nothing walks rows with
`p[i]`.

**Measured:**

| Shape | ritz0 | ritz1, selfhosted | Want |
|---|---|---|---|
| `p[1]`, `p: *[3]i32` | 20 | 20 | 20 |
| `@p[1]` | **0** | refused | 20 |
| `p[1] = 7` | refused | refused | 7 |
| `(*p)[1]`, also store and `@` | refused | refused | 20 |
| `p[1] = b`, a whole array | **SIGSEGV** | refused | type error |
| `p[1].y = 7` on `*[2]S` | refused | 7 | 7 |
| `let s: S = p[1]` | 4 | refused | 4 |
| `(*pp)[1]`, `pp: **[3]i32` | 20 | **0** | 20 |
| `q[1]`, `q: @*[3]i32` | **0** | **1, and 41** | error |
| `h.r[1]`, `h(@a)[1]` | 20 | **0** | 20 |
| `p[1]`, `p: *Vec<i32>` | clang error | **112, and 160** | 20 |
| `p[1] = 7`, `p: *Vec<i32>` | refused | **16, and 96** | 7 |
| `p[1] = 7`, `p: @&Vec<i32>` | refused | **20, store lost** | 7 |
| `p[1] = 7`, `p: @&i32` | writes past it | writes past it | error |
| `(*p).bump(2)`, want 42 | **40** | refused | 42 |
| `(*p).w = 7`, `@*p`, `*p = v` | right | right | |
| `let c`, two `@c` equal | **false** | true | true |
| `let c`, `f(@c)` writes through `*C` | **1, a copy** | 3 | 3 |
| `let c`, `c.w()`, `self: *C` | **1, a copy** | 3 | 3 |

Where two values are given, they're ritz1's and ritz1_selfhosted's. The two ritz1
builds disagreeing on one program is itself a sign of reading the wrong memory.

**Cost.** 0 to migrate: this legalises. 8 `*[N]T` params, 1 `@[N]T` param, 2 `*[N]T`
locals, no fields, globals or returns. 1 index through one (angelo
`simple_test.ritz:152`). 5 `(*buf)[i]`, all spire. 11 indexes through a reference to
a non-array, all `@Vec`, all legal. 0 `(*x).m()`. 1764 `@x` sites root at a `let`,
and rule 7 changes one only if a callee writes through it.

**Compilers.** ritz0: the store and address paths go to element stride, the field
refusals go, receivers stop copying, `@let` stops copying. ritz1: #2321's refusals
become lowerings, a `*p` receiver arm, `p + i` on `*[N]T`, and the silent rows go.

**Not ruled.** `mk().mbump(2)`, a mutating method on an rvalue, compiles on all three
and the write goes nowhere. It's the receiver twin of `f(1 + 2)` into `:&`. They agree,
and measuring it needs return types, because a chain through a reference is legal.

## R10: by-value `self` (#2393)

**Rule.** Bare `self` and `self: T` are a by-value parameter named `self`, with no
exception: the method's own storage, a copy or a move, and a local root under R2.
`self:& T` stays distinct. The rule is about what a program can see, so a compiler may
pass a pointer if the callee copies first.

**Why it fits.** §5.4 already says so, and #1854 settles what by-value means. An
exception would make `c.g()` and `C_g(c)` differ.

**Measured.** Worse than the ticket says: it's a silent wrong answer, not only a lifetime.

| Shape | ritz0 | ritz1, selfhosted |
|---|---|---|
| `self.x = 9`, then `c.x` | 1 | **9** |
| the same on a plain `s: C` param | 1 | 1 |
| `c.g(@&c)` writes `q.x`, reads `self.x` | 1 | **9** |
| `G.g()` writes `G.x`, reads `self.x` | 1 | **9** |
| `return @self` | dangles | refused, unlocated |

**Cost.** 452 methods with `self`: 168 by-value, 159 `:&`, 125 reference or pointer.
0 of the 168 write `self`. 4 take `@self...`, and only #2396 returns one. So 1 site.

**Compilers.** ritz0 gets the check. ritz1 splits bare `self` from `self:&` and copies.

## R11: a `for` through a Vec element (#2425, §13.5)

**Rule.**

- **Option 2 is out.** It contradicts Aaron's "evaluated once".
- **Option 1 ships** with #2387, and stays the limit for what nothing can see.
- **#2438:** §13.5's rule holds on all three compilers and covers every mutable
  borrow. While a binding holds an `@T` of a place, these are errors on the same root:
  `@&x`, `x` bare into `:&`, a `self: @&T` or `self:& T` method, and `x = v` or a write
  in its own storage. The loan lasts to the end of the block, as ritz0's does.
- **#2439:** a `for` whose iterable path crosses an index into anything but an array
  holds an `@` on the root for the loop, so `vs.push(h)` in the body is refused.
  `vs[0].a[2] = 50` stays legal and is seen, as Aaron's ruling requires.
- **`let p: *H = @vs[0]` stays unchecked**, by Aaron's #2371.

**Why it fits.** It's §13.5's own rule, reaching what it always said. It only refuses
programs that would read freed memory, so nothing about `for` changes. Like R2, it's
a check for the definite case: a push through another path isn't seen.

**Measured.** The ticket's "tracking that doesn't exist" is half right, and §13.5's
"The first rule is checked" is true of ritz0 only. The doc gate compiles on ritz0
alone (#1319), so its expect-error blocks pass anyway.

| Shape | ritz0 | ritz1, selfhosted |
|---|---|---|
| `let p = @n`, `bump(@&n)` | refused | **exit 2** |
| `let p = @n`, `bump(n)` into `:&` | refused | **exit 2** |
| `let p = @c`, `c.up()` | **exit 2** | **exit 2** |
| `let p = @n`, `n = 2` | **exit 2** | **exit 2** |
| `let p: @H = @vs[0]`, pushes | **exit 4, freed memory** | `@vs[0]` refused, unlocated |
| `for v in vs[0].a`, pushes, at `1fac612` | **5, freed memory** | not re-run |

**Cost.** 0 for both. 1062 `for` loops: 1024 ranges, 9 bare names, 29 `h.a` or `@h.a`,
none with an index on the path. 0 sites where a `let` holding `@place` meets a
mutating receiver or a write to that root.

**Compilers.** ritz0 adds receivers and `=`. ritz1 gets the check itself.

### R11a: overlapping places, not the same root (#2511, 2026-11-09)

R11's "on the same root" was loose wording. The rule compares **places**.

**Rule (text for §13.5).** A borrow is of a place: a root binding followed by field
(`.f`) and index (`[i]`) steps. Two places overlap when one path is a prefix of the
other. Field names must match exactly, and any two indexes count as equal. While a
binding holds an `@` of a place, or within the arguments of one call, these are errors
on any overlapping place: a mutable borrow (`@&p`, `p` passed bare to `:&`, a
`self: @&T` or `self:& T` method on `p`), or a write (`p = v`, or a write inside `p`).
Disjoint fields of one root don't conflict.

| Shape | Ruling |
|---|---|
| `let a = @c.x`, then `c.y = 2` | legal |
| `f(@&r.a, @&r.b)` | legal |
| `let a = @c.x`, then `c.x = 2` / `c = d` / `c.up()` | refused |
| `let a = @c.x`, then `c.x.k = 2` | refused (write inside the loaned place) |
| `let e = @a[1]`, then `a[2] = 5` | refused (indexes overlap) |
| `let e = @vs[0]`, then `vs.push(h)` | refused |
| `f(@&r.a, @&r.a.b)` | refused |

**Why.** §13.5 says the rules are Rust's, and a field is separate storage. R9 already
made `x.f` and `x[i]` places. Comparing indexes would need values, so any two indexes
overlap. As before, this is a check for the definite case: the path is syntactic, and
an alias through another binding isn't seen. The loan still lasts to the end of the
block.

**Cost.** (A) costs 2 sites and (B) 3, not the 0 and 3 #2511 gave. angelo's
`GlyphCache.get` and `SubpixelGlyphCache.get` write `self.entries[i].access_count`
while `entry = @self.entries[i]` is live, and the loan is a prefix of that write. They
need the rewrite either way: drop `entry` and compare `self.entries[i].key.hash()`, as
`contains` already does. The overlapping-place rule makes tempest `tab_renderer.ritz:275` legal.

**Compilers.** ritz0, ritz1 and ritz1_selfhosted record a place path on each loan and
test for overlap. The error names both places, not just the root.

## R12: names (#2407, #2350, #2386)

**Rule.** A local binding can't take the name of a module-level value that a bare read
would reach: a `const`, a global `var` or an enum variant, declared there or imported.
It's a located error at the binding, for `let`, `var`, parameters, `for` variables,
match bindings and payload bindings. A local named like a **fn** is legal and wins;
calling a local that isn't a fn value is a located error.

**The questions it answers.**

- `Some(K)` and `Some(R)` stay refused. A payload doesn't simply shadow, because
  nothing does.
- A float const on an integer payload stays refused, and §8.2's "integer const" goes.
  String and array consts, which bind today, are refused too. The const's type stops
  mattering, so `name_tests_payload` loses its name branch to the binder check.
- `Some(Red)` on `Option<i32>` binds today and is refused.
- A top-level `F =>` naming a non-integer const: ritz0 says non-exhaustive, ritz1
  binds it. Now the same error. `K =>` on an integer const still compares.
- The binder check runs ahead of coverage, so the first error agrees. Agreement is
  required on the first error only.

**Why it fits.** Aaron's #2395 forbids reuse so the scope question never arises. Here
that also gives a pattern name one reading: if locals could shadow consts, `K =>`
would change meaning with the scope. Fns differ because a call says what it wants.

**§10.2 changes.** "A local or parameter named like a variant shadows it" came from a
crash fix (#2038, #1600), not a decision I can find. **`rz` should check.** If Aaron
decided it, variants drop out, and `Some(R)` needs its own refusal.

**The price.** A new `pub const` can break a local downstream. Today the same change
silently alters that local's value.

**Measured.** All three compilers agree on each row unless shown.

| Shape | Result |
|---|---|
| `let K`, `var K`, param `K`, read `K` | 7: the const wins |
| `for K in 2..3`, read `K` | 8: reads 7 |
| `import ritzlib.sys`, `let SYS_READ = 3` | 0: an imported const wins |
| `let G`, param `G` over a global | 3: the local wins |
| `for v in g`, local over a global | ritz0 3, ritz1 30 |
| `let Red` over a variant | 3: the local wins |
| `let k = 3`, `k()` with `fn k` | ritz0 7, ritz1 **SIGSEGV** |
| `let k: fn() -> i32 = a`, `k()` | 5, stays legal |

**Cost.** 3 renames, all `broadcast_mac` in harland (`net/arp.ritz:179`,
`net/dhcp.ritz:122`, `:221`). 56,822 binders: 0 reuse any const name anywhere in the
tree, 0 a variant in scope, 3 a global. 77 reuse a fn name, which stays legal. 0 call a
local that isn't a fn value.

**Compilers.** One check where names are bound, on all three.

### For Aaron: the rest of #2395

His ruling covers a nested `let` or `var` (5 sites). He asked for the rest to be
reported, not decided. Measured, all running on all three today: same-block rebinding
7, plus 2 of `let _`; a `for` variable over an outer local 2; a `let` over a param 0;
a payload over an outer local 0.

**Recommendation:** extend it to all of these, with `_` exempt, so a name means one thing
per fn. It costs 9 renames. A `for` variable reusing a local raises the scope question
just as a nested `let` does. It's his, because he set that ruling's limits.

## R13: `match` arm order (#2349)

**Rule.** Arms are tried top to bottom and the first match wins, and every arm must be
reachable. An unreachable arm is a located error at that arm, naming what covers it.
An arm is unreachable after an unguarded catch-all; after the same literal or const
value; after the same variant, whatever its binding; or once arms already cover the
scrutinee under R6, so a `_` after every variant is an error. A guarded arm covers
nothing.

**Why it fits.** R6 says no value can miss every arm; this says no arm can miss every
value. It also catches a real mistake: `KX => 1 / KK => 2`, where `KX` is a typo,
takes the first arm silently today, and becomes an error at `KK`.

**Measured.** Wider than the ticket:

| Shape | ritz0 | ritz1, selfhosted |
|---|---|---|
| `_ => 1 / 5 => 2`, also statements | **2** | 1 |
| `x => 1 / 5 => 2` | **2** | 1 |
| enum `_ => 1 / B => 2` | **2** | 1 |
| `Option`, `_ => 1 / Some(v) => v` | **2** | 1 |
| `5 / 5`, `K / 5`, `B / B`, `Some / Some`, `true / true` | clang error, unlocated | first arm |
| `_ / _`, full enum or bool then `_` | 1 | 1 |

**Cost.** 0. 551 matches: 0 arms after a catch-all, 0 duplicates, 84 ending in a
catch-all, 0 of those after full coverage. Consts were compared by name, not value.

**Compilers.** One check beside coverage, on all three. Lowering doesn't change, so
#2419 isn't touched.

## Suggested order

1. **#2440, then #2393:** silent wrong answers on ritz1 that write memory or reach the
   caller, in shapes real code could write.
2. **#2349, #2407 (with #2386):** end silent divergences, at 0 and 3 sites.
3. **#2330, #2331, #2329, #2175:** one room could take them, as they share one table.
4. **#2441,** whose cost only the gate can show.
5. **#2438, then #2439.**
