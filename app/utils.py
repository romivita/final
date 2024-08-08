import ast
import operator as op


def letra_a_indice(letra):
    """Convierte una letra de columna (p.ej., 'A') a un indice de columna basado en 0 (p.ej., 0)"""
    indice = 0
    for caracter in letra:
        if 'A' <= caracter <= 'Z':
            indice = indice * 26 + (ord(caracter) - ord('A'))
    return indice


def celda_a_indices(celda):
    """Convierte una referencia de celda (p.ej., 'A1') a indices de fila y columna (p.ej., (0, 0))"""
    columna_letras = ''.join(filter(str.isalpha, celda)).upper()
    fila_numeros = ''.join(filter(str.isdigit, celda))
    columna = letra_a_indice(columna_letras)
    fila = int(fila_numeros) - 1
    return fila, columna


OPERADORES = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Mod: op.mod, ast.Pow: op.pow,
              ast.UAdd: op.pos, ast.USub: op.neg, }


def evaluar_expresion(expresion):
    if expresion.startswith('='):
        expresion = expresion[1:]

        try:
            tree = ast.parse(expresion, mode='eval')

            def eval_ast(node):
                if isinstance(node, ast.Expression):
                    return eval_ast(node.body)
                elif isinstance(node, ast.BinOp):
                    left = eval_ast(node.left)
                    right = eval_ast(node.right)
                    return OPERADORES[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    operand = eval_ast(node.operand)
                    return OPERADORES[type(node.op)](operand)
                elif isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.Constant):
                    return node.value
                else:
                    raise TypeError(f"Tipo de nodo no soportado: {type(node)}")

            return eval_ast(tree.body)
        except Exception as e:
            print(f"Error al evaluar la expresion: {e}")
            return f"={expresion}"
    else:
        return expresion
