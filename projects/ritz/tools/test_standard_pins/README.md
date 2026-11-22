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
