# Moved: Ritz Style Guide

The Ritz standard is now [`docs/STANDARD.md`](STANDARD.md) (AGAST #1344).

This file was the gated style guide from 2026-09-03 to 2026-11-18. Its
conventions (naming, layout, files, comments, tests) were reviewed into
`STANDARD.md` Part II, each with an ENFORCED, CHECKED or ADVISORY status. Its
ownership and error-handling advice was replaced by Part I, which answers the
questions it left open: `bool` against `i32`, `Result` against a sentinel,
`Option` against `null`, `Span`/references against a raw `*T`, methods
against free functions, who frees what, and what a library may abort on.

Several of its points are no longer true. It said `x: T` is always a borrow,
but a by-value parameter of a move-only type moves. It said `defer` was not
implemented. It told library code to return a sentinel. And it used `&&` in
the examples beneath its own rule for `and`.

This stub exists so that old links don't break silently. Update the link;
nothing more will be added here.
