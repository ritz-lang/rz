# Moved: Ritz Style Guide

This document now lives at [`docs/STYLE.md`](docs/STYLE.md).

It was retired on 2026-09-12. Two style guides were in the tree claiming to be
canonical; `docs/STYLE.md` is the gated one — it is listed in `DOC_EXAMPLE_DOCS`
in the Makefile, so every fenced ```ritz block in it is compiled by
`tools/check_doc_examples.py` on each build. This one, last touched 2026-02-11,
was not, and only 3 of its 20 examples compiled.

On every point where the two disagreed, this document was the wrong one. It
taught `&mut Self` method receivers, said bare `"..."` was a heap-allocated
`String` (it is a `StrView`), listed `s"..."` as implemented (removed by AGAST
#98, and `make check-no-s-strings` fails the build if one reappears), claimed an
implicit `String` → `*u8` coercion, showed `println` with `{}` interpolation
(there is no `println`, and interpolation is a `print`-builtin-only facility),
showed brace blocks such as `if done { break }` in an indentation-only language,
and pointed at `examples/48_ritzfmt` for ritzfmt, which actually lives at
`examples/tier5_async/48_ritzfmt`.

Its only genuinely project-specific content — line length, blank lines and
section banners — is already covered by [`docs/STYLE.md` §2](docs/STYLE.md#2-formatting).

This stub exists only so that existing links do not break silently. Please update
your link; nothing further will be added here.
