"""What `.` sees through a struct (LANGUAGE_SPEC §7.7, LARB ruling R17, AGAST #3015).

A struct opts into `.` reaching through it with two compiler-known traits,
resolved statically like `Drop` and R15's `Index`:

    impl Deref for S        fn deref(self: @S) -> @T
    impl DerefMut for S     fn deref_mut(self: @&S) -> @&T

`s.f` is S's own field or method first; otherwise, when S implements `Deref`,
T's, through `deref(@s)` for a shared use and `deref_mut(@&s)` for a mutable
one. The errors, located at the field name, are worded here; ritz1 prints the
same words (deref_field.ritz), and ritz0/test_ritz1_box_field.py holds all three
compilers to them.
"""

TRAITS = ("Deref", "DerefMut")


def display(name, arity):
    """A monomorphised type name as the source spells it: `Wrap$H` is `Wrap<H>`,
    `Wrap$Wrap$H` is `Wrap<Wrap<H>>` and `Pair$i64$i32` is `Pair<i64, i32>`.
    `arity(head)` is how many type parameters the generic `head` declares (0
    for any other name). A nested argument may be mangled with `_` (`Wrap$Wrap_H`).
    A name the arities can't account for is left as is."""
    for sep in ("$_", "$"):
        shown = _display(name, arity, sep)
        if shown is not None:
            return shown
    return name


def _display(name, arity, seps):
    parts = [name]
    for sep in seps:
        parts = [q for part in parts for q in part.split(sep)]

    def take(i):
        head = parts[i]
        n = arity(head)
        if n == 0:
            return head, i + 1
        args = []
        i += 1
        for _ in range(n):
            if i >= len(parts):
                raise ValueError(name)
            arg, i = take(i)
            args.append(arg)
        return f"{head}<{', '.join(args)}>", i

    try:
        shown, used = take(0)
    except ValueError:
        return None
    return shown if used == len(parts) else None


# Each message takes types as the source spells them (`Box<H>`, see display).


def no_field(type_name, field, hint=None):
    """5(a): S has no `f` and doesn't implement `Deref`. `hint` is the spelling
    of the field reached through a `*T` field of S whose T has `f` (`w.ptr.k`)."""
    msg = f"`{type_name}` has no field `{field}`"
    if hint is not None:
        msg += f": it points at one: `{hint}`, or implement `Deref`"
    return msg


def neither_has(type_name, target_name, field):
    """5(b): S implements `Deref`, and neither S nor T has `f`."""
    return f"neither `{type_name}` nor `{target_name}` has a field `{field}`"


def needs_deref_mut(use, type_name):
    """5(c): a mutable use of `s.f` through a struct with only `Deref`. `use` is
    its spelling: `b.k = …`, `b.k op= …`, `@&b.k`, `b.k.m()`."""
    return f"`{use}` needs `DerefMut`, and `{type_name}` implements only `Deref`"


def deref_mut_alone(type_name):
    """Rule 1: `impl DerefMut for S` with no `impl Deref for S`."""
    return f"`{type_name}` implements `DerefMut` without `Deref`"


def targets_differ(type_name, deref_target, mut_target):
    """Rule 1: `deref_mut`'s T must be `deref`'s."""
    return (f"`DerefMut` for `{type_name}` reaches `{mut_target}`, "
            f"but its `Deref` reaches `{deref_target}`")


def impl_errors(items):
    """Rule 1's errors for a module's items: `(message, span)` for each
    `impl DerefMut for S` with no `impl Deref for S`, or whose `@&T` isn't
    the `@T` of S's `deref`. Located at the impl's trait name."""
    from metadata import type_to_string

    def target(block, method):
        for m in block.methods:
            if m.name == method and m.ret_type is not None and hasattr(m.ret_type, 'inner'):
                return type_to_string(m.ret_type.inner)
        return None

    def shown(block):
        return type_to_string(block.impl_type) if block.impl_type is not None else block.type_name

    derefs = {}
    for item in items:
        if getattr(item, 'trait_name', None) == "Deref" and hasattr(item, 'methods'):
            derefs[item.type_name] = item
    out = []
    for item in items:
        if getattr(item, 'trait_name', None) != "DerefMut" or not hasattr(item, 'methods'):
            continue
        where = getattr(item, 'trait_span', None) or item.span
        deref = derefs.get(item.type_name)
        if deref is None:
            out.append((deref_mut_alone(shown(item)), where))
            continue
        want, got = target(deref, "deref"), target(item, "deref_mut")
        if want is not None and got is not None and want != got:
            out.append((targets_differ(shown(item), want, got), where))
    return out
