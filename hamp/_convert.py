"""Convert python code for code generation"""

from ._ast import parse_func
import ast
from typing import Tuple, Any, Dict, Callable
from ._module import _Module, _DataMember


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

    def __init__(self, var: str, module: _Module):
        super().__init__()
        self.var = var
        self.module = module
        self.in_attr = False
        self.hw_types = 0

    def visit_If(self, node):
        self.hw_types = 0
        self.visit(node.test)
        hw_expr = self.hw_types > 0
        self.generic_visit(node)
        if hw_expr:
            n = [_with_node(self.var, "if_stmt", node.body, node.test)]
            if node.orelse:
                x = node.orelse
                if x and getattr(x[0], "_hamp_with", "") == "if_stmt":
                    # Convert if to elif:
                    x[0].items[0].context_expr.func.attr = "elif_stmt"
                    n += x
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

    def visit_Attribute(self, node):
        """Figure out if top level attribute access is to a hardware type"""
        if self.in_attr:
            self.generic_visit(node)
            return node
        self.in_attr = True
        self.generic_visit(node)
        if isinstance(node.value, ast.Name):
            if (
                node.value.id == self.var
                and node.attr in self.module
                and isinstance(self.module[node.attr], _DataMember)
            ):
                self.hw_types += 1
        self.in_attr = False
        return node


def _replace(tree: ast.AST, var: str, module: _Module):
    tree = ast.fix_missing_locations(_Replacer(var, module).visit(tree))
    return tree


def _cell_contentes(cell):
    try:
        return cell.cell_contents
    except:
        return None

def _closure_locals(func: Callable) -> Dict[str, Any]:
    """Extract function closure variables"""
    if c := func.__closure__:
        return {
            var: _cell_contentes(cell)
            for var, cell in zip(func.__code__.co_freevars, c)
        }
    return {}


def convert(func: Callable, module: _Module) -> Tuple[Callable, str]:
    """Convert function to code generator, and return converted function

    If statements with hardware expressions are replaced with
    if_stmt/elif_stmt/else_stmt with-statements.

    and/or/not eppressions are replaced with and_expr/or_expr/no_expr calls.
    """
    tree = parse_func(func)
    var = func.__code__.co_varnames[0]
    dtree = _replace(tree, var, module)
    srccode = ast.unparse(dtree)
    # Remove @xx.code decorator:
    start = srccode.find("def ")
    srccode = srccode[start:]
    syms: Dict[str, Any] = {**func.__globals__, **_closure_locals(func)}
    exec(srccode, syms)
    return syms[func.__name__], srccode
