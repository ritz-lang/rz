# Archive — historical documents, NOT authoritative

Nothing in this directory describes the project as it is now. These are
point-in-time records: session logs, superseded status reports, completed
work-tracking files, code reviews of source trees that no longer exist, and an
entire earlier compiler (`ritz1_old/`).

They are kept because they explain *how* decisions were reached. They are not
kept as a description of the present.

**Do not use a file in here to answer a question about current state.** For that:

- **What is being worked on, and why** → AGAST, the task tracker.
- **Does the compiler work** → `make -C projects/ritz ci-local`.
- **What the language is** → `projects/ritz/docs/LANGUAGE_SPEC.md`.
- **The plan** → `projects/ritz/docs/ROADMAP.md`.

## Reading these safely

Three traps, all of which have cost real time:

1. **Dates written in these files are unreliable.** Many carry a year that is
   simply wrong — documents about work done in late 2025 are stamped 2024, and one
   is stamped `2024-01-XX` with the placeholder never filled in. The monorepo's
   first commit is 2026-02-15, and everything here predates or accompanies the
   consolidation. Trust `git log`, not a hand-typed date.

2. **Several of these files describe removed syntax as current.** Address-of was
   `&x` and is now `@x`; `module::item` qualified access, `&T`/`&mut T` reference
   types, `@test` attributes and `s"..."` literals were all removed. At least one
   archived progress log records changing the grammar *from* `@` *to* `&` as a
   fix — the language went the other way, and following that file would re-break
   it. The authoritative syntax is whatever `LANGUAGE_SPEC.md` says and what
   `ritz0` accepts.

3. **Filenames repeat.** Some names appear both here and, historically, in a live
   directory, with different contents. Files moved in later carry a scope suffix
   (`-docs`, `-ritz1`, `-ritz-root`) for exactly that reason. If two files look
   like the same document, they are probably two different documents.

## Why these were moved here

They used to sit beside the live documentation — at one point twenty-one
point-in-time snapshots shared a directory with `README.md` and `CLAUDE.md`, with
nothing to indicate which, if any, was current. Quarantining by directory is
cheaper than annotating each file, and it means a reader has to opt in to reading
history.

Work tracking that used to live in per-project `TODO.md` / `DONE.md` files was
deleted rather than archived: it is superseded by AGAST, and git retains it. A few
such files already in this directory when that happened were left alone.
