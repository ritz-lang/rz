"""Where each generic instance was instantiated, for the notes an error
inside one carries (AGAST #4844).

An error found while checking an instance (a generic fn, or a method of a
generic impl, at concrete type args) points at a line inside the generic:
`ritzlib/gvec.ritz:235:16`.  Nothing there says which call in the user's code
made that instance.  monomorph records, per instance, the expression that
first named it and the body it sits in (`InstanceSite`); `add_notes` appends
one line per instantiation step to such an error, innermost first, down to
the first frame in a non-generic body:

    .../ritzlib/gvec.ritz:235:16: cannot move out of a reference
    .../main.ritz:11:16: note: `Vec<T>.get` instantiated here (and 1 more)

An instance named from several places reports the first, plus "and N more".
ritz1's twin is diag.ritz's diag_inst_notes, which prints the same lines.
"""

from dataclasses import dataclass

import ritz_ast as rast
from tokens import Span

NOTE = "note"


@dataclass(eq=False)
class InstanceSite:
    """The first expression that named an instance, and the body it sits in."""

    span: Span | None
    # The fn whose body holds `span`: a plain fn, or another instance, whose
    # own `instance_site` continues the chain.
    requester: rast.FnDef | None
    # Other places that name the same instance.
    more: int = 0
    # The instance as written: `cell_get<T>`, `Vec<T>.get`.  Set when the
    # instance is made (monomorph names it from its template and args).
    name: str = ""

    def again(self, span: Span | None, requester: rast.FnDef | None) -> None:
        """Another expression names the same instance."""
        if span != self.span or requester is not self.requester:
            self.more += 1

    def made(self, name: str) -> "InstanceSite":
        """This site as instance `name`'s own: a copy, since a site an
        unknown receiver wants is shared by every instance it reaches."""
        return InstanceSite(self.span, self.requester, self.more, name)

    def __deepcopy__(self, memo) -> "InstanceSite":
        # The move checker checks a deep copy of each instance; the chain is
        # the original's and must not drag its requesters' bodies along.
        return self


def notes(fn: rast.FnDef | None) -> list[str]:
    """One `<file>:<line>:<col>: note: ...` line per instantiation step from
    `fn` out, innermost first; none for a fn that is no instance."""
    lines: list[str] = []
    seen = set()
    while fn is not None and id(fn) not in seen:
        seen.add(id(fn))
        site = getattr(fn, "instance_site", None)
        if site is None or site.span is None:
            break
        where = f"{site.span.file}:{site.span.line}:{site.span.column}"
        tail = f" (and {site.more} more)" if site.more else ""
        lines.append(f"{where}: {NOTE}: `{site.name}` instantiated here{tail}")
        fn = site.requester
    return lines


def add_notes(error: Exception, fn: rast.FnDef | None) -> Exception:
    """`error`, its message followed by `fn`'s instantiation notes.  An
    error that has them already is left alone (one raised in a callee
    instance and seen again by its caller keeps the innermost chain)."""
    if getattr(error, "instance_notes", None) is not None:
        return error
    lines = notes(fn)
    error.instance_notes = lines
    if lines and error.args:
        error.args = ("\n".join([str(error.args[0])] + lines),) + error.args[1:]
    return error
