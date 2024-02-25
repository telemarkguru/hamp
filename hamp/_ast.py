import inspect
import ast
from tokenize import generate_tokens, untokenize, INDENT
from io import StringIO


def _dedent(s):
    """Dedent python code string."""
    result = [t[:2] for t in generate_tokens(StringIO(s).readline)]
    if result[0][0] == INDENT:
        result[0] = (INDENT, "")
    return untokenize(result)


def parse_func(func):
    """Parse function source and return AST"""
    source = _dedent(inspect.getsource(func))
    empty_lines = [
        i for i, line in enumerate(source.splitlines()) if not line.strip()
    ]
    tree = compile(
        source,
        mode="exec",
        filename="<unknown>",
        dont_inherit=True,
        flags=ast.PyCF_ONLY_AST,
    )
    return tree, empty_lines
