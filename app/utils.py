import ast
import operator as op

OPERADORES = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.Pow: op.pow,
    ast.UAdd: op.pos,
    ast.USub: op.neg
}


def letra_a_indice(letra):
    """Convierte una letra de columna (p.ej., 'A') a un índice de columna basado en 0 (p.ej., 0)."""
    indice = 0
    for caracter in letra.upper():
        if 'A' <= caracter <= 'Z':
            indice = indice * 26 + (ord(caracter) - ord('A') + 1)
    return indice - 1


def celda_a_indices(celda):
    """Convierte una referencia de celda (p.ej., 'A1') a índices de fila y columna (p.ej., (0, 0))."""
    columna_letras = ''.join(filter(str.isalpha, celda)).upper()
    fila_numeros = ''.join(filter(str.isdigit, celda))

    if not columna_letras or not fila_numeros:
        raise ValueError(f"Referencia de celda inválida: {celda}")

    columna = letra_a_indice(columna_letras)
    fila = int(fila_numeros) - 1
    return fila, columna


def evaluar_expresion(expresion):
    """Evalúa una expresión matemática dada como string. Si la expresión comienza con '=', se evalúa,
    en caso contrario, se devuelve tal cual."""
    if not expresion.startswith('='):
        return expresion

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
            elif isinstance(node, (ast.Num, ast.Constant)):
                return node.n if isinstance(node, ast.Num) else node.value
            else:
                raise TypeError(f"Tipo de nodo no soportado: {type(node)}")

        return eval_ast(tree.body)

    except (TypeError, ValueError, SyntaxError) as e:
        print(f"Error al evaluar la expresión: {e}")
        return f"={expresion}"
