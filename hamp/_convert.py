"""Convert python code for code generation"""

from ._ast import parse_func
import ast
from typing import List, Tuple, Any, Dict


def _member_func_call(var: str, memb: str, params: Tuple[Any, ...]):
    """Create and return member function call ast node"""
    node = ast.Call(
        func=ast.Attribute(
            value=ast.Name(id=var, ctx=ast.Load()),
            attr=memb,
            ctx=ast.Load(),
        ),
        args=list(params),
        keywords=[],
    )
    return node


def _with_node(builder: str, attr: str, body: ast.AST, *params: Any):
    """Create and return with statment node"""
    node = ast.With(
        items=[
            ast.withitem(
                context_expr=_member_func_call(builder, attr, params)
            ),
        ],
        body=body,
    )
    setattr(node, "_hamp_with", attr)
    return node


class _Replacer(ast.NodeTransformer):
    """Replace if:s that uses hardware types with with-statements
    and logical expressions (and/or/not) with function calls
    """

    def __init__(self, var: str):
        super().__init__()
        self.var = var

    def visit_If(self, node):
        self.generic_visit(node)
        if hasattr(node.test, "__hamp_expr__") or True:
            n = [_with_node(self.var, "if_stmt", node.body, node.test)]
            if node.orelse:
                l = node.orelse
                if l and getattr(l[0], "_hamp_with", "") == "if_stmt":
                    # Convert if to elif:
                    l[0].items[0].context_expr.func.attr = "elif_stmt"
                    n += l
                else:
                    n.append(_with_node(self.var, "else_stmt", node.orelse))
            return n
        else:
            return node

    def visit_BoolOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.And):
            member = "and_expr"
        else:
            member = "or_expr"
        return _member_func_call(self.var, member, node.values)

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if isinstance(node.op, ast.Not):
            return _member_func_call(self.var, "not_expr", [node.operand])
        return node


def _replace(tree: ast.AST, var: str):
    tree = ast.fix_missing_locations(_Replacer(var).visit(tree))
    return tree


def convert(func: function):
    """Convert function to code generator, and return converted function

    If statements with hardware expressions are replaced with
    if_stmt/elif_stmt/else_stmt calls

    and/or/not eppressions are replaced with and_expr/or_expr/no_expr calls.
    """
    tree = parse_func(func)
    var = func.__code__.co_varnames[0]
    dtree = _replace(tree, var)
    srccode = ast.unparse(dtree)
    syms: Dict[str, Any] = {}
    exec(srccode, syms)
    return syms[func.__name__]


if __name__ == "__main__":

    def func(b):
        for i in range(3):
            if b.x[i] <= 1 and b.x[i] > -1 or b.x[i] & 1:
                b.y[i] = 2
            elif not (b.x[i] > 2):
                b.y[i] = 8
            else:
                b.y[i] = 3

    t = parse_func(func)
    t2 = _replace(t, func.__code__.co_varnames[0])
    print(ast.dump(t2, indent="    "))
    print(ast.unparse(t2))
    c = convert(func)
    from contextlib import contextmanager

    class m:
        @contextmanager
        def if_stmt(self, x):
            try:
                yield None
            finally:
                pass

        @contextmanager
        def elif_stmt(self, y):
            try:
                yield None
            finally:
                pass

        @contextmanager
        def else_stmt(self):
            try:
                yield None
            finally:
                pass

        def and_expr(self, *x):
            return list(x)

        def or_expr(self, *x):
            pass

        def not_expr(self, x):
            pass

        def __init__(self):
            self.x = [3, 4, 1]
            self.y = [5, 6, 2]

    c(m())
