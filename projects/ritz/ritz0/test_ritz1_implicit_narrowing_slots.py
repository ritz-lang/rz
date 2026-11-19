#!/usr/bin/env python3
"""ritz1 rejects implicit narrowing at an assignment, a call argument and a
return exactly where ritz0 does (AGAST #4081, ritz1's half of #1444).

#1444 held `n = big()`, `take(big())` and `return big()` to LANGUAGE_SPEC §7.5's
let/var rule in ritz0; ritz1 (slot_narrowing.ritz) now does too. This feeds
ritz1 every case in ritz0's own tables (test_implicit_narrowing_slots.py, the
single source of truth for the rule) and requires ritz0's verdict. Taking the
tables from that file, rather than copying them, means a new route or
exemption there cannot silently skip ritz1.

The rows are ritz1 compiles only (~10 ms each). ritz0 already pins its own
verdict on every table row; only the extra rows below, which ritz0's tables
do not hold, also ask ritz0, so that ritz0 stays the oracle for them.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
from test_ritz1_for_iterable import SELFHOSTED_BIN

HERE = Path(__file__).resolve().parent
RITZ_ROOT = HERE.parent

_spec = importlib.util.spec_from_file_location(
    "_ritz0_narrowing_slots", HERE / "test_implicit_narrowing_slots.py")
SLOTS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SLOTS)

pytestmark = pytest.mark.integration


def _ritz1(bin_, work, body):
    src = work / "unit.ritz"
    src.write_text(SLOTS.PRELUDE + body)
    env = dict(os.environ, RITZ_PATH=str(RITZ_ROOT))
    return subprocess.run(
        [str(bin_), str(src), "-o", str(work / "unit.ll")],
        cwd=work, capture_output=True, text=True, env=env, timeout=300)


def _rejected(r):
    return r.returncode != 0 and "implicit narrowing:" in r.stderr


def _diagnostic_miss(r, work, line, col, slot):
    """ritz1 says `error:` after the position; the rest is ritz0's words."""
    want = (f"unit.ritz:{SLOTS.PRELUDE_LINES + line}:{col}: error: implicit "
            f"narrowing: {slot} but this value has type `i64`")
    if r.returncode == 0 or want not in r.stderr:
        return f"wanted {want!r}"
    if "as i32" not in r.stderr:
        return "no `as i32` hint"
    if (work / "unit.ll").exists():
        return "a rejected unit left a .ll behind"
    return None


# Routes ritz1 reaches by a way of its own, which ritz0's tables do not name:
# its parser spells a store through a pointer field, and `op=` on a field, as
# their own statements, and its Sema judges a tail value where the walk
# reaches it (a match arm's binding and an arm's `let` must be in scope).
_EXTRA_FN = "fn f(q: *P) -> i32\n    {}\n    0\n"
_OPT = ("fn ob() -> Option<{t}>\n    Some(5)\n\n"
        "fn f() -> i32\n    match ob()\n        Some(v) => v\n        None => 0\n")
_TAIL_LET = ("fn f(x: i32) -> i32\n    if x > 0\n        let w: {t} = {e}\n"
             "        w\n    else\n        0\n")
EXTRA_REJECTED = {
    "member_through_pointer":    _EXTRA_FN.format("q.x = big()"),
    "member_through_pointer_op": _EXTRA_FN.format("q.x += big()"),
    "local_field_op":            SLOTS._fn("var p = P { x: 0 }\np.x += big()"),
    "tail_match_binding":        _OPT.format(t="i64"),
    "tail_if_arm_let":           _TAIL_LET.format(t="i64", e="big()"),
    # An async fn's `return v` is lowered to `self.__result = v`, so both
    # compilers judge it on the assignment route at the declared type.
    "async_fn_narrow_result":    "async fn f() -> i32\n    return big()\n",
}
EXTRA_ACCEPTED = {
    "member_through_pointer_cast": _EXTRA_FN.format("q.x = big() as i32"),
    "tail_match_binding_fits":     _OPT.format(t="i32"),
    "tail_if_arm_let_fits":        _TAIL_LET.format(t="i32", e="x"),
    "narrow_shift_assign":         SLOTS._fn("var b: u8 = k\nb = b << 1", ret="u8",
                                             tail="b"),
    # ritz0 does not judge a call through a fn-pointer field, so ritz1 must
    # not either: a nameless callee is skipped.
    "fn_pointer_field_call":       ("struct H\n    cb: fn(i32) -> i32\n\n"
                                    "fn f(h: *H) -> i32\n    h.cb(big())\n"),
}


# ritz0's async rows (#4166) name the fn; ritz1 still names the lowered
# place it assigns. Same verdict and position, only the words differ.
# AGAST #4221 drops this table.
_RESULT_PLACE = "`self.__result` is `i32`"
RITZ1_WORDING = {
    "async_return": _RESULT_PLACE,
    "async_tail": _RESULT_PLACE,
    "async_return_after_await": _RESULT_PLACE,
}


# ritz1 still narrows silently into a struct literal field (#4157 is ritz0's
# half). AGAST #4218 drops this set.
RITZ1_PENDING = {
    "rejected[field_value_lit]", "rejected[field_in_place_lit]",
    "rejected[field_unsigned_slot]", "diagnostic[field_init]",
}


def _rows():
    """(id, body, check): check(r, work) is None or what went wrong."""
    def rejects(r, _work):
        return None if _rejected(r) else "accepted it; ritz0 rejects it"

    def accepts(r, _work):
        # The load-bearing controls: without them, rejecting everything passes.
        return None if r.returncode == 0 else "rejected it; ritz0 accepts it"

    def at(line, col, slot):
        return lambda r, work: _diagnostic_miss(r, work, line, col, slot)

    rows = [(f"rejected[{n}]", b, rejects) for n, b in sorted(SLOTS.REJECTED.items())]
    rows += [(f"accepted[{n}]", b, accepts) for n, b in sorted(SLOTS.ACCEPTED.items())]
    rows += [(f"diagnostic[{n}]", body, at(line, col, RITZ1_WORDING.get(n, slot)))
             for n, (body, line, col, slot) in sorted(SLOTS.DIAGNOSTICS.items())]
    rows += [(f"extra_rejected[{n}]", b, rejects) for n, b in sorted(EXTRA_REJECTED.items())]
    rows += [(f"extra_accepted[{n}]", b, accepts) for n, b in sorted(EXTRA_ACCEPTED.items())]
    return [row for row in rows if row[0] not in RITZ1_PENDING]


def _ritz0_disagrees(tmp_path):
    """ritz0's own tables pin its verdict; the extra rows are pinned here."""
    wrong = []
    for name, body in sorted(EXTRA_REJECTED.items()):
        if not _rejected(SLOTS._compile(tmp_path, body)):
            wrong.append(f"{name}: ritz0 accepted it")
    for name, body in sorted(EXTRA_ACCEPTED.items()):
        if SLOTS._compile(tmp_path, body).returncode != 0:
            wrong.append(f"{name}: ritz0 rejected it")
    return [f"ritz0 is the oracle, fix the case: {w}" for w in wrong]


def test_ritz1_gives_ritz0s_verdict_on_every_row(ritz1_bin, tmp_path):
    """One table test (TESTING.md, "What a ritz0 pytest case costs"): every
    row on ritz1 and ritz1_selfhosted, each compiled alone, and every
    failing row named with what it got."""
    fails = _ritz0_disagrees(tmp_path)
    for compiler, bin_ in (("ritz1", ritz1_bin), ("ritz1_selfhosted", SELFHOSTED_BIN)):
        for i, (rid, body, check) in enumerate(_rows()):
            work = tmp_path / f"{compiler}-{i}"
            work.mkdir()
            r = _ritz1(bin_, work, body)
            miss = check(r, work)
            if miss:
                fails.append(f"{compiler} {rid}: {miss}\n{body}\n{r.stderr[-800:]}")
    assert not fails, f"{len(fails)} row(s) differ from ritz0:\n\n" + "\n\n".join(fails[:20]) + (
        "" if len(fails) <= 20 else "\n...and " + ", ".join(f.split(":")[0] for f in fails[20:]))
