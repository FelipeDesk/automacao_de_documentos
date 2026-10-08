import re


def identificar_tipo_pdf(texto):
    if not texto:
        return "desconhecido"

    texto = re.sub(r"\s+", " ", texto).upper()

    indicadores_nfe = [
        "DANFE",
        "CHAVE DE ACESSO",
        "NOTA FISCAL ELETRÔNICA",
        "DESTINATÁRIO / REMETENTE"
    ]

    encontrados = 0

    for indicador in indicadores_nfe:
        if indicador in texto:
            encontrados += 1

    if encontrados >= 2 and "DANFE" in texto:
        return "nfe"

    return "desconhecido"