# AGENTS.md

Guidance for coding agents in the `rz` monorepo, the Ritz language ecosystem.
The full agent prompt is [`AGENT.md`](AGENT.md); the compiler project's is
[`projects/ritz/CLAUDE.md`](projects/ritz/CLAUDE.md).

**Write Ritz, not C.** `c"strings"` are only for C interop, where the callee
can't take a length and needs NUL termination; null termination is unsafe and
heavily discouraged wherever a safer API exists. App code passes
`StrView`/`String`; if the only API for something takes NUL-terminated `*u8`,
the fix is a `StrView` API in ritzlib, not a `c""` at the call site.

Read before writing Ritz code, in this order:

1. [`projects/ritz/docs/RITZ_NOT_C.md`](projects/ritz/docs/RITZ_NOT_C.md): each
   C habit and its Ritz form, with a compiled example.
2. [`projects/ritz/docs/REVIEW.md`](projects/ritz/docs/REVIEW.md): what a review
   rejects. Run it on your own diff before you commit.
3. [`projects/ritz/docs/STANDARD.md`](projects/ritz/docs/STANDARD.md): the rules
   (S-* IDs) the other two cite.

[`projects/ritz/docs/LANGUAGE_SPEC.md`](projects/ritz/docs/LANGUAGE_SPEC.md) is
the language reference. Work is tracked in AGAST, not in `TODO.md` files.
