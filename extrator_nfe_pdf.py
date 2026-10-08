import re
import json
from leitor import ler_pdf

def extrair_chave_acesso(texto):
    padrao = r"CHAVE DE ACESSO\s*([0-9 \t]+)"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:
        return None

    chave = re.sub(r"\D", "", resultado.group(1))

    if len(chave) != 44:
        print(
            f"Chave encontrada, mas possui "
            f"{len(chave)} dígitos. Esperado: 44."
        )
        return None

    return chave

def extrair_numero_nota(texto):
    padrao = r"NF-e\s*N[º°.]?\s*\.?\s*([\d.]+)"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:
        return None

    numero = re.sub(
        r"\D",
        "",
        resultado.group(1)
    )

    return numero

def extrair_bloco(texto, inicio, fim):
    padrao = rf"{inicio}(.*?){fim}"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE | re.DOTALL
    )

    if not resultado:
        return None

    return resultado.group(1).strip()

def extrair_bloco_emitente(texto):
    return extrair_bloco(
        texto,
        r"IDENTIFICAÇÃO DO EMITENTE",
        r"DESTINATÁRIO / REMETENTE"
    )

def extrair_cnpj_emitente(texto):
    bloco = extrair_bloco_emitente(texto)

    if not bloco:
        return None

    padrao = r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"

    resultado = re.search(
        padrao,
        bloco
    )

    if not resultado:
        return None

    return resultado.group()

def extrair_razao_emitente(texto):
    bloco = extrair_bloco_emitente(texto)

    if not bloco:
        return None

    linhas = bloco.splitlines()

    if not linhas:
        return None

    return linhas[0].strip()

def extrair_bloco_destinatario(texto):
    return extrair_bloco(
        texto,
        r"DESTINATÁRIO / REMETENTE",
        r"CÁLCULO DO IMPOSTO"
    )

def extrair_documento_destinatario(texto):
    bloco = extrair_bloco_destinatario(texto)

    if not bloco:
        return None

    padrao = r"CNPJ\s*/\s*CPF\s*([\d./-]+)"

    resultado = re.search(
        padrao,
        bloco,
        re.IGNORECASE
    )

    if not resultado:
        return None

    return resultado.group(1)

def extrair_razao_destinatario(texto):
    bloco = extrair_bloco_destinatario(texto)

    if not bloco:
        return None

    padrao = r"NOME\s*/\s*RAZÃO SOCIAL\s*(.+)"

    resultado = re.search(
        padrao,
        bloco,
        re.IGNORECASE
    )

    if not resultado:
        return None

    return resultado.group(1).strip()

def extrair_data_emissao(texto):
    padrao = r"DATA DA EMISSÃO\s*(\d{2}/\d{2}/\d{4})"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:
        return None

    return resultado.group(1)

def extrair_valor_total(texto):
    padrao = r"V\.\s*TOTAL DA NOTA\s*([\d.,]+)"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:
        return None

    return resultado.group(1)

def extrair_data_vencimento(texto):
    padrao = r"(?:VENCIMENTO|DT\.\s*VENC\.?)\s*(\d{2}/\d{2}/\d{4})"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:
        return None

    return resultado.group(1)

def extrair_nfe_pdf(texto):
    return {
        "tipo": "nfe",

        "numero_nota": extrair_numero_nota(texto),

        "chave_acesso": extrair_chave_acesso(texto),

        "emitente": {
            "cnpj": extrair_cnpj_emitente(texto),
            "razao_social": extrair_razao_emitente(texto)
        },

        "destinatario": {
            "cnpj_cpf": extrair_documento_destinatario(texto),
            "razao_social": extrair_razao_destinatario(texto)
        },

        "data_emissao": extrair_data_emissao(texto),

        "data_vencimento": extrair_data_vencimento(texto),

        "valor_total": extrair_valor_total(texto)
    }