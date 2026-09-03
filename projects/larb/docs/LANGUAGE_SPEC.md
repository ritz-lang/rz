# Moved: Ritz Language Specification

This document now lives at [`projects/ritz/docs/LANGUAGE_SPEC.md`](../../ritz/docs/LANGUAGE_SPEC.md).

It was moved there on 2026-09-03 (AGAST #1311). It had sat in `projects/larb/docs/`
since February 2026, describing pre-RERITZ syntax that the compiler rejects outright —
and it sat there precisely *because* it was in `projects/larb`: every in-tree migration
wave swept `projects/ritz` and stopped at the project boundary. The specification now
lives next to the compiler that defines it, and every fenced ```ritz example in it is
compiled by `projects/ritz/tools/check_doc_examples.py` on each build. A stale example
is now a red build rather than a reader's afternoon.

This stub exists only so that existing links do not break silently. Please update
your link; nothing further will be added here.
