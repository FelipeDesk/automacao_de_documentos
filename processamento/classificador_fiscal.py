import re
import unicodedata

def limpar_texto(texto):
    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = re.sub(r"\s+", " ", texto)

    return texto.upper()


def identificar_tipo_pdf(texto):
    if not texto:
        return "desconhecido"

    texto = limpar_texto(texto)

    indicadores_nfse = [
        "NOTA FISCAL DE SERVICOS ELETRONICA",
        "NOTA FISCAL DE SERVICO ELETRONICA",
        "NFS-E",
        "NFSE"
    ]

    for indicador in indicadores_nfse:
        if indicador in texto:
            return "nfse"

    indicadores_nfe = [
        "DANFE",
        "CHAVE DE ACESSO",
        "NOTA FISCAL ELETRONICA",
        "DESTINATARIO / REMETENTE"
    ]

    encontrados = sum(
        indicador in texto
        for indicador in indicadores_nfe
    )

    if "DANFE" in texto and encontrados >= 2:
        return "nfe"

    return "desconhecido"