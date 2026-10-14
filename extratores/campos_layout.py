"""Campos tabulares em texto de PDF com posições de coluna preservadas."""
import re

DINHEIRO = r'(?:R\$[ \t]*)?\d[\d.]*,\d{2}(?!\d)'
DOCUMENTO = r'(?<!\d)(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})(?!\d)'
DATA = r'\d{2}/\d{2}/\d{4}'


def campo_abaixo(texto, rotulo, padrao, max_linhas=3):
    linhas = texto.splitlines()
    encontrados = []
    for i, linha in enumerate(linhas):
        titulo = re.search(rotulo, linha, re.I)
        if not titulo:
            continue
        proxima = re.search(r' {2,}(?=\S)', linha[titulo.end():])
        fim = titulo.end() + proxima.end() if proxima else float('inf')
        inicio = max(0, titulo.start() - 3)
        # Campo inline não deve capturar um valor da linha seguinte.
        if re.search(padrao, linha[titulo.end():int(fim) if fim != float('inf') else None]):
            continue
        for abaixo in linhas[i+1:i+1+max_linhas]:
            if not abaixo.strip():
                continue
            cabecalhos = re.split(r' {2,}', linha.strip())
            celulas = re.split(r' {2,}', abaixo.strip())
            if len(cabecalhos) > 1 and len(cabecalhos) == len(celulas):
                indices = [j for j, c in enumerate(cabecalhos) if re.search(rotulo, c, re.I)]
                if len(indices) == 1:
                    valor = re.match(padrao, celulas[indices[0]])
                    if valor:
                        encontrados.append(valor.group().strip())
                        break
            valores = [m.group().strip() for m in re.finditer(padrao, abaixo)
                       if inicio <= m.start() < fim and not abaixo[inicio:m.start()].strip()]
            if len(valores) == 1:
                encontrados.append(valores[0])
            # Só a primeira linha de valores do campo; não percorre outras seções.
            break
    unicos = set(encontrados)
    return encontrados[0] if len(unicos) == 1 else None


def documento_unico(bloco):
    encontrados = set(re.findall(DOCUMENTO, bloco or ''))
    return next(iter(encontrados)) if len(encontrados) == 1 else None
