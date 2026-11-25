# Standard-report module pins

One file per module (or tightly-coupled group), one pin per file.  Each file
pins the counts `tools/standard_report.py` produces for that module against
`docs/STANDARD.md`, so a new raw `*T` parameter (or free fn on a type's own
methods, ...) has to be converted or exempted with a reason deliberately
rather than landing quietly.

**Add a new module pin as its own new file.**  Do not append it to
`tools/test_standard_report.py` or to another module's file: the whole point
of this directory is that two independent cars can add two pins in the same
merge train and never touch the same lines (AGAST #4551).  Adding a file is
the conflict-free operation; appending to a shared file is what caused four
bounces on 2026-11-22.

`tools/test_standard_report.py` keeps only the report tool's own unit tests
(counting rules, exemption syntax, tree walk, CLI).

Run them with:

```bash
python -m pytest -q projects/ritz/tools/test_standard_pins/
```

or as part of `make -C projects/ritz tools-unit`.

The original module-group comment from `test_standard_report.py` (#1347):

> Converted module groups (#1347).  Each group that has been driven to zero is
> pinned here, so a new raw `*T` parameter has to be converted or exempted with
> a reason deliberately rather than landing quietly.  The whole tree is still
> being converted, so the pin is per module, not tree-wide.
>
> AGAST #4539: the remaining module groups (#1347 continuation).  Each
> parameter that is not a raw boundary takes a reference or a span; the rest
> are exempt against the C/allocator/sink ABI they exist to serve.

## C-shape ratchets (AGAST #4636)

`test_cshape_<module>.py` pin the C shapes `standard_report.py` counts for
goal 5 (`bool-return`, `status-return`, `out-param`, and since #4682
`raw-receiver`) as down-only ceilings
(`standard_report.ratchet_breaches`): a migration that lowers a count passes,
a new C-shaped fn fails.  `test_cshape_ritzlib.py` pins the whole tree, so a
module with no file of its own is covered too.  Lower a pin when you lower
its count.
`test_raw_receiver.py` pins `raw-receiver` per module (#4682: all zero).

The `--callers` ratchet (calls of exempt raw APIs from outside ritzlib, per
project) is `tools/test_standard_callers.py`: it names every package, and
`tools/ritz0_scope.py` reads this directory as a ritz0-step source.
