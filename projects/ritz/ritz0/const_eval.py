"""
Constant Expression Evaluator for Ritz

Evaluates compile-time constant expressions for use in:
- Array size declarations: [SIZE]u8, [1 << 9]u32
- static_assert conditions (future)
- const fn evaluation (future)
"""

import dataclasses
import functools
from typing import Dict, Any, Iterable, Optional, Union
import ritz_ast as rast


class ConstEvalError(Exception):
    """Raised when a constant expression cannot be evaluated."""
    pass


class ConstEvaluator:
    """Evaluates constant expressions at compile time.

    Supports:
    - Integer literals
    - Named constants
    - Binary operations: +, -, *, /, %, <<, >>, &, |, ^
    - Unary operations: -, ~, ! (logical: 0 -> 1, nonzero -> 0)
    - Char and bool literals, `as` casts (the value is kept; the target's
      own type governs its use), parenthesized expressions

    `/` and `%` truncate toward zero, as the generated sdiv/srem do.
    """

    def __init__(self, constants: Optional[Dict[str, int]] = None,
                 u64_names: Iterable[str] = ()):
        """Initialize with known constants.

        Args:
            constants: Dict mapping constant names to their values
            u64_names: The names among them declared `u64`
        """
        self.constants: Dict[str, int] = constants or {}
        self.u64_names = frozenset(u64_names)

    def add_constant(self, name: str, value: int) -> None:
        """Register a constant for use in expressions."""
        self.constants[name] = value

    def _is_u64(self, expr: rast.Expr) -> bool:
        """Is `expr` a u64? The emitter's _int_shape, for the width a fold can
        lose: a literal only a u64 can hold, a u64 const, `as u64`, and any
        operator over those. A shift's count does not count (#2356)."""
        if isinstance(expr, rast.IntLit):
            return expr.value >= 1 << 63
        if isinstance(expr, rast.Ident):
            return expr.name in self.u64_names
        if isinstance(expr, rast.Cast):
            return getattr(expr.target, 'name', None) == 'u64'
        if isinstance(expr, rast.UnaryOp):
            return self._is_u64(expr.operand)
        if isinstance(expr, rast.BinOp):
            if expr.op in ('<<', '>>'):
                return self._is_u64(expr.left)
            return self._is_u64(expr.left) or self._is_u64(expr.right)
        return False

    def evaluate(self, expr: rast.Expr) -> int:
        """Evaluate a constant expression to an integer.

        Args:
            expr: The AST expression to evaluate

        Returns:
            The computed integer value

        Raises:
            ConstEvalError: If the expression cannot be evaluated at compile time
        """
        if isinstance(expr, (rast.IntLit, rast.CharLit)):
            return expr.value

        elif isinstance(expr, rast.BoolLit):
            return 1 if expr.value else 0

        elif isinstance(expr, rast.Cast):
            return self.evaluate(expr.expr)

        elif isinstance(expr, rast.Ident):
            name = expr.name
            if name not in self.constants:
                raise ConstEvalError(
                    f"Unknown constant '{name}' in constant expression"
                )
            return self.constants[name]

        elif isinstance(expr, rast.UnaryOp):
            operand = self.evaluate(expr.operand)
            if expr.op == '-':
                return -operand
            elif expr.op == '~':
                return ~operand
            elif expr.op == '!':
                return 1 if operand == 0 else 0
            else:
                raise ConstEvalError(
                    f"Unsupported unary operator '{expr.op}' in constant expression"
                )

        elif isinstance(expr, rast.BinOp):
            left = self.evaluate(expr.left)
            right = self.evaluate(expr.right)

            op = expr.op
            if op == '+':
                return left + right
            elif op == '-':
                return left - right
            elif op == '*':
                return left * right
            elif op == '/':
                if right == 0:
                    raise ConstEvalError("Division by zero in constant expression")
                quotient = abs(left) // abs(right)
                return quotient if (left < 0) == (right < 0) else -quotient
            elif op == '%':
                if right == 0:
                    raise ConstEvalError("Modulo by zero in constant expression")
                remainder = abs(left) % abs(right)
                return -remainder if left < 0 else remainder
            elif op == '<<':
                if right < 0:
                    raise ConstEvalError("Negative shift amount in constant expression")
                return left << right
            elif op == '>>':
                if right < 0:
                    raise ConstEvalError("Negative shift amount in constant expression")
                # A folded u64 is kept in its signed form (#2356).
                if self._is_u64(expr.left):
                    left &= (1 << 64) - 1
                return left >> right
            elif op == '&':
                return left & right
            elif op == '|':
                return left | right
            elif op == '^':
                return left ^ right
            # Comparison operators (return 1 for true, 0 for false)
            elif op == '==':
                return 1 if left == right else 0
            elif op == '!=':
                return 1 if left != right else 0
            elif op == '<':
                return 1 if left < right else 0
            elif op == '<=':
                return 1 if left <= right else 0
            elif op == '>':
                return 1 if left > right else 0
            elif op == '>=':
                return 1 if left >= right else 0
            # Logical operators
            elif op == '&&':
                return 1 if (left != 0 and right != 0) else 0
            elif op == '||':
                return 1 if (left != 0 or right != 0) else 0
            else:
                raise ConstEvalError(
                    f"Unsupported binary operator '{op}' in constant expression"
                )

        elif isinstance(expr, rast.Grouped):
            return self.evaluate(expr.expr)

        else:
            raise ConstEvalError(
                f"Expression type '{type(expr).__name__}' cannot be evaluated at compile time"
            )

    def try_evaluate(self, expr: rast.Expr) -> Optional[int]:
        """Try to evaluate an expression, returning None on failure."""
        try:
            return self.evaluate(expr)
        except ConstEvalError:
            return None


def evaluate_const_expr(expr: rast.Expr, constants: Dict[str, int] = None) -> int:
    """Convenience function to evaluate a constant expression.

    Args:
        expr: The expression to evaluate
        constants: Optional dict of known constants

    Returns:
        The computed integer value
    """
    evaluator = ConstEvaluator(constants)
    return evaluator.evaluate(expr)


class ConstEvalPass:
    """AST pass that evaluates constant expressions in array sizes and static_assert.

    This pass should run after name resolution and before emission.
    It transforms ArrayType nodes with expression sizes to have integer sizes,
    and evaluates static_assert conditions.
    """

    def __init__(self):
        self.evaluator = ConstEvaluator()
        self.errors: list = []

    def process_module(self, module: rast.Module) -> list:
        """Process a module, evaluating all constant expressions.

        Returns a list of ConstEvalError instances for any failures.
        """
        self.errors = []

        # First pass: collect all constant values
        self._collect_constants(module)

        # Second pass: evaluate static_assert conditions
        for item in module.items:
            if isinstance(item, rast.StaticAssert):
                self._evaluate_static_assert(item)

        # Third pass: evaluate array sizes in types, wherever they appear
        self._walk(module.items)

        return self.errors

    def _collect_constants(self, module: rast.Module) -> None:
        """Collect constant definitions."""
        for item in module.items:
            if isinstance(item, rast.ConstDef):
                if item.value:
                    try:
                        # Try to evaluate the constant's value
                        value = self.evaluator.evaluate(item.value)
                        self.evaluator.add_constant(item.name, value)
                    except ConstEvalError:
                        # If we can't evaluate, it might be a complex expression
                        # that depends on other constants - skip for now
                        pass

    def _evaluate_static_assert(self, item: rast.StaticAssert) -> None:
        """Evaluate a static_assert condition."""
        try:
            result = self.evaluator.evaluate(item.condition)
            if result == 0:
                # Assertion failed
                if item.message:
                    self.errors.append(ConstEvalError(
                        f"static_assert failed: {item.message}"
                    ))
                else:
                    self.errors.append(ConstEvalError(
                        "static_assert failed"
                    ))
        except ConstEvalError as e:
            self.errors.append(ConstEvalError(
                f"Cannot evaluate static_assert condition: {e}"
            ))

    def _walk(self, node) -> None:
        """Fold every array size reachable from `node`, through all AST fields.

        A per-kind walker visited a Call's args but not its type_args, and
        skipped struct literals, method calls, grouping, `sizeof`, lambdas,
        tuple types and enum payloads, so `first<*[N]i8>(@x)` kept
        `size = Ident('N')` and crashed the emitter (AGAST #2857).  Walking
        every field means a new node kind can't hide an array type from this
        pass, and the emitter can take every size as an int.
        """
        if node is None:
            return
        if isinstance(node, list) or isinstance(node, tuple):
            for item in node:
                self._walk(item)
            return
        if not isinstance(node, rast.Node):
            return
        if isinstance(node, rast.ArrayType):
            self._fold_size(node)
        for name in _child_fields(type(node)):
            self._walk(getattr(node, name))

    def _fold_size(self, type_node: rast.ArrayType) -> None:
        """Replace an array type's size expression with its int value."""
        if isinstance(type_node.size, int):
            return
        try:
            size = self.evaluator.evaluate(type_node.size)
            if size < 0:
                self.errors.append(ConstEvalError(
                    f"Array size cannot be negative: {size}"
                ))
                size = 0  # Use 0 to allow compilation to continue
            type_node.size = size
        except ConstEvalError as e:
            self.errors.append(e)
            type_node.size = 0  # Use 0 to allow compilation to continue


@functools.cache
def _child_fields(cls) -> tuple:
    """The dataclass fields of an AST node class that can hold child nodes."""
    return tuple(f.name for f in dataclasses.fields(cls) if f.name != "span")


def evaluate_array_sizes(module: rast.Module) -> list:
    """Evaluate all constant expressions in array sizes.

    Args:
        module: The AST module to process

    Returns:
        List of ConstEvalError instances for any failures
    """
    pass_instance = ConstEvalPass()
    return pass_instance.process_module(module)
