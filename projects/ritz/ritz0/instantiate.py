"""
Monomorphisation and the checks that judge each generic instance: the two
ritz0.PASSES between the source-level checks and _emit (AGAST #3523, LARB
review/5 N2).  emitter_llvmlite.emit takes the module these leave.

    monomorphize_module   deref rules, monomorph.monomorphize, the test-mode
                          `main` drop; notes what the emitter's errors need
                          to know about the templates monomorph drops
    check_instances       the typing pass over what is emitted, so a generic
                          body is typed, and its slots judged, at each `T`;
                          then the move checker over each instance

`prepare` runs both, for an emit() caller other than compile_file (tests).
"""

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import ritz_ast as rast
import deref_rules
from emitter_llvmlite import EmitError, emits_definition
from monomorph import GenericInferError, monomorphize
from move_checker import MoveChecker
from typed import type_module


@dataclass(frozen=True)
class Generics:
    """The source's generic templates, by what an emit error needs of them.
    monomorph drops every template, so these are noted before it runs."""
    # Each generic fn's name: a call that names one without type args
    # deserves a better error than "Unknown function" (#1968).
    fn_names: FrozenSet[str]
    # Each generic struct's arity: an error spells `Wrap$H` as `Wrap<H>` (§7.7).
    arity: Dict[str, int]
    # Each generic impl's methods by the free name R10 would give them, which
    # they don't have (§5.4, LARB R37, AGAST #3372): `W_bump` -> its words.
    method_names: Dict[str, Tuple[str, str, list]]
    # Each generic struct and enum, by its variants (none for a struct):
    # `Slot.mk(5)` names one (AGAST #2185).
    types: Dict[str, FrozenSet[str]]


def _generics(module: rast.Module) -> Generics:
    items = module.items
    return Generics(
        fn_names=frozenset(item.name for item in items
                           if isinstance(item, rast.FnDef) and item.is_generic()),
        arity={item.name: len(item.type_params) for item in items
               if isinstance(item, rast.StructDef) and item.type_params},
        method_names={f"{item.type_name}_{m.name}": (m.name, item.type_name, item.type_params)
                      for item in items
                      if isinstance(item, rast.ImplBlock) and item.type_params
                      for m in item.methods},
        types={item.name: frozenset(v.name for v in getattr(item, 'variants', ()))
               for item in items
               if isinstance(item, (rast.StructDef, rast.EnumDef)) and item.type_params})


def monomorphize_module(module: rast.Module, test_mode: bool = False) -> rast.Module:
    """The monomorphised `module`, its templates' Generics as `.generics`.
    Raises EmitError for a source error found on the way."""
    generics = _generics(module)
    # §7.7 rule 1: a `DerefMut` needs a `Deref` reaching the same T.
    for message, where in deref_rules.impl_errors(module.items):
        raise EmitError(message, where)
    try:
        module = monomorphize(module)
    except GenericInferError as e:
        # `f(args)` whose args don't determine f's T (AGAST #1982).
        raise EmitError(str(e)) from None
    # Test mode (§17.1): the runner supplies `main`, so the file's own goes.
    if test_mode:
        module.items = [item for item in module.items
                        if not (isinstance(item, rast.FnDef) and item.name == 'main')]
    module.generics = generics
    return module


def check_instances(module: rast.Module, module_names: Optional[Set[str]] = None,
                    source_file: Optional[str] = None) -> List:
    """Type monomorphised `module` (setting `module.typed`, which the emitter
    reads) over the fns that `source_file`'s .ll defines, so a generic body
    is typed, and its slots judged, at each `T` it's instantiated with: a
    reference in a by-value slot or a value in a reference slot (§13.2,
    §13.4, AGAST #2336, #2337).  Then the move checker over each instance.
    Returns the errors, slot errors first."""
    def emits_body(item):
        return emits_definition(item, source_file)
    errors = list(type_module(module, module_names, emits_body).slot_errors)
    return errors + MoveChecker().check_instances(module)


def raise_instance_errors(errors: List) -> None:
    """check_instances' errors, as the one EmitError compile_file reports."""
    if errors:
        raise EmitError('\n'.join(str(e) for e in errors))


def prepare(module: rast.Module, test_mode: bool = False,
            module_names: Optional[Set[str]] = None,
            source_file: Optional[str] = None) -> rast.Module:
    """What ritz0.PASSES runs between the source checks and _emit, for an
    emit() caller that has only a parsed module: monomorphise, then check
    each instance.  Returns the module to hand emit()."""
    module = monomorphize_module(module, test_mode)
    raise_instance_errors(check_instances(module, module_names, source_file))
    return module
