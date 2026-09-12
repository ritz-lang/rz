# Moved: Ritz Language Quick Reference

The language reference now lives at
[`projects/ritz/docs/LANGUAGE_SPEC.md`](../../ritz/docs/LANGUAGE_SPEC.md).

This document was retired on 2026-09-12. AGAST #1311 stubbed four sibling docs in
this directory on 2026-09-03 and missed this one, which then kept its February
2026 contents: `&x` address-of (7 times), `&T` / `&mut T` reference types (7),
`@test` attributes (2) and `::` qualified access (2) — all removed from the
language — plus `String` / `Span<u8>` descriptions of what bare `"..."` produces
(it is a `StrView`). It also pointed readers at
`projects/larb/docs/LANGUAGE_SPEC.md`, which has itself been a stub since
2026-09-03, so the one link out of here led nowhere.

It described itself as "minimal context for AI agents", which made it the most
harmful stale document in the tree: its whole purpose was to be read instead of
the specification, by readers with no independent way to notice it was wrong.

`projects/ritz/docs/LANGUAGE_SPEC.md` is listed in `DOC_EXAMPLE_DOCS` in
`projects/ritz/Makefile`, so every fenced ```ritz block in it is compiled by
`projects/ritz/tools/check_doc_examples.py` on each build. A stale example there
is a red build rather than a misled agent.

This stub exists only so that existing links do not break silently. Please update
your link; nothing further will be added here.
