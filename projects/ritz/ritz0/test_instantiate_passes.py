"""
AGAST #3523: monomorphisation and the per-instance checks are ritz0.PASSES of
their own (_monomorph, _check_instances), not steps hidden inside
emitter_llvmlite.emit.  emit() takes the monomorphised module they leave.
The pass order itself is test_pass_structure's.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import instantiate  # noqa: E402
import monomorph  # noqa: E402
from emitter_llvmlite import EmitError, emit  # noqa: E402
from lexer import Lexer  # noqa: E402
from move_checker import MoveChecker  # noqa: E402
from parser import Parser  # noqa: E402

pytestmark = pytest.mark.unit

GENERIC = """\
fn ident<T>(x: T) -> T
    x

fn main() -> i32
    ident(0)
"""


def _parse(src: str):
    return Parser(Lexer(src, "t.ritz").tokenize()).parse_module()


def test_emit_refuses_an_unmonomorphised_module():
    with pytest.raises(ValueError, match="monomorphised"):
        emit(_parse(GENERIC), no_runtime=True)


def test_emit_neither_monomorphises_nor_checks_instances(monkeypatch):
    module = instantiate.prepare(_parse(GENERIC))

    def boom(*_args, **_kwargs):
        raise AssertionError("emit() ran a pass that isn't its own")

    monkeypatch.setattr(monomorph, 'monomorphize', boom)
    monkeypatch.setattr(instantiate, 'monomorphize', boom)
    monkeypatch.setattr(MoveChecker, 'check_instances', boom)
    ir = emit(module, no_runtime=True)
    assert 'define' in ir and 'ident' in ir


def test_monomorph_pass_drops_templates_and_notes_them():
    module = instantiate.monomorphize_module(_parse(GENERIC))
    assert not any(getattr(item, 'name', None) == 'ident' for item in module.items)
    assert module.generics.fn_names == frozenset({'ident'})


def test_monomorph_pass_drops_main_in_test_mode_only():
    def has_main(module):
        return any(getattr(item, 'name', None) == 'main' for item in module.items)
    assert has_main(instantiate.monomorphize_module(_parse(GENERIC)))
    assert not has_main(instantiate.monomorphize_module(_parse(GENERIC), test_mode=True))


def test_check_instances_reports_through_emit_error():
    with pytest.raises(EmitError, match="a\nb"):
        instantiate.raise_instance_errors(['a', 'b'])
    instantiate.raise_instance_errors([])


SLOT_ERROR = """\
fn want(p: @&i32) -> i32
    0

fn bad(p: @i32) -> i32
    want(p)
"""


def test_check_instances_judges_only_what_this_ll_defines():
    """An imported fn's body is its own module's to judge: the .ll for
    main.ritz only declares it (emitter_llvmlite.emits_definition)."""
    module = instantiate.monomorphize_module(_parse(SLOT_ERROR))
    [err] = instantiate.check_instances(module, source_file='/w/main.ritz')
    assert "doesn't fit an `@&T` slot" in str(err)
    for item in module.items:
        if item.name == 'bad':
            item.source_file = '/w/other.ritz'
    assert instantiate.check_instances(module, source_file='/w/main.ritz') == []
