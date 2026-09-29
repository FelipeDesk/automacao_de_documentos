import re

def extrair_cpf(texto):
    padrao_cpf = r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}'

    cpf = re.search(padrao_cpf, texto)

    if cpf:
        return cpf.group()

    return None