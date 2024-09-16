import ast
import logging
import operator as op
import re

OPERADORES = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Mod: op.mod, ast.Pow: op.pow,
              ast.UAdd: op.pos, ast.USub: op.neg}


def letra_a_indice(letra):
    letra = letra.upper()
    if not letra.isalpha():
        raise ValueError(f"Letra invalida: {letra}")
    return sum((ord(c) - ord('A') + 1) * (26 ** i) for i, c in enumerate(reversed(letra))) - 1


def celda_a_indices(celda):
    match = re.fullmatch(r"([A-Z]+)(\d+)", celda.upper())
    if not match:
        raise ValueError(f"Referencia de celda invalida: {celda}")

    columna_letras, fila_numeros = match.groups()
    columna = letra_a_indice(columna_letras)
    fila = int(fila_numeros) - 1
    return fila, columna


def eliminar_ceros_a_la_izquierda(expresion):
    return re.sub(r'\b0+(\d)', r'\1', expresion)


def evaluar_expresion(expresion):
    if not expresion.startswith('='):
        return expresion

    expresion = eliminar_ceros_a_la_izquierda(expresion[1:])

    try:
        tree = ast.parse(expresion, mode='eval')

        def eval_ast(node):
            if isinstance(node, ast.Expression):
                return eval_ast(node.body)
            elif isinstance(node, ast.BinOp):
                left = eval_ast(node.left)
                right = eval_ast(node.right)

                if isinstance(node.op, ast.Div) and right == 0:
                    raise ZeroDivisionError("Intento de división por cero.")

                return OPERADORES[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = eval_ast(node.operand)
                return OPERADORES[type(node.op)](operand)
            elif isinstance(node, (ast.Constant, ast.Num)):
                return node.n if isinstance(node, ast.Num) else node.value
            else:
                raise TypeError(f"Tipo de nodo no soportado: {type(node)}")

        return eval_ast(tree.body)

    except ZeroDivisionError as e:
        logging.error(f"Error: {e}")
        return "Error: División por cero."
    except (SyntaxError, TypeError, ValueError) as e:
        logging.error(f"Error de formato o sintaxis: {e}")
        return f"Error: ={expresion}"
