# Moved: The Ritz Programming Language

This document now lives at [`docs/LANGUAGE_SPEC.md`](LANGUAGE_SPEC.md).

It was retired on 2026-09-12. It was never a tutorial companion to
`LANGUAGE_SPEC.md` — it was the *same document at an earlier point in history*,
pre-RERITZ, carrying no date stamp, so its staleness was invisible to a reader.
Only 34% of its fenced ```ritz examples compiled: it taught `&x` address-of,
`module::item` qualified access, `@test` attributes, `&T` / `&mut T` reference
types and `|x| x + 1` closures — all removed or never implemented — and claimed
string literals were `*u8` when bare `"..."` produces a `StrView`.

Its one current section, §8a Enums (struct-style variants), was ported into
[§10 of `LANGUAGE_SPEC.md`](LANGUAGE_SPEC.md#10-enums) before this stub replaced
it. Nothing else here was salvageable.

`LANGUAGE_SPEC.md` is listed in `DOC_EXAMPLE_DOCS` in the Makefile, so every
fenced ```ritz block in it is compiled by `tools/check_doc_examples.py` on each
build. This document was not, which is the whole reason the two diverged.

This stub exists only so that existing links do not break silently. Please update
your link; nothing further will be added here.
