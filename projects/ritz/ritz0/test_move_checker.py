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
