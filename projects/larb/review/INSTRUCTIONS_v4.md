# LARB Code Review Instructions — v4 (design quality and structure)

**Introduced:** 2026-10-25 (AGAST #1800). Supersedes nothing: Phase 3
(`INSTRUCTIONS.md`, Feb 2026) remains the *syntax and idiom* checklist. v4 adds
*design quality and structure*, and changes how findings are produced: **measure
first, then read.** Output goes to `projects/larb/review/4/<area>.md`.

---

## 1. Measure (scripted, never by eye)

```bash
# Ritz sources
python3 projects/larb/tools/ritz-metrics/ritz_metrics.py <paths> --top 30 \
    --json /tmp/<area>.json > projects/larb/review/4/metrics-<area>.md
# Python sources (ritz0, build.py, tools)
python3 projects/larb/tools/ritz-metrics/ritz_metrics.py <paths> --lang py ...
```

`ritz-metrics` reports, ranked: function SLOC, cyclomatic complexity (1 +
`if/elif/while/for/=>/and/or/?`), max nesting depth, file sizes, duplicated
6-line windows (normalised: literals, numbers, whitespace), and string/C-idiom
smell counts. It reads files only; it never builds.

Thresholds that make a function a **finding by default** (justify any exception):

| Metric | Major | Critical |
|---|---|---|
| Function SLOC | > 150 | > 300 |
| Cyclomatic complexity | > 30 | > 80 |
| Nesting depth | ≥ 6 | ≥ 9 |
| File SLOC (hand-written) | > 1500 | > 3000 |
| Duplicate cluster | ≥ 3 copies of a 6-line window | ≥ 8 copies |

Also measure *liveness*: for each module, list its production importers
(`grep -rlE '^(from|import) <mod>\b'` excluding tests). A module with only test
importers is dead code with green tests, which is worse than dead code.

## 2. Read for design (the v4 checklist)

For every area, answer each heading with evidence or "none found".

1. **C in Ritz clothing** — `i32` flags where `bool` belongs; out-params where a
   struct/`Result` return belongs; `malloc(N) as *T` with magic sizes; global
   mutable arrays with `MAX_*` capacities; integer `kind` codes where an `enum`
   + `match` belongs.
2. **String handling** — `(*u8, len)` parameter pairs and struct field pairs
   (should be `StrView`); manual `strlen`/`memcpy`/byte-compare loops (ritzlib
   `str`/`strview` has these); `c"..."` where `"..."` (StrView) fits; fixed
   `[N]u8` buffers; ad-hoc number formatting.
3. **Function and file decomposition** — the §1 thresholds; for each giant
   function, name its natural split.
4. **Duplication** — within a module (copy-paste ladders) and across modules
   (the same helper written twice; two implementations of one subsystem).
5. **Layering and boundaries** — import graph, cycles, lower layers importing
   higher ones; phases fused (type inference inside emission, checks inside
   codegen); side-channel state (a field written by one function and read by
   another as an implicit return value).
6. **Policy vs mechanism** — decisions (what to do) entangled with machinery
   (how to do it): e.g. cache policy inside a compiler pass, CI policy inside a
   build script.
7. **Generated code** — is it regenerated and diffed in CI (`regen-check`)? Are
   hand edits possible? Does the generator emit avoidable boilerplate?
8. **Dead code, stale docs, leftovers** — `.orig`, `.old`, `_v2`, binaries in
   git, docs whose claims the code contradicts (verify every claim you cite).
9. **Tests that assert nothing about production** — tests importing a dead copy,
   skip-on-missing-artifact, duplicates of other gates.

## 3. Classify each finding

- **[cleanup]** — the language and ritzlib already provide the right tool; the
  code doesn't use it. Cite the spec/ritzlib location of the tool.
- **[language-gap]** — Ritz cannot express the clean version. Under the No
  Concessions doctrine (`projects/larb/AGENT.md`) this is a **language ticket**
  (spec + ritz0 + ritz1), not a cleanup ticket. State the missing feature
  precisely and show the code it would collapse.
- **[architecture]** — structure/phase/layering change spanning modules.
- **[generator]** — fix belongs in a code generator or its grammar, not its output.

## 4. Write it up

`projects/larb/review/4/<area>.md`:

```markdown
# LARB v4 Review: <area>
**Reviewed:** <date> · **Metrics:** metrics-<area>.md · **Status:** PASS | NEEDS WORK | CRITICAL

## Summary            (3-5 sentences, the shape of the problem)
## Findings           (ranked Critical → Major → Minor)
### F<n>. <title> [cleanup|language-gap|architecture|generator] — Critical
- Evidence: `file:line`, `file:line` (several sites; counts from the script)
- Impact: quantified (lines, call sites, bug classes it has caused — cite AGAST)
- Fix direction: concrete (the API / split / feature), and what it collapses
- Ticket: #NNNN (new or existing)
## Not findings       (things that look bad but are justified, with the reason)
```

## 5. Ticket

Search AGAST first; append evidence to an existing ticket instead of filing a
duplicate. One ticket per *group* of related findings, not per line. Every
ticket has: evidence with `file:line`, a fix direction, acceptance criteria
that can fail (a metric threshold, a red-then-green test, a grep that must come
back empty). Language gaps are filed as language tickets.
