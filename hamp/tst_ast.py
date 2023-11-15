from ._ast import parse_func
import ast


def func(m):
    for i in range(3):
        if m.x[i] <= 1:
            m.y[i] = 2
        else:
            m.y[i] = 3
    with open("foo", "w") as fh:
        fh.read()


class _IfReplacer(ast.NodeTransformer):
    """Replace if:s that uses hardware types with with-statements"""

    def visit_If(self, node):
        self.generic_visit(node)
        if hasattr(node.test, "__hamp_expr__") or True:
            n = [
                ast.With(
                    items=[
                        ast.withitem(
                            ast.Call(
                                ast.Name(id="_if", ctx=ast.Load()),
                                [node.test],
                                {},
                            )
                        ),
                    ],
                    body=node.body,
                ),
            ]
            if node.orelse:
                n.append(
                    ast.With(
                        items=[
                            ast.withitem(
                                ast.Call(
                                    ast.Name(id="_else", ctxt=ast.Load()),
                                    [],
                                    {},
                                )
                            ),
                        ],
                        body=node.orelse,
                    ),
                )
            return n
        else:
            return node

    def visit_Compare(self, node):
        self.generic_visit(node)
        return node


def _replace_ifs(tree):
    tree = ast.fix_missing_locations(_IfReplacer().visit(tree))
    return tree


t = parse_func(func)
print(ast.dump(t, indent="    "))
t2 = _replace_ifs(t)
print(ast.unparse(t2))
