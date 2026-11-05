"""
Tests for the Move and Borrow Checker

Phase 9: Ownership & Borrowing
"""

import pytest
from parser import parse
from move_checker import MoveChecker, OwnershipError


def drop_impl(ty: str) -> str:
    """`impl Drop for ty`: Drop is what makes a type move-only (LANGUAGE_SPEC
    §13.1, AGAST #2157); a struct without one copies."""
    return f"""
trait Drop
    fn drop(self: @&Self)

impl Drop for {ty}
    fn drop(self: @&{ty})
        pass
"""


def check(source: str) -> list:
    """Parse and run move checker, return errors."""
    module = parse(source)
    checker = MoveChecker()
    return checker.check(module)


class TestMoveChecker:
    """Test move checking."""

    def test_simple_use(self):
        """Basic variable use should be fine."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    return x
""")
        assert len(errors) == 0

    def test_copy_type_no_move(self):
        """Copy types (primitives) don't move."""
        errors = check("""
fn takes_i32(x: i32) -> i32
    return x

fn main() -> i32
    var x: i32 = 42
    takes_i32(x)
    return x
""")
        # i32 is Copy, so x can still be used after passing to function
        assert len(errors) == 0

    def test_use_after_move_struct(self):
        """Using a struct after move should error."""
        errors = check("""
struct Point
    x: i32
    y: i32

fn takes_point(p: Point) -> i32
    return p.x

fn main() -> i32
    var p: Point = Point { x: 1, y: 2 }
    takes_point(p)
    return p.x
""" + drop_impl("Point"))
        # Point is not Copy, so p is moved, then used - should error
        assert len(errors) == 1
        assert "use of moved value" in str(errors[0])
        assert "p" in str(errors[0])

    def test_use_after_move_to_variable(self):
        """Moving to another variable then using original should error."""
        errors = check("""
struct Data
    value: i64

fn main() -> i32
    var a: Data = Data { value: 100 }
    var b: Data = a
    return a.value
""" + drop_impl("Data"))
        # a is moved to b, then a.value is accessed - should error
        assert len(errors) == 1
        assert "use of moved value" in str(errors[0])

    def test_multiple_moves(self):
        """Moving same value twice should error."""
        errors = check("""
struct Box
    ptr: *i32

fn consume(b: Box) -> i32
    return 0

fn main() -> i32
    var b: Box = Box { ptr: 0 as *i32 }
    consume(b)
    consume(b)
    return 0
""" + drop_impl("Box"))
        # b is moved first time, second call is use-after-move
        assert len(errors) == 1
        assert "use of moved value" in str(errors[0])


class TestBorrowChecker:
    """Test borrow checking."""

    def test_shared_borrow_ok(self):
        """Single shared borrow should be fine."""
        errors = check("""
fn read_ref(x: @i32) -> i32
    return *x

fn main() -> i32
    var x: i32 = 42
    return read_ref(@x)
""")
        assert len(errors) == 0

    def test_multiple_shared_borrows_ok(self):
        """Multiple shared borrows should be fine."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    let a: @i32 = @x
    let b: @i32 = @x
    return *a + *b
""")
        # Multiple @ borrows are allowed
        # Note: Current simple implementation doesn't track borrow lifetimes perfectly
        # This test documents expected behavior
        assert len(errors) == 0

    def test_mutable_borrow_ok(self):
        """Single mutable borrow should be fine."""
        errors = check("""
fn modify(x:& i32)
    *x = 100

fn main() -> i32
    var x: i32 = 42
    modify(@&x)
    return x
""")
        assert len(errors) == 0

    def test_mutable_borrow_after_shared(self):
        """Mutable borrow after active shared borrow should error."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    let a: @i32 = @x
    let b: @&i32 = @&x
    return *a
""")
        # Can't have @& (mutable) while @ (immutable) exists
        assert len(errors) == 1
        assert "cannot borrow" in str(errors[0])
        assert "mutable" in str(errors[0])

    def test_shared_borrow_after_mutable(self):
        """Shared borrow after active mutable borrow should error."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    let a: @&i32 = @&x
    let b: @i32 = @x
    return *b
""")
        # Can't have @ while @& exists
        assert len(errors) == 1
        assert "cannot borrow" in str(errors[0])
        assert "immutable" in str(errors[0])

    def test_double_mutable_borrow(self):
        """Two mutable borrows should error."""
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    let a: @&i32 = @&x
    let b: @&i32 = @&x
    return 0
""")
        # Can't have two @& to same value
        assert len(errors) == 1
        assert "cannot borrow" in str(errors[0])
        assert "already borrowed as mutable" in str(errors[0])

    def test_borrow_moved_value(self):
        """Borrowing a moved value should error."""
        errors = check("""
struct Data
    x: i32

fn consume(d: Data) -> i32
    return d.x

fn main() -> i32
    var d: Data = Data { x: 42 }
    consume(d)
    let r: @Data = @d
    return 0
""" + drop_impl("Data"))
        # d is moved, then borrowed - should error
        assert len(errors) == 1
        assert "cannot borrow" in str(errors[0])
        assert "moved" in str(errors[0])


class TestFunctionParameters:
    """Test ownership of function parameters."""

    def test_param_owned(self):
        """Parameters start as owned."""
        errors = check("""
struct Data
    x: i32

fn process(d: Data) -> i32
    return d.x
""")
        assert len(errors) == 0

    def test_param_move_then_use(self):
        """Const-borrow param can be reused after call."""
        errors = check("""
struct Data
    x: i32

fn consume(d: Data) -> i32
    return d.x

fn process(d: Data) -> i32
    consume(d)
    return d.x
""")
        # In RERITZ, `d: Data` is a const borrow parameter.
        # Passing it to another const-borrow parameter does not move ownership.
        assert len(errors) == 0

    def test_owned_param_moved_on_then_use(self):
        """A by-value `d: Data` param of a move-only type owns its value
        (§13.2), so passing it on moves it (AGAST #2157). It used to be
        exempt as a 'const borrow', and the callee then dropped a value it
        had already given away."""
        errors = check("""
struct Data
    x: i32

fn consume(d: Data) -> i32
    return d.x

fn process(d: Data) -> i32
    consume(d)
    return d.x
""" + drop_impl("Data"))
        assert len(errors) == 1
        assert "use of moved value: `d`" in str(errors[0])

    def test_param_explicit_move_then_use(self):
        """Explicit move param then use should error."""
        errors = check("""
struct Data
    x: i32

fn consume(d:= Data) -> i32
    return d.x

fn process(d:= Data) -> i32
    consume(d)
    return d.x
""" + drop_impl("Data"))
        # d is explicitly moved to consume, then d.x accessed - error
        assert len(errors) == 1
        assert "use of moved value" in str(errors[0])


class TestTypeInference:
    """Test type inference for ownership checking (Issue #89)."""

    def test_inferred_extern_fn_return_is_copy(self):
        """Inferred type from extern fn should recognize Copy types."""
        errors = check("""
extern fn socket(domain: i32, type_: i32, proto: i32) -> i32

fn main() -> i32
    let fd = socket(2, 1, 0)
    let x = fd + 1
    return fd
""")
        # fd is inferred as i32 from socket() return type
        # i32 is Copy, so fd can be used after being "passed" to + operator
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_inferred_extern_fn_return_passed_to_function(self):
        """Inferred Copy type from extern fn can be passed to function and reused (Issue #89)."""
        errors = check("""
extern fn socket(domain: i32, type_: i32, proto: i32) -> i32
extern fn close(fd: i32) -> i32

fn main() -> i32
    let fd = socket(2, 1, 0)
    close(fd)
    return fd
""")
        # fd is inferred as i32 from socket() return type
        # i32 is Copy, so close(fd) copies it and fd can be used again
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_inferred_regular_fn_return_is_copy(self):
        """Inferred type from regular fn should recognize Copy types."""
        errors = check("""
fn get_value() -> i32
    return 42

fn main() -> i32
    let x = get_value()
    let y = x + 1
    return x
""")
        # x is inferred as i32 from get_value() return type
        # i32 is Copy, so x can be used after being passed to + operator
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_inferred_pointer_is_copy(self):
        """Inferred pointer type should be Copy."""
        errors = check("""
fn get_ptr() -> *i32
    return 0 as *i32

fn main() -> i32
    let p = get_ptr()
    let q = p
    return *p
""")
        # p is inferred as *i32, which is Copy
        assert len(errors) == 0, f"Unexpected errors: {errors}"


class TestControlFlow:
    """Test ownership across control flow."""

    def test_if_else_branches(self):
        """Moves in if/else branches."""
        # TODO: This is a simplified test - full branch analysis is complex
        errors = check("""
fn main() -> i32
    var x: i32 = 42
    if x > 0
        let y: i32 = x
    else
        let z: i32 = x
    return 0
""")
        # i32 is Copy, so this is fine
        assert len(errors) == 0

    def test_loop_move(self):
        """Move in loop - currently we check each iteration independently."""
        # TODO: Proper loop analysis would detect that first iteration moves
        # and second iteration would use-after-move
        errors = check("""
fn main() -> i32
    var x: i32 = 0
    while x < 10
        x = x + 1
    return x
""")
        # i32 is Copy, assignments don't move
        assert len(errors) == 0

    def test_sequential_mutable_borrows_in_loop(self):
        """Sequential mutable borrows to same variable in loop should work.

        This tests that borrows are properly released after each function call,
        allowing multiple calls with mutable borrows in the same loop iteration.
        """
        errors = check("""
extern fn vec_push(v:& i32, val: i32)

fn main() -> i32
    var x: i32 = 0
    while x < 10
        vec_push(@&x, 1)
        vec_push(@&x, 2)
        x = x + 1
    return x
""")
        # Borrows should be released after each vec_push call
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_sequential_mutable_borrows_same_statement(self):
        """Sequential mutable borrow calls in same scope should work."""
        errors = check("""
extern fn modify(v:& i32)

fn main() -> i32
    var x: i32 = 42
    modify(@&x)
    modify(@&x)
    modify(@&x)
    return x
""")
        # Each call should release its borrow before the next
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_mutable_borrow_then_read(self):
        """After mutable borrow call, variable should be usable."""
        errors = check("""
extern fn modify(v:& i32)

fn main() -> i32
    var x: i32 = 42
    modify(@&x)
    return x
""")
        # x should be usable after modify() releases its borrow
        assert len(errors) == 0, f"Unexpected errors: {errors}"


class TestStrViewIsCopy:
    """StrView is a borrowed `{ ptr, len }` view — passing it by value must
    not move it (AGAST #1560). AGAST #98 made bare "..." literals produce
    StrView and documented it as Copy, but never added it to COPY_TYPES, so
    reusing a StrView key after `doc_set_field(@doc, key, ...)` was rejected
    as "use of moved value" (all 29 mausoleum test_document tests)."""

    SV = """
struct StrView
    ptr: *u8
    len: i64

fn takes_sv(s: StrView) -> i64
    return s.len
"""

    def test_annotated_strview_reused_after_by_value_call(self):
        errors = check(self.SV + """
fn main() -> i32
    let key: StrView = "age"
    takes_sv(key)
    takes_sv(key)
    return 0
""")
        assert errors == []

    def test_inferred_strview_literal_reused_after_by_value_call(self):
        errors = check(self.SV + """
fn main() -> i32
    let key = "age"
    takes_sv(key)
    takes_sv(key)
    return 0
""")
        assert errors == []

    def test_drop_struct_still_moves(self):
        """Guard: a Drop struct moves (§13.1)."""
        errors = check(self.SV + """
struct Owned
    p: *u8
    n: i64

fn takes_owned(o: Owned) -> i64
    return o.n

fn main() -> i32
    var o: Owned = Owned { p: null, n: 0 }
    takes_owned(o)
    takes_owned(o)
    return 0
""" + drop_impl("Owned"))
        assert len(errors) == 1
        assert "moved" in str(errors[0])


class TestMoveOnlyFromDrop:
    """§13.1 (AGAST #2157): move-only iff Drop, or a field / enum payload /
    generic argument that is move-only; everything else copies. Replaced a
    hard-coded COPY_TYPES list, under which every struct moved (#1489 Span,
    #1548 Option<i64>)."""

    TWICE = """
fn take(x: {ty}) -> i32
    return 0

fn main() -> i32
    var v: {ty} = {init}
    take(v)
    take(v)
    return 0
"""

    DEFS = """
struct Plain
    x: i32

struct Res
    h: i32

struct Holder
    r: Res

struct Wrap<T>
    inner: T

enum Opt<T>
    Nothing
    Just(T)

enum ResEnum
    Empty
    Has(Res)
""" + drop_impl("Res")

    def _errs(self, ty, init):
        return check(self.DEFS + self.TWICE.format(ty=ty, init=init))

    @pytest.mark.parametrize("ty,init", [
        ("Plain", "Plain { x: 1 }"),
        ("Wrap<i32>", "Wrap<i32> { inner: 1 }"),
        ("Opt<i64>", "Nothing"),
        ("[4]i32", "[1, 2, 3, 4]"),
        ("*Res", "null"),
    ])
    def test_copies(self, ty, init):
        assert self._errs(ty, init) == []

    @pytest.mark.parametrize("ty,init", [
        ("Res", "Res { h: 1 }"),
        ("Holder", "Holder { r: Res { h: 1 } }"),
        ("Wrap<Res>", "Wrap<Res> { inner: Res { h: 1 } }"),
        ("Opt<Res>", "Nothing"),
        ("ResEnum", "Empty"),
        ("[2]Res", "[Res { h: 1 }, Res { h: 2 }]"),
    ])
    def test_moves(self, ty, init):
        errs = self._errs(ty, init)
        assert len(errs) == 1 and "use of moved value: `v`" in str(errs[0]), errs

    def test_lent_to_ref_param_is_not_a_move(self):
        """Auto-borrow into `@T` (#1290) lends; the caller still owns."""
        errs = check(self.DEFS + """
fn peek(r: @Res) -> i32
    return r.h

fn main() -> i32
    var r = Res { h: 1 }
    peek(r)
    peek(r)
    return r.h
""")
        assert errs == []

    def test_assign_to_moved_binding_is_not_a_use(self):
        errs = check(self.DEFS + """
fn take(r: Res) -> i32
    return 0

fn main() -> i32
    var r = Res { h: 1 }
    take(r)
    r = Res { h: 2 }
    return r.h
""")
        assert errs == []

    def test_moves_are_marked_for_the_emitter(self):
        """The emitter clears a drop flag at each Ident marked moves_binding."""
        from parser import parse as _parse
        module = _parse(self.DEFS + """
fn take(r: Res) -> i32
    return 0

fn main() -> i32
    var r = Res { h: 1 }
    let n = r.h
    take(r)
    return n
""")
        assert MoveChecker().check(module) == []
        main = next(i for i in module.items
                    if getattr(i, 'name', None) == 'main')
        call = main.body.stmts[2].expr
        assert getattr(call.args[0], 'moves_binding', False) is True
        n_init = main.body.stmts[1].value
        assert not getattr(n_init.expr, 'moves_binding', False)


class TestMutBorrowParamLends:
    """A `name:& T` parameter borrows its argument (AGAST #1315).

    `Res` implements Drop, so it is move-only and these cases go through the
    lending path. A struct without Drop copies (§13.1) and would pass whether
    or not `:&` lends, which is why the ticket's own repro, kept below as
    `test_ticket_repro_copy_struct`, can't guard this on its own.
    """

    DEFS = drop_impl("Res") + """
struct Res
    h: i32

struct Wrap
    r: Res

struct Outer
    w: Wrap

fn bump(r:& Res)
    r.h += 1

fn eat(r:= Res) -> i32
    return r.h

"""

    def test_ticket_repro_copy_struct(self):
        """The program AGAST #1315 reported, verbatim."""
        assert check("""
struct P
    x: i32

fn bump(p:& P)
    p.x += 1

fn main() -> i32
    var q = P { x: 1 }
    bump(q)
    q.x
""") == []

    @pytest.mark.parametrize("body", [
        pytest.param("""
fn main() -> i32
    var q = Res { h: 1 }
    bump(q)
    return q.h
""", id="read_after_call"),
        pytest.param("""
fn main() -> i32
    var q = Res { h: 1 }
    bump(q)
    bump(q)
    return q.h
""", id="two_calls"),
        pytest.param("""
fn main() -> i32
    var q = Res { h: 1 }
    var i: i32 = 0
    while i < 3
        bump(q)
        i += 1
    return q.h
""", id="call_in_loop"),
        pytest.param("""
fn main() -> i32
    var w = Wrap { r: Res { h: 1 } }
    bump(w.r)
    bump(w.r)
    return w.r.h
""", id="field_of_struct"),
        pytest.param("""
fn main() -> i32
    var o = Outer { w: Wrap { r: Res { h: 1 } } }
    bump(o.w.r)
    bump(o.w.r)
    return o.w.r.h
""", id="field_of_nested_struct"),
        pytest.param("""
fn touch<T>(v:& T) -> i32
    return 0

fn main() -> i32
    var q = Res { h: 1 }
    touch<Res>(q)
    touch<Res>(q)
    return q.h
""", id="generic_fn"),
        pytest.param("""
impl Res
    fn inc(self:& Res)
        self.h += 1

fn main() -> i32
    var q = Res { h: 1 }
    q.inc()
    q.inc()
    return q.h
""", id="method_receiver"),
        pytest.param("""
struct Poker
    n: i32

impl Poker
    fn poke(self:& Poker, r:& Res)
        r.h += self.n

fn main() -> i32
    var p = Poker { n: 1 }
    var q = Res { h: 1 }
    p.poke(q)
    p.poke(q)
    return q.h
""", id="method_argument"),
        pytest.param("""
fn twice(r:& Res)
    bump(r)
    bump(r)
    r.h += 1

fn main() -> i32
    var q = Res { h: 1 }
    twice(q)
    return q.h
""", id="reborrow_in_callee"),
        pytest.param("""
fn main() -> i32
    var q = Res { h: 1 }
    bump(q)
    return eat(q)
""", id="move_after_borrow"),
    ])
    def test_lends(self, body):
        assert check(self.DEFS + body) == []

    def test_owned_param_still_moves(self):
        """Control: `:=` takes ownership, so the same read is an error."""
        errs = check(self.DEFS + """
fn main() -> i32
    var q = Res { h: 1 }
    eat(q)
    return q.h
""")
        assert len(errs) == 1 and "use of moved value: `q`" in str(errs[0])

    def test_lending_a_moved_value_is_rejected(self):
        """Lending needs a live value: a `:&` call doesn't revive `q`."""
        errs = check(self.DEFS + """
fn main() -> i32
    var q = Res { h: 1 }
    eat(q)
    bump(q)
    return 0
""")
        assert len(errs) == 1 and "use of moved value: `q`" in str(errs[0])


class TestMoveOutOfMutBorrowParam:
    """A `name:& T` parameter can't be moved out of (AGAST #2231).

    The caller keeps ownership of a lent value, so a by-value use in the
    callee would give it two owners and two drops. Reads stay legal:
    `test_reads_are_accepted` is what a blanket "any by-value use is an
    error" would wrongly reject.
    """

    DEFS = drop_impl("Res") + """
struct Res
    h: i32

struct Wrap
    r: Res

struct Deep
    w: Wrap

enum Slot
    Full(Res)
    Empty

struct Box1
    s: Slot

impl Wrap
    fn put(self: @Wrap, r:= Res) -> i32
        return r.h

impl Res
    fn burn(self:= Res) -> i32
        return self.h

    fn look(self: @Res) -> i32
        return self.h

    fn keep(self:& Res) -> i32
        return self.h

fn eat(r:= Res) -> i32
    return r.h

fn see(r: @Res) -> i32
    return r.h

fn seep(r: *Res) -> i32
    return r.h

fn bump(r:& Res)
    r.h += 1

"""

    @pytest.mark.parametrize("body, param", [
        pytest.param("""
fn f(t:& Res) -> i32
    return eat(t)
""", "t", id="call_argument"),
        pytest.param("""
fn f(t:& Res) -> i32
    let u = t
    return u.h
""", "t", id="let"),
        pytest.param("""
fn f(t:& Res) -> i32
    var u = t
    return u.h
""", "t", id="var"),
        pytest.param("""
fn f(t:& Res) -> i32
    let u: Res = t
    return u.h
""", "t", id="let_annotated_by_value"),
        pytest.param("""
fn f(t:& Res) -> i32
    var p: *Res = t
    return p.h
""", "t", id="var_as_pointer"),
        pytest.param("""
fn f(t:& Res) -> Res
    return t
""", "t", id="return"),
        pytest.param("""
fn f(t:& Res) -> Res
    t
""", "t", id="tail"),
        pytest.param("""
fn f(t:& Res, c: i32) -> Res
    if c == 1
        t
    else
        Res { h: 2 }
""", "t", id="if_tail"),
        pytest.param("""
fn f(t:& Res) -> i32
    var u = Res { h: 2 }
    u = t
    return u.h
""", "t", id="assignment"),
        pytest.param("""
fn f(t:& Res) -> i32
    let w = Wrap { r: t }
    return w.r.h
""", "t", id="struct_literal_field"),
        pytest.param("""
fn f(t:& Res) -> i32
    let s = Slot.Full(t)
    return 0
""", "t", id="variant_payload"),
        pytest.param("""
fn f(t:& Res) -> i32
    var w = Wrap { r: Res { h: 1 } }
    return w.put(t)
""", "t", id="method_argument"),
        pytest.param("""
fn f(t:& Res) -> i32
    return eat((t))
""", "t", id="grouped"),
        pytest.param("""
fn f(t:& Res) -> i32
    return eat(*t)
""", "t", id="deref"),
        pytest.param("""
fn f(w:& Wrap) -> i32
    return eat(w.r)
""", "w", id="field"),
        pytest.param("""
fn f(d:& Deep) -> i32
    return eat(d.w.r)
""", "d", id="nested_field"),
        pytest.param("""
fn f(d:& Deep) -> i32
    return eat((d.w).r)
""", "d", id="grouped_nested_field"),
        pytest.param("""
fn f(d:& Deep) -> i32
    let w = d.w
    return w.r.h
""", "d", id="nested_field_into_let"),
        pytest.param("""
impl Res
    fn burn(self:& Res) -> i32
        return eat(self)
""", "self", id="mut_self"),
        pytest.param("""
fn f(t:& Res) -> i32
    let a = [t]
    return 0
""", "t", id="array_element"),
        pytest.param("""
fn f(t:& Res) -> i32
    let a = (t, 1)
    return 0
""", "t", id="tuple_element"),
        pytest.param("""
fn f(w:& Wrap) -> i32
    let a = [w.r]
    return 0
""", "w", id="array_element_field"),
        pytest.param("""
fn f(t:& Res) -> i32
    let a = (*t, 1)
    return 0
""", "t", id="tuple_element_deref"),
        pytest.param("""
fn f(t:& Res) -> i32
    [t]
    return 0
""", "t", id="array_element_of_a_temporary"),
    ])
    def test_move_out_is_rejected(self, body, param):
        errs = check(self.DEFS + body)
        assert len(errs) == 1, errs
        assert f"cannot move out of borrowed parameter `{param}`" in str(errs[0])

    def test_ticket_repro(self):
        """The program AGAST #2231 reported."""
        errs = check(self.DEFS + """
fn steal(t:& Res) -> i32
    return eat(t)

fn main() -> i32
    var t = Res { h: 1 }
    steal(t)
    return 0
""")
        assert len(errs) == 1
        assert "cannot move out of borrowed parameter `t`" in str(errs[0])

    def test_rejected_move_does_not_mark_moved(self):
        """Each by-value use is its own error, and neither says "moved":
        the parameter still holds the caller's value."""
        errs = check(self.DEFS + """
fn f(t:& Res) -> i32
    eat(t)
    return eat(t)
""")
        assert len(errs) == 2
        assert all("cannot move out of borrowed parameter `t`" in str(e) for e in errs)

    def test_error_points_at_the_use(self):
        errs = check(self.DEFS + """
fn f(t:& Res) -> i32
    return eat(t)
""")
        assert errs[0].span is not None and errs[0].span.column == 16

    def test_reported_once_in_a_loop(self):
        errs = check(self.DEFS + """
fn f(t:& Res) -> i32
    var i = 0
    while i < 2
        eat(t)
        i += 1
    return 0
""")
        assert len(errs) == 1

    @pytest.mark.parametrize("body", [
        pytest.param("""
fn f(t:& Res) -> i32
    return t.h
""", id="copy_field"),
        pytest.param("""
fn f(t:& Res) -> i32
    bump(t)
    bump(t)
    return see(t) + seep(t)
""", id="relend"),
        pytest.param("""
fn f(t:& Res) -> i32
    return see(@t)
""", id="explicit_borrow"),
        pytest.param("""
fn touch<T>(v:& T) -> i32
    return 1

fn f(t:& Res) -> i32
    return touch(t)
""", id="relend_to_generic"),
        pytest.param("""
fn touch<T>(v:& T) -> i32
    return 1

fn f(t:& Res) -> i32
    return touch<Res>(t)
""", id="relend_to_explicit_generic"),
        pytest.param("""
impl Res
    fn inc(self:& Res)
        self.h += 1

fn f(t:& Res) -> i32
    t.inc()
    return t.h
""", id="method_receiver"),
        pytest.param("""
impl Wrap
    fn poke(self: @Wrap, r:& Res) -> i32
        return r.h

fn f(t:& Res) -> i32
    var w = Wrap { r: Res { h: 1 } }
    return w.poke(t)
""", id="relend_to_method_argument"),
        pytest.param("""
fn f(t:& Res) -> i32
    let p: @Res = t
    return p.h
""", id="let_as_reference"),
        pytest.param("""
fn f(t:& Res) -> i32
    let p: *Res = t
    return p.h
""", id="let_as_pointer"),
        pytest.param("""
fn f(w:& Wrap) -> i32
    let p: @Res = w.r
    return p.h
""", id="let_field_as_reference"),
        pytest.param("""
fn f(w:& Wrap) -> i32
    bump(w.r)
    return w.r.h
""", id="field_relend"),
        pytest.param("""
fn f(d:& Deep) -> i32
    return d.w.r.h
""", id="nested_copy_field"),
        pytest.param("""
fn f(s:& Slot) -> i32
    match s
        Full(r) => return r.h
        Empty => return 0
""", id="match_param"),
        pytest.param("""
fn f(s:& Slot) -> i32
    match (s)
        Full(_) => return 1
        Empty => return 0
""", id="match_grouped"),
        pytest.param("""
fn f(b:& Box1) -> i32
    match b.s
        Full(r) => return r.h
        Empty => return 0
""", id="match_field"),
        pytest.param("""
fn f(t:& [2]Res) -> i32
    var n: i32 = 0
    for r in t
        n += 1
    return n
""", id="for_iterates_in_place"),
        pytest.param("""
fn f(t:& Res) -> i32
    t = Res { h: 2 }
    return t.h
""", id="assign_through"),
        pytest.param("""
fn f(t:& Res) -> i32
    t.h = 2
    return t.h
""", id="field_assign_through"),
        pytest.param("""
fn f(t:& Res) -> i32
    let t = Res { h: 3 }
    return eat(t)
""", id="shadowed_by_an_owner"),
    ])
    def test_reads_are_accepted(self, body):
        assert check(self.DEFS + body) == []

    @pytest.mark.parametrize("param", ["t: Res", "t:= Res"])
    def test_owning_param_still_moves(self, param):
        """Control: an owning parameter moves, so reuse is "use of moved"."""
        errs = check(self.DEFS + f"""
fn f({param}) -> i32
    eat(t)
    return eat(t)
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_owned_match_still_moves(self):
        """Control: only a lent scrutinee is a read."""
        errs = check(self.DEFS + """
fn f(s:= Slot) -> i32
    match s
        Full(r) => eat(r)
        Empty => 0
    match s
        _ => 0
""")
        assert len(errs) == 1 and "use of moved value: `s`" in str(errs[0])

    def test_annotated_let_of_an_owner_still_moves(self):
        """Control: the reference-annotated `let` exemption is for lent
        parameters; an owner's behaviour there is unchanged."""
        errs = check(self.DEFS + """
fn f(t:= Res) -> i32
    let p: @Res = t
    return t.h
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_copy_param_is_not_a_move_out(self):
        """Control: without Drop the value copies, so nothing moves."""
        assert check("""
struct P
    x: i32

fn take(p: P) -> i32
    return p.x

fn f(p:& P) -> i32
    let q = p
    let r = *p
    return take(p) + q.x + r.x
""") == []

    @pytest.mark.parametrize("body, param", [
        pytest.param("""
fn f(t:& Res) -> i32
    return t.burn()
""", "t", id="param"),
        pytest.param("""
fn f(t:& Res) -> i32
    return (t).burn()
""", "t", id="grouped"),
        pytest.param("""
fn f(t:& Res) -> i32
    return (*t).burn()
""", "t", id="deref"),
        pytest.param("""
fn f(w:& Wrap) -> i32
    return w.r.burn()
""", "w", id="field"),
        pytest.param("""
fn f(d:& Deep) -> i32
    return d.w.r.burn()
""", "d", id="nested_field"),
        pytest.param("""
impl Wrap
    fn spend(self:& Wrap) -> i32
        return self.r.burn()
""", "self", id="self_param"),
    ])
    def test_by_value_receiver_is_a_move_out(self, body, param):
        """`t.burn()` takes the receiver by value, so on a lent `t` it's the
        same move out as `eat(t)` (AGAST #2239)."""
        errs = check(self.DEFS + body)
        assert len(errs) == 1, errs
        assert f"cannot move out of borrowed parameter `{param}`" in str(errs[0])

    def test_lending_receivers_are_accepted(self):
        """Control: a method that borrows its receiver only reads it."""
        assert check(self.DEFS + """
fn f(t:& Res, w:& Wrap) -> i32
    return t.look() + t.keep() + w.r.look()
""") == []


class TestByValueReceiver:
    """A method that takes `self` by value moves its receiver (AGAST #2239).

    `self:= T`, `self: T` and bare `self` are all by-value parameters
    (LANGUAGE_SPEC §5.4, §13.2). The method is found on the receiver's own
    type: other types' methods of that name say nothing about this call.
    """

    DEFS = drop_impl("T") + """
struct T
    id: i32

struct H
    t: T
    u: T

impl T
    fn burn(self:= T) -> i32
        return self.id

    fn typed(self: T) -> i32
        return self.id

    fn bare(self) -> i32
        return self.id

    fn look(self: @T) -> i32
        return self.id

    fn poke(self: @&T) -> i32
        return self.id

    fn keep(self:& T) -> i32
        return self.id

    fn make(id: i32) -> T
        return T { id: id }

fn eat(t:= T) -> i32
    return t.id

"""

    @pytest.mark.parametrize("method", ["burn", "typed", "bare"])
    def test_use_after_receiver_moved(self, method):
        errs = check(self.DEFS + f"""
fn f(t:= T) -> i32
    t.{method}()
    return t.id
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    @pytest.mark.parametrize("method", ["look", "poke", "keep"])
    def test_lending_method_keeps_the_receiver(self, method):
        assert check(self.DEFS + f"""
fn f(t:= T) -> i32
    t.{method}()
    t.{method}()
    return eat(t)
""") == []

    def test_second_by_value_call_is_a_use_after_move(self):
        errs = check(self.DEFS + """
fn f(t:= T) -> i32
    t.burn()
    return t.burn()
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_argument_reads_the_receiver_after_it_moved(self):
        """The receiver is evaluated first, so it has gone by the argument."""
        errs = check(self.DEFS + """
impl T
    fn plus(self:= T, n: i32) -> i32
        return self.id + n

fn f(t:= T) -> i32
    return t.plus(t.id)
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_receiver_field_moves_that_field_only(self):
        assert check(self.DEFS + """
fn f(h:= H) -> i32
    h.t.burn()
    return h.u.burn()
""") == []
        errs = check(self.DEFS + """
fn f(h:= H) -> i32
    h.t.burn()
    return h.t.id
""")
        assert len(errs) == 1 and "use of moved value: `h.t`" in str(errs[0])

    def test_moved_in_a_loop(self):
        errs = check(self.DEFS + """
fn f(t:= T) -> i32
    var i = 0
    while i < 2
        t.burn()
        i += 1
    return 0
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_reassigned_receiver_is_usable_again(self):
        assert check(self.DEFS + """
fn f() -> i32
    var t = T { id: 1 }
    t.burn()
    t = T { id: 2 }
    return t.burn()
""") == []

    def test_copy_receiver_stays_usable(self):
        assert check(self.DEFS + """
struct P
    x: i32

impl P
    fn get(self) -> i32
        return self.x

fn f(p: P) -> i32
    p.get()
    return p.get()
""") == []

    def test_alias_of_the_receiver_type(self):
        errs = check(self.DEFS + """
type Alias = T

fn f(t:= Alias) -> i32
    t.burn()
    return t.id
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_generic_receiver(self):
        errs = check("""
trait Drop
    fn drop(self: @&Self)

struct G<V>
    v: V

impl<V> Drop for G<V>
    fn drop(self: @&G<V>)
        pass

impl<V> G<V>
    fn burn(self:= G<V>) -> i32
        return 0

fn f(g:= G<i32>) -> i32
    g.burn()
    return g.burn()
""")
        assert len(errs) == 1 and "use of moved value: `g`" in str(errs[0])

    def test_another_types_lending_method_does_not_save_the_receiver(self):
        """`name` matching every impl would call `t.size()` lending."""
        errs = check(self.DEFS + """
struct U
    n: i32

impl U
    fn size(self: @U) -> i32
        return self.n

impl T
    fn size(self) -> i32
        return self.id

fn f(t:= T) -> i32
    t.size()
    return t.id
""")
        assert len(errs) == 1 and "use of moved value: `t`" in str(errs[0])

    def test_another_types_by_value_method_does_not_move_the_receiver(self):
        """`peek` on U is by value and on T lends: T's receiver stays."""
        assert check(self.DEFS + """
struct U
    n: i32

impl U
    fn peek(self) -> i32
        return self.n

impl T
    fn peek(self: @T) -> i32
        return self.id

fn f(t:= T) -> i32
    t.peek()
    return eat(t)
""") == []

    def test_method_only_another_type_has_does_not_move(self):
        """A method T has no impl of (a UFCS fallback, say) isn't known to
        take T by value."""
        assert check(self.DEFS + """
struct U
    n: i32

impl U
    fn only_u(self) -> i32
        return self.n

fn f(t:= T) -> i32
    t.only_u()
    return eat(t)
""") == []

    def test_associated_fn_called_on_a_value_does_not_move(self):
        """No `self`, so no receiver to take."""
        assert check(self.DEFS + """
fn f(t:= T) -> i32
    t.make(1)
    return eat(t)
""") == []

    def test_pointer_receiver_does_not_move_the_pointer(self):
        """Control: `@T` and `*T` copy; what a by-value method on one should
        mean is the #2227 question."""
        assert check(self.DEFS + """
fn f(r: @T, p: *T) -> i32
    r.burn()
    p.burn()
    return r.burn() + p.burn()
""") == []


class TestMethodCallBindingType:
    """A binding from a method call has that method's return type (AGAST
    #2257), so it moves and drops once. The method is found on the receiver's
    own type, for `Type.method()` and `value.method()` alike: other types'
    methods of that name say nothing about this call.
    """

    DEFS = drop_impl("T") + """
struct T
    id: i32

struct H
    t: T

struct Box<X>
    v: X

trait Named
    fn name(self: @T) -> i32

impl T
    fn new(id: i32) -> T
        return T { id: id }

    fn open(id: i32) -> Result<T, i32>
        return Ok(T { id: id })

    fn again(self: @T) -> T
        return T { id: self.id }

    fn twin(self: @T) -> Self
        return T { id: self.id }

    fn look(self: @T) -> i32
        return self.id

    fn len(self: @T) -> T
        return T { id: self.id }

    fn name(self: @T) -> T
        return T { id: self.id }

impl Named for T
    fn name(self: @T) -> i32
        return self.id

impl<X> Box<X>
    fn get(self: @Box<X>) -> X
        return self.v

# Same method names as T's, on a type that copies.
struct C
    n: i32

impl C
    fn new(n: i32) -> i32
        return n

    fn again(self: @C) -> i32
        return self.n

fn eat(t: T) -> i32
    return t.id

"""

    def moved_twice(self, setup: str, name: str = "u") -> list:
        """Errors for using `name`, bound by `setup`, by value twice."""
        return check(self.DEFS + f"""
fn f(t: T, p: @T, h: H, bt: Box<T>, bi: Box<i32>, c: C) -> i32
    {setup}
    var a = {name}
    var b = {name}
    return 0
""")

    def assert_moves(self, setup: str, name: str = "u"):
        errors = self.moved_twice(setup, name)
        assert any(f"use of moved value: `{name}`" in str(e) for e in errors), errors

    def assert_copies(self, setup: str, name: str = "u"):
        assert self.moved_twice(setup, name) == []

    def test_static_call(self):
        self.assert_moves("var u = T.new(1)")

    def test_let_binding(self):
        self.assert_moves("let u = T.new(1)")

    def test_value_receiver(self):
        self.assert_moves("var u = t.again()")

    def test_reference_receiver(self):
        self.assert_moves("var u = p.again()")

    def test_field_receiver(self):
        self.assert_moves("var u = h.t.again()")

    def test_chained_on_a_method_result(self):
        self.assert_moves("var u = T.new(1).again()")

    def test_try_unwraps_the_declared_result(self):
        self.assert_moves("var u = T.open(1)?")

    def test_self_return_is_the_receiver_type(self):
        self.assert_moves("var u = t.twin()")

    def test_generic_return_takes_the_receiver_argument(self):
        self.assert_moves("var u = bt.get()")

    def test_generic_return_of_a_copy_argument_copies(self):
        self.assert_copies("var u = bi.get()")

    def test_copy_return_copies(self):
        self.assert_copies("var u = t.look()")

    def test_other_type_of_the_same_method_name_copies(self):
        self.assert_copies("var u = c.again()")

    def test_static_call_on_other_type_of_the_same_method_name_copies(self):
        self.assert_copies("var u = C.new(1)")

    def test_binding_named_like_a_type_is_the_receiver(self):
        # `C` here is a T, so this is T.again, not C.again.
        self.assert_moves("var C = T.new(1)\n    var u = C.again()")

    def test_declared_method_beats_the_name_heuristic(self):
        self.assert_moves("var u = t.len()")

    def test_undeclared_method_copies(self):
        self.assert_copies("var u = t.nothing()")

    def test_impls_disagreeing_on_the_return_type_copy(self):
        # A wrong "move" rejects a valid program (MoveTypes).
        self.assert_copies("var u = t.name()")


class TestArrayTupleLiteralMoves:
    """An array or tuple literal owns its elements (AGAST #2238), so a
    move-only binding used as an element moves into the literal, wherever
    the literal itself goes."""

    DEFS = drop_impl("Res") + """
struct Res
    h: i32

struct Holder
    r: Res
    n: i32

struct Point
    x: i32

fn make() -> Res
    return Res { h: 1 }

fn see(r: @Res) -> i32
    return r.h
"""

    LITERALS = [
        pytest.param("let a = [t]", id="array"),
        pytest.param("let a = (t, 1)", id="tuple"),
        pytest.param("let a = [1, t]", id="array_not_first"),
        pytest.param("let a = (1, t)", id="tuple_not_first"),
        pytest.param("let a = [(t)]", id="grouped"),
        pytest.param("let a = [(t, 1)]", id="tuple_in_array"),
        pytest.param("let a = ([t], 1)", id="array_in_tuple"),
        pytest.param("[t]", id="array_statement"),
        pytest.param("(t, 1)", id="tuple_statement"),
    ]

    @pytest.mark.parametrize("literal", LITERALS)
    def test_use_after_the_literal_is_rejected(self, literal):
        errs = check(self.DEFS + f"""
fn f() -> i32
    var t = make()
    {literal}
    return t.h
""")
        assert len(errs) == 1, errs
        assert "use of moved value: `t`" in str(errs[0])

    @pytest.mark.parametrize("literal", LITERALS)
    def test_element_binding_is_marked_moved(self, literal):
        """The emitter clears the binding's drop flag at this mark; without
        it the binding and the literal both drop the value."""
        module = parse(self.DEFS + f"""
fn f() -> i32
    var t = make()
    {literal}
    return 0
""")
        assert MoveChecker().check(module) == []
        fn = next(i for i in module.items if getattr(i, 'name', '') == 'f')
        marks = []

        def walk(node):
            if getattr(node, 'moves_binding', False):
                marks.append(node.name)
            for child in vars(node).values() if hasattr(node, '__dict__') else ():
                for c in child if isinstance(child, list) else [child]:
                    if hasattr(c, 'span'):
                        walk(c)
        walk(fn.body)
        assert marks == ['t']

    @pytest.mark.parametrize("literal", ["[t, t]", "(t, t)"])
    def test_same_binding_twice_is_rejected(self, literal):
        errs = check(self.DEFS + f"""
fn f() -> i32
    var t = make()
    let a = {literal}
    return 0
""")
        assert len(errs) == 1, errs
        assert "use of moved value: `t`" in str(errs[0])

    @pytest.mark.parametrize("literal", ["[t]", "(t, 1)"])
    def test_element_of_a_moved_binding_is_rejected(self, literal):
        errs = check(self.DEFS + f"""
fn f() -> i32
    var t = make()
    let u = t
    let a = {literal}
    return 0
""")
        assert len(errs) == 1, errs
        assert "use of moved value: `t`" in str(errs[0])

    @pytest.mark.parametrize("param", ["t: Res", "t:= Res"])
    @pytest.mark.parametrize("literal", ["[t]", "(t, 1)"])
    def test_owning_param_moves(self, param, literal):
        errs = check(self.DEFS + f"""
fn f({param}) -> i32
    let a = {literal}
    return t.h
""")
        assert len(errs) == 1, errs
        assert "use of moved value: `t`" in str(errs[0])

    def test_move_in_a_loop_is_rejected(self):
        errs = check(self.DEFS + """
fn f() -> i32
    var t = make()
    var i = 0
    while i < 2
        let a = [t]
        i += 1
    return 0
""")
        assert len(errs) == 1, errs
        assert "use of moved value: `t`" in str(errs[0])

    @pytest.mark.parametrize("literal", ["[h.r]", "(h.r, 1)"])
    def test_field_element_moves_only_that_field(self, literal):
        assert check(self.DEFS + f"""
fn f() -> i32
    var h = Holder {{ r: make(), n: 1 }}
    let a = {literal}
    return h.n
""") == []
        errs = check(self.DEFS + f"""
fn f() -> i32
    var h = Holder {{ r: make(), n: 1 }}
    let a = {literal}
    return h.r.h
""")
        assert len(errs) == 1, errs
        assert "use of moved value: `h.r`" in str(errs[0])

    @pytest.mark.parametrize("body", [
        pytest.param("""
fn f() -> i32
    var t = make()
    let a = [t]
    t = make()
    return t.h
""", id="assigned_again"),
        pytest.param("""
fn f() -> i32
    let p = Point { x: 1 }
    let a = [p, p]
    let b = (p, p)
    return p.x
""", id="copy_struct"),
        pytest.param("""
fn f() -> i32
    let n = 1
    let a = [n, n]
    let b = (n, n)
    return n
""", id="copy_scalar"),
        pytest.param("""
fn f(t: @Res) -> i32
    let a = [t, t]
    let b = (t, t)
    return t.h
""", id="reference_param"),
        pytest.param("""
fn f() -> i32
    var t = make()
    let a = [@t]
    let b = (@t, 1)
    return t.h
""", id="borrowed_element"),
        pytest.param("""
fn f() -> i32
    var t = make()
    let a = [see(@t), see(@t)]
    return t.h
""", id="element_reads_the_binding"),
        pytest.param("""
fn f() -> i32
    var t = make()
    let a = [t.h, t.h]
    return t.h
""", id="copy_field_element"),
    ])
    def test_non_moves_are_accepted(self, body):
        assert check(self.DEFS + body) == []

    @pytest.mark.parametrize("value, is_temp", [
        pytest.param("[make()]", True, id="array"),
        pytest.param("(make(), 1)", True, id="tuple"),
        pytest.param("[1]", False, id="copy_array"),
        pytest.param("(1, 2)", False, id="copy_tuple"),
    ])
    def test_unowned_literal_is_a_temporary(self, value, is_temp):
        module = parse(self.DEFS + f"""
fn f() -> i32
    {value}
    return 0
""")
        assert MoveChecker().check(module) == []
        fn = next(i for i in module.items if getattr(i, 'name', '') == 'f')
        literal = fn.body.stmts[0].expr
        assert (getattr(literal, 'drop_temp', None) is not None) == is_temp
        # The literal owns its element, so the element is no temporary.
        assert getattr(literal.elements[0], 'drop_temp', None) is None

    @pytest.mark.parametrize("value", ["[make()]", "(make(), 1)"])
    def test_owned_literal_is_not_a_temporary(self, value):
        module = parse(self.DEFS + f"""
fn f() -> i32
    let a = {value}
    return 0
""")
        assert MoveChecker().check(module) == []
        fn = next(i for i in module.items if getattr(i, 'name', '') == 'f')
        assert getattr(fn.body.stmts[0].value, 'drop_temp', None) is None


class TestLoopsMatchesTemporaries:
    """AGAST #2161: loop bodies see the previous iteration's moves, match
    arms start from the same state, and unowned move-only values are
    marked as temporaries for the emitter to drop."""

    DEFS = """
struct Res
    h: i32

enum Slot
    Full(Res)
    Empty

fn make() -> Res
    return Res { h: 1 }

fn take(r: Res) -> i32
    return 0

impl Res
    fn peek(self: @Res) -> i32
        return self.h
    fn into(self: Res) -> i32
        return self.h
""" + drop_impl("Res")

    def test_move_in_loop_reported_once(self):
        errs = check(self.DEFS + """
fn main() -> i32
    var r = make()
    var i = 0
    while i < 3
        take(r)
        i = i + 1
    return 0
""")
        assert len(errs) == 1 and "use of moved value: `r`" in str(errs[0]), errs

    def test_for_loop_move_rejected(self):
        errs = check(self.DEFS + """
fn main() -> i32
    var r = make()
    for i in 0..3
        take(r)
    return 0
""")
        assert len(errs) == 1 and "use of moved value: `r`" in str(errs[0]), errs

    def test_match_arms_start_from_the_same_state(self):
        errs = check(self.DEFS + """
fn main() -> i32
    var r = make()
    var k = 1
    match k
        1 => take(r)
        _ => take(r)
    return 0
""")
        assert errs == []

    def test_match_arm_that_breaks_takes_its_move_out_of_the_loop(self):
        errs = check(self.DEFS + """
fn main() -> i32
    var r = make()
    var i = 0
    while i < 3
        i = i + 1
        match i
            2 =>
                take(r)
                break
            _ => 0
    return 0
""")
        assert errs == []

    def _main(self, body):
        module = parse(self.DEFS + "fn main() -> i32\n" + body)
        assert MoveChecker().check(module) == []
        return next(i for i in module.items if getattr(i, 'name', None) == 'main')

    def test_unowned_call_is_a_temporary(self):
        main = self._main("    make()\n    var v = make()\n    return 0\n")
        assert getattr(main.body.stmts[0].expr, 'drop_temp', None) is not None
        assert getattr(main.body.stmts[1].value, 'drop_temp', None) is None

    def test_variant_payload_is_owned_not_temporary(self):
        main = self._main("    var s = Slot.Full(make())\n    return 0\n")
        assert getattr(main.body.stmts[0].value.args[0], 'drop_temp', None) is None

    def test_receiver_lent_or_moved(self):
        main = self._main("    let a = make().peek()\n    let b = make().into()\n    return 0\n")
        assert getattr(main.body.stmts[0].value.expr, 'drop_temp', None) is not None
        assert getattr(main.body.stmts[1].value.expr, 'drop_temp', None) is None
