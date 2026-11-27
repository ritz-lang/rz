# AGENTS.md

Guidance for coding agents in the `rz` monorepo, the Ritz language ecosystem.
`CLAUDE.md` at the repo root is a symlink to this file. The compiler
project's own agent doc is [`projects/ritz/CLAUDE.md`](projects/ritz/CLAUDE.md).

## Write idiomatic Ritz, not C in Ritz clothing

**No Concessions:** never make concessions for the language — we are MAKING
the language. If Ritz can't express something cleanly, fix Ritz; don't work
around it. If a feature is missing, implement it in `projects/ritz/ritzlib`
with tests, submit the change, and only then use it. "It compiles" is not
"idiomatic" — C-with-Ritz-syntax (raw pointers, out-params, status codes,
`c""` strings) is a bug, not a style choice.

## Read before writing Ritz code, in this order

1. [`projects/ritz/docs/LANGUAGE_SPEC.md`](projects/ritz/docs/LANGUAGE_SPEC.md):
   the language itself. Read this before writing any Ritz, not last.
2. [`projects/ritz/docs/RITZ_NOT_C.md`](projects/ritz/docs/RITZ_NOT_C.md): each
   C habit and its Ritz form, with a compiled example.
3. [`projects/ritz/docs/REVIEW.md`](projects/ritz/docs/REVIEW.md): what a review
   rejects. Run `/ritz-review` on your own diff before you commit — its
   verdict is a step, not the end of your turn: fix what it finds and keep
   going.
4. [`projects/ritz/docs/STANDARD.md`](projects/ritz/docs/STANDARD.md): the rules
   (S-* IDs) the other two cite.

## The concrete rules

- **Text:** `StrView`/`String`, never `*u8` + length. `c"strings"` are only
  for C interop, where the callee can't take a length and needs NUL
  termination (a syscall path/argv, an `extern fn`). If the only API for
  something takes NUL-terminated `*u8`, the fix is a `StrView` API in
  ritzlib, not a `c""` at the call site (STANDARD.md S-TEXT-1).
- **Fallibility:** `Option<T>`/`Result<T, E>`, never `i32` status codes or
  out-pointers (STANDARD.md S-PTR-1).
- **Ownership:** borrow (`x: T`), mutable borrow (`x:& T`), or move (`x:= T`)
  — not raw pointers for anything but FFI.

## Doctrines

- **Ghost Doctrine:** warnings are the ghosts of future production outages.
  Fix anomalies when discovered, not later; a compiler warning is a bug.
  Track every known failure in AGAST — a `known-failures/<agast>.toml` entry
  must cite the AGAST task (validated by `projects/ritz/tools/known_failures.py`).
- **TDD:** write a failing test first, implement to pass it, refactor with
  confidence, all tests green before committing.
- **Main is always green**, CI enforced. Branches are short-lived; squash on
  merge. Commit format: `<scope>: 🤖 <description>`, cross-project as
  `ritzlib,squeeze,valet: 🤖 <description>`.

## Monorepo structure

`./rz list` is the authoritative project list. Each project keeps library
code in `lib/` and binary entry points in `src/`; `ritz.toml` declares
`[[bin]]`/`[[lib]]` targets. Using `./rz`, you do not need to set
`RITZ_PATH` — the workspace CLI sets it. Module resolution lets any project
import from any other:

```ritz
import ritzlib.sys           # From projects/ritz/ritzlib/
import lib.gzip              # From projects/squeeze/lib/
```

`projects/ritz/` is the compiler (ritz0 bootstrap, ritz1 self-hosted,
ritzlib); other projects (ritzunit, squeeze, cryptosec, valet, zeus,
mausoleum, tome, spire, harland, ...) are built on it. `projects/larb/`
holds ecosystem standards and design docs, not buildable code.

## Testing and validation

```bash
./rz test <project>          # tests pass, from the workspace root
```

**Do not use `make -C projects/<project> test`** outside `projects/ritz`: in
most project directories `make` matches the `test/` directory as an
already-up-to-date target and exits 0 having run nothing. See
[`projects/ritz/CLAUDE.md`](projects/ritz/CLAUDE.md) for the compiler's own
gates (`make ci-local`, `make matrix-full`, `make valgrind`).

## Tracking

Work is tracked in AGAST, not in `TODO.md`/`DONE.md` files. Do not recreate
them.
