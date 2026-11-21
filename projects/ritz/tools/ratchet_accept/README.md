# Ratchet acceptances — one file per AGAST ticket (AGAST #4447)

`tools/ritz1_ratchet.py` holds ritz1's M1.3 metrics to a one-way budget. A room
that deliberately accepts a raised metric runs:

```bash
python3 tools/ritz1_ratchet.py --update
```

and commits `<ticket>.json` here instead of rewriting
`tools/ritz1_metrics_baseline.json`. The shared baseline is the *base* and a
room leaves it untouched, so two rooms that both accept a cost — even on the
same metric — add different files and cherry-pick into a train in either order
with **neither rebasing**. Before #4447 every such room rewrote the whole
measurement blob and the second one conflicted.

The file name is the AGAST ticket (`--ticket`, or the room's `ADELE_ROOM`);
outside a room a content hash is used. A fix deletes its own file, the same
rule as `known-failures/<ticket>.toml` (AGAST #3963).

## Format: deltas, not absolutes

Each file records only the metrics the tree raises above its allowance, as
**non-negative deltas**:

```json
{
 "ticket": "4447",
 "scalars": {"cstr_literal": 18},
 "long_fns": {"emitter_stmt::emit_assign": 7},
 "large_files": {"ast_helpers": 24},
 "cycle_module_names": ["new_module"]
}
```

The allowance is `baseline + d1 + d2 + ...`. Deltas are additive because a
merge train gates the superposition of two rooms' feature costs; an absolute
value would under-budget the second room (`max(v1, v2)`), and the train would
fail even though neither room regressed on its own base.

The budget is monotonic: improvements pass (`improvements need no record`) but
are not written back, so tightening it is a deliberate edit. An in-flight room
still running the old tool rewrites the baseline blob instead; that format is
still read as the base, so the transition is tolerant.
