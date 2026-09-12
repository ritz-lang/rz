# Moved: Ritz Grammar Specification

The language reference now lives at
[`projects/ritz/docs/LANGUAGE_SPEC.md`](../../ritz/docs/LANGUAGE_SPEC.md); see
[§20 Appendix A](../../ritz/docs/LANGUAGE_SPEC.md#a-grammar-simplified) for the
grammar sketch.

The machine-readable ground truth is `projects/ritz/grammars/ritz1.grammar`, the
file the self-hosted parser is actually generated from. Prefer it to any prose
EBNF, including the 878 lines that used to be here.

This document was retired on 2026-09-12. AGAST #1311 stubbed four sibling docs in
this directory on 2026-09-03 and missed this one. It opened by calling itself "the
authoritative reference for parser implementers" — a third document in the tree
claiming authority over the language — while its productions still admitted `&x`
address-of, the `::` path separator and `s"..."` string literals, none of which
the compiler accepts. Hand-maintained EBNF that no generator reads and no build
checks will diverge from the parser; this one did.

This stub exists only so that existing links do not break silently. Please update
your link; nothing further will be added here.
