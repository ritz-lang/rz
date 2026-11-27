Review a Ritz diff against `projects/ritz/docs/REVIEW.md` ("Ritz, not C").

**Usage:** `/ritz-review [<git range or sha>]` (default: the working tree and
staged changes against `HEAD`; on a clean tree, `HEAD^..HEAD`)

Arguments: $ARGUMENTS

1. Read `projects/ritz/docs/REVIEW.md` in full, then `projects/ritz/docs/RITZ_NOT_C.md`.
   The rules they cite are in `projects/ritz/docs/STANDARD.md`; read a rule
   there when a finding turns on it.
2. Get the diff: `git diff <range>` for the range given, else `git diff HEAD`,
   else `git show HEAD`. Only added (`+`) lines in `.ritz` files are Part A
   findings; Part B covers the whole change, docs and pins included.
3. Count the `c"` literals the diff adds and removes in `.ritz` files:
   `git diff <range> -- '*.ritz' | grep -c '^+.*c"'` and the same with `^-`.
   For each added one, name the callee that needs the NUL. No callee that
   genuinely needs it (a syscall path or argv, an `extern fn`) is an A1 finding.
4. Walk Parts A and B item by item. For an item marked ENFORCED, still read the
   diff: a ratchet counts, it doesn't judge.
5. Report in REVIEW.md's "Output" form: one line per finding, the `c"` added /
   removed counts, then **ACCEPT** or **REJECT**. Change nothing during the
   review itself.
6. **The verdict is not the end of your turn.** If you ran this as a step of a
   task (a task room's ROOM.md step 2a), go straight on in the same turn: on
   REJECT, fix every blocking finding and run the review again; on ACCEPT,
   carry on with the task's next step (squash, smoke check, push, REAP). Four
   rooms stalled for 11-37 h on 2026-11-26/27 by stopping at this line.
