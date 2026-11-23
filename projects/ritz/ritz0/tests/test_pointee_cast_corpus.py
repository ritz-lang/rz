"""LARB R1 corpus repair (AGAST #3608): no pointer changes pointee without `as`.

R1: only `@T`/`@&T`/`*T` of ONE pointee convert; a pointer to a different
pointee needs `as`.  ritz0's emitter used to accept these silently because
every pointer is an opaque `ptr`, so #2229's re-measure found 16 in the corpus:

- harland (15): `kfree(dev)` etc., a `*Struct` passed to `kfree(ptr: *u8)`.
  Each now says `kfree(dev as *u8)`.
- ritz1 (1): the grammar rule `struct_lit -> *StructLit` returned its
  `field_inits` (a `*FieldInit`).  The rule and its consumers
  (`ident_or_struct`, `struct_lit_expr`, `generic_struct_lit_arg`) now say
  `*FieldInit`, parser_gen.ritz is regenerated and `struct StructLit` is gone.

This pins each repaired file type-checking clean (the typing pass's errors), so
nothing regrows there.  One case per package, and each compile stops after
`_check_types` (no ownership pass, no emit), so a failure's stderr names the
file and line.
"""

import json
from pathlib import Path

import pytest

import ritz0
from import_resolver import DependencyMapping
from test_harland_kernel_features import harland_deps_args

ROOT = Path(__file__).resolve().parents[4]
HARLAND = ROOT / "projects/harland"
RITZ1 = ROOT / "projects/ritz/ritz1"

# (project root, source roots, target, files) per package.
GROUPS = {
    # ROOT/projects/ritz holds ritzlib (serial.ritz imports ritzlib.fmt.digits,
    # #1957): harland's build gets it from RITZ_PATH, which CI doesn't set
    # for pytest (AGAST #4150).
    "harland_kfree": (HARLAND, ["kernel/src", str(ROOT / "projects/ritz")],
                      "x86_64-none-elf", [
        "kernel/src/drivers/display/framebuffer.ritz",
        "kernel/src/drivers/virtio/blk.ritz",
        "kernel/src/drivers/virtio/common.ritz",
        "kernel/src/drivers/virtio/input.ritz",
        "kernel/src/mm/dma.ritz",
    ]),
    "ritz1_struct_lit": (RITZ1, ["src", ".."], "x86_64-unknown-linux-gnu", [
        "src/parser_gen.ritz",
    ]),
}


@pytest.mark.unit
@pytest.mark.parametrize("group", sorted(GROUPS))
def test_repaired_files_type_check_clean(group, tmp_path, capsys, monkeypatch):
    root, sources, target, files = GROUPS[group]
    passes = ritz0.PASSES
    # Through the typing pass, then its report (ritz0 runs that after _emit).
    monkeypatch.setattr(ritz0, "PASSES",
                        passes[:passes.index(ritz0._type) + 1] + (ritz0._check_types,))
    failed = []
    # harland's kernel imports its [dependencies] (goliath, cryptosec,
    # boot_abi: #1881, #4578), as `rz build harland` passes them.
    deps = None
    if root == HARLAND:
        deps = {name: DependencyMapping(name=name, path=Path(spec["path"]), sources=spec["sources"])
                for name, spec in json.loads(harland_deps_args()[1]).items()}
    for i, rel in enumerate(files):
        # A fresh output path each time: an up-to-date .ll skips every pass,
        # type checking included.
        ok = ritz0.compile_file(str(root / rel), str(tmp_path / f"{i}.ll"),
                                no_runtime=True, dependencies=deps,
                                source_roots=sources, project_root=str(root),
                                target=target)
        if not ok:
            failed.append(rel)
    err = capsys.readouterr().err
    assert failed == [], err
    assert "Type error" not in err, err
