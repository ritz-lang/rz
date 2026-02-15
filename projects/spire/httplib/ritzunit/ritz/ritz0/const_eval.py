"""
Constant Expression Evaluator for Ritz

Evaluates compile-time constant expressions for use in:
- Array size declarations: [SIZE]u8, [1 << 9]u32
- static_assert conditions (future)
- const fn evaluation (future)
"""

from typing import Dict, Any, Optional, Union
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
    - Unary operations: -, ~
    - Parenthesized expressions
    """

    def __init__(self, constants: Optional[Dict[str, int]] = None):
        """Initialize with known constants.

        Args:
            constants: Dict mapping constant names to their values
        """
        self.constants: Dict[str, int] = constants or {}

    def add_constant(self, name: str, value: int) -> None:
        """Register a constant for use in expressions."""
        self.constants[name] = value

    def evaluate(self, expr: rast.Expr) -> int:
        """Evaluate a constant expression to an integer.

        Args:
            expr: The AST expression to evaluate

        Returns:
            The computed integer value

        Raises:
            ConstEvalError: If the expression cannot be evaluated at compile time
        """
        if isinstance(expr, rast.IntLit):
            return expr.value

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
                return left // right
            elif op == '%':
                if right == 0:
                    raise ConstEvalError("Modulo by zero in constant expression")
                return left % right
            elif op == '<<':
                if right < 0:
                    raise ConstEvalError("Negative shift amount in constant expression")
                return left << right
            elif op == '>>':
                if right < 0:
                    raise ConstEvalError("Negative shift amount in constant expression")
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

        # Third pass: evaluate array sizes in types
        for item in module.items:
            self._process_item(item)

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

    def _process_item(self, item) -> None:
        """Process an item, evaluating array sizes in its types."""
        if isinstance(item, rast.FnDef):
            self._process_function(item)
        elif isinstance(item, rast.StructDef):
            self._process_struct(item)
        elif isinstance(item, rast.VarDef):
            self._process_type(item.type)
        elif isinstance(item, rast.ConstDef):
            if item.type:
                self._process_type(item.type)
        elif isinstance(item, rast.TypeAlias):
            self._process_type(item.target)
        elif isinstance(item, rast.ImplBlock):
            for method in item.methods:
                self._process_function(method)

    def _process_function(self, fn: rast.FnDef) -> None:
        """Process a function, evaluating array sizes in parameters and body."""
        # Process parameter types
        for param in fn.params:
            self._process_type(param.type)

        # Process return type
        if fn.ret_type:
            self._process_type(fn.ret_type)

        # Process function body
        if fn.body:
            self._process_block(fn.body)

    def _process_struct(self, struct: rast.StructDef) -> None:
        """Process a struct's field types."""
        for _name, field_type in struct.fields:
            self._process_type(field_type)

    def _process_block(self, block: rast.Block) -> None:
        """Process a block, evaluating array sizes in variable declarations."""
        for stmt in block.stmts:
            self._process_stmt(stmt)

    def _process_stmt(self, stmt) -> None:
        """Process a statement."""
        if isinstance(stmt, (rast.LetStmt, rast.VarStmt)):
            if stmt.type:
                self._process_type(stmt.type)
            if stmt.value:
                self._process_expr(stmt.value)
        elif isinstance(stmt, rast.If):
            # If is an expression in Ritz
            self._process_expr(stmt)
        elif isinstance(stmt, rast.WhileStmt):
            self._process_expr(stmt.cond)
            self._process_block(stmt.body)
        elif isinstance(stmt, rast.ForStmt):
            self._process_expr(stmt.iter)
            self._process_block(stmt.body)
        elif isinstance(stmt, rast.ReturnStmt):
            if stmt.value:
                self._process_expr(stmt.value)
        elif isinstance(stmt, rast.ExprStmt):
            self._process_expr(stmt.expr)
        elif isinstance(stmt, rast.Block):
            self._process_block(stmt)
        elif isinstance(stmt, rast.Match):
            # Match is an expression in Ritz
            self._process_expr(stmt)

    def _process_expr(self, expr) -> None:
        """Process an expression, looking for array types in casts."""
        if isinstance(expr, rast.Cast):
            self._process_type(expr.target)
            self._process_expr(expr.expr)
        elif isinstance(expr, rast.BinOp):
            self._process_expr(expr.left)
            self._process_expr(expr.right)
        elif isinstance(expr, rast.UnaryOp):
            self._process_expr(expr.operand)
        elif isinstance(expr, rast.Call):
            for arg in expr.args:
                self._process_expr(arg)
        elif isinstance(expr, rast.Index):
            self._process_expr(expr.expr)
            self._process_expr(expr.index)
        elif isinstance(expr, rast.Field):
            self._process_expr(expr.expr)
        elif isinstance(expr, rast.ArrayLit):
            for elem in expr.elements:
                self._process_expr(elem)
        elif isinstance(expr, rast.ArrayFill):
            self._process_expr(expr.value)
        elif isinstance(expr, rast.If):
            self._process_expr(expr.cond)
            self._process_block(expr.then_block)
            if expr.else_block:
                if isinstance(expr.else_block, rast.Block):
                    self._process_block(expr.else_block)
                else:
                    self._process_expr(expr.else_block)
        elif isinstance(expr, rast.Match):
            self._process_expr(expr.value)
            for arm in expr.arms:
                if arm.guard:
                    self._process_expr(arm.guard)
                self._process_block(arm.body)

    def _process_type(self, type_node) -> None:
        """Process a type, evaluating array size if needed."""
        if type_node is None:
            return

        if isinstance(type_node, rast.ArrayType):
            # If size is already an int, nothing to do
            if isinstance(type_node.size, int):
                self._process_type(type_node.inner)
                return

            # Evaluate the size expression
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

            self._process_type(type_node.inner)

        elif isinstance(type_node, rast.PtrType):
            self._process_type(type_node.inner)
        elif isinstance(type_node, rast.RefType):
            self._process_type(type_node.inner)
        elif isinstance(type_node, rast.SliceType):
            self._process_type(type_node.inner)
        elif isinstance(type_node, rast.NamedType):
            for arg in type_node.args:
                self._process_type(arg)
        elif isinstance(type_node, rast.FnType):
            for param in type_node.params:
                self._process_type(param)
            if type_node.ret:
                self._process_type(type_node.ret)
        elif isinstance(type_node, rast.UnionType):
            for variant in type_node.variants:
                self._process_type(variant)


def evaluate_array_sizes(module: rast.Module) -> list:
    """Evaluate all constant expressions in array sizes.

    Args:
        module: The AST module to process

    Returns:
        List of ConstEvalError instances for any failures
    """
    pass_instance = ConstEvalPass()
    return pass_instance.process_module(module)
