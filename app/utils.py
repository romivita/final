def letra_a_indice(letra):
    """Convierte una letra de columna a un índice numérico (A=1, B=2, ...)"""
    return ord(letra.upper()) - ord('A') + 1


def indice_a_letra(indice):
    """Convierte un índice numérico a una letra de columna (1=A, 2=B, ...)"""
    return chr(indice + ord('A') - 1)


def celda_a_indices(celda):
    """Convierte una referencia de celda (p.ej., 'A1') a índices de fila y columna (p.ej., (1, 1))"""
    columna_letras = ''.join(filter(str.isalpha, celda))
    fila_numeros = ''.join(filter(str.isdigit, celda))
    columna = letra_a_indice(columna_letras)
    fila = int(fila_numeros)
    return fila, columna


def indices_a_celda(fila, columna):
    """Convierte índices de fila y columna a una referencia de celda (p.ej., (1, 1) a 'A1')"""
    letra_columna = indice_a_letra(columna)
    return f"{letra_columna}{fila}"
