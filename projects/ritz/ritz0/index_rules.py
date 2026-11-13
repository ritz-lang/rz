"""What indexing a struct may not do (LANGUAGE_SPEC §7.8, LARB ruling R15, AGAST #1635).

A struct opts into `[]` through three compiler-known traits. Each use of `m[k]`
needs one of them, and the error, located at the `[`, names the one missing and
what the type does implement. ritz1 prints the same words (struct_index.ritz),
and ritz0/test_struct_index.py holds all three compilers to them.
"""

# The compiler-known traits, in the order an error lists them.
TRAITS = ("Index", "IndexMut", "IndexSet")

# The types whose `[]` is built in (§7.8). None of them can implement a trait above.
BUILT_IN = ("Vec", "Span", "String")


def _listed(traits):
    """`Index`, `Index` and `IndexSet`, `Index`, `IndexMut` and `IndexSet`."""
    names = [f"`{t}`" for t in TRAITS if t in traits]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def needs_index(type_name):
    """A use of `m[k]` on a type that implements none of the traits; or a shared
    use (a read, `.f`, `@m[k]`) on one that doesn't implement `Index`."""
    return f"`{type_name}` can't be indexed: it doesn't implement `Index` (§7.8)"


def needs_writer(type_name, traits):
    """`m[k] = v` on a type that has neither `IndexSet` nor `IndexMut`."""
    return (f"`m[k] = v` needs `IndexSet` or `IndexMut`, and `{type_name}` "
            f"implements only {_listed(traits)}")


def needs_index_mut(use, type_name, traits):
    """A mutable use (`@&m[k]`, `m[k] op= x`, `m[k].f = x`) without `IndexMut`."""
    return f"`{use}` needs `IndexMut`, and `{type_name}` implements only {_listed(traits)}"


def builtin_impl(trait, type_name):
    """`impl Index for String`: the built-in types keep one meaning of `[]`."""
    return f"`{type_name}` is indexed by the language: it can't implement `{trait}` (§7.8)"


def message(traits, type_name, use):
    """The error for `use` on `type_name`, which implements `traits`, or None
    when the use is allowed. `use` is "read", "assign", or a mutable use's
    spelling (`@&m[k]`, `m[k] op= x`, `m[k].f = x`)."""
    if not traits:
        return needs_index(type_name)
    if use == "read":
        return None if "Index" in traits else needs_index(type_name)
    if use == "assign":
        if "IndexSet" in traits or "IndexMut" in traits:
            return None
        return needs_writer(type_name, traits)
    return None if "IndexMut" in traits else needs_index_mut(use, type_name, traits)
