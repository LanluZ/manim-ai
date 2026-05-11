from __future__ import annotations

import ast


class _FastManimTransformer(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        func_name = _call_name(node.func)

        if func_name in {"MathTex", "Tex"}:
            node.func = ast.Name(id="Text", ctx=ast.Load())
            node.args = [_plain_text_arg(node.args[0])] if node.args else [ast.Constant(value="label")]

        if func_name == "Axes":
            _disable_axis_numbers(node)

        if func_name == "wait":
            node.args = [ast.Constant(value=0.1)]
            node.keywords = []

        for keyword in node.keywords:
            if keyword.arg == "run_time":
                keyword.value = ast.Constant(value=0.25)

        return node


def optimize_manim_code_for_speed(code: str) -> str:
    """Make generated Manim code cheaper to render in preview/evaluation mode."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    tree = _FastManimTransformer().visit(tree)
    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree) + "\n"
    except Exception:
        return code


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _plain_text_arg(node: ast.AST) -> ast.expr:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = (
            node.value.replace("\\", "")
            .replace("{", "")
            .replace("}", "")
            .replace("^", "")
            .replace("_", "")
        )
        return ast.Constant(value=text[:32] or "label")
    return ast.Constant(value="label")


def _disable_axis_numbers(node: ast.Call) -> None:
    for keyword in node.keywords:
        if keyword.arg != "axis_config" or not isinstance(keyword.value, ast.Dict):
            continue
        for key, value in zip(keyword.value.keys, keyword.value.values, strict=False):
            if isinstance(key, ast.Constant) and key.value == "include_numbers":
                if isinstance(value, ast.Constant):
                    value.value = False
                else:
                    keyword.value.values[keyword.value.values.index(value)] = ast.Constant(value=False)
                return
        keyword.value.keys.append(ast.Constant(value="include_numbers"))
        keyword.value.values.append(ast.Constant(value=False))
