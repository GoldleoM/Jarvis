import ast
import math
import operator
import re

from skills.spoken_numbers import quantity


def expression(text):
    text = text.casefold().strip().rstrip("?!").strip()
    text = re.sub(r"^(?:(?:please|can you|could you|would you)\s+)+", "", text)
    explicit = text.startswith(("calculate ", "solve "))
    text = re.sub(r"^(?:what(?: is|'s)|how much is|calculate|solve(?: this math)?)\s+", "", text)
    for verb, join, op in (("multiply", "by", "*"), ("divide", "by", "/"), ("subtract", "from", "-"),
                           ("add", "and", "+"), ("(?:the )?sum of", "and", "+")):
        operands = re.fullmatch(rf"{verb} (.+?) {join} (.+)", text)
        if operands:
            a, b = operands.groups()
            text = f"({b})-({a})" if verb == "subtract" else f"({a}){op}({b})"
            break
    for words, op in (("percent of", "/100*"), ("% of", "/100*"), ("to the power of", "**"),
                      ("multiplied by", "*"), ("divided by", "/"), ("times", "*"), ("plus", "+"), ("minus", "-")):
        text = text.replace(words, op)

    def number(match):
        phrase = match.group().strip().replace("-", " ")
        value = quantity(phrase)
        return str(value) if value is not None else match.group()

    text = re.sub(r"[a-z]+(?:[ -][a-z]+)*", number, text).strip()
    if len(text) <= 160 and re.fullmatch(r"[\d\s.+*/%()-]+", text) and (explicit or re.search(r"[+*/%-]", text)):
        return text
    return None


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def _value(node):
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        arg = _value(node.operand)
        value = -arg if isinstance(node.op, ast.USub) else arg
    elif isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _value(node.left), _value(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        value = _OPS[type(node.op)](left, right)
    else:
        raise ValueError("unsupported operation")
    if isinstance(value, complex) or abs(value) > 10**100 or not math.isfinite(value):
        raise ValueError("result out of range")
    return value


def calculate(text):
    expr = expression(text)
    if expr is None:
        return "Which arithmetic expression would you like me to calculate?"
    try:
        value = _value(ast.parse(expr, mode="eval").body)
        if isinstance(value, float):
            value = int(value) if value.is_integer() else round(value, 2)
        return f"The answer is {value}."
    except ZeroDivisionError:
        return "Division by zero is undefined."
    except (ArithmeticError, SyntaxError, ValueError):
        return "I couldn't evaluate that arithmetic expression."
