import re
from extratores.campos_layout import campo_abaixo, documento_unico, DINHEIRO, DATA

def extrair_chave_acesso(texto):
    chaves = set(re.sub(r"\s", "", m.group()) for m in re.finditer(r"(?<!\d)(?:\d{4}[ \t]+){10}\d{4}(?!\d)|(?<!\d)\d{44}(?!\d)", texto))
    if len(chaves) == 1 and re.search("CHAVE DE ACESSO", texto, re.I):
        return next(iter(chaves))
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
        return None

    return chave

def extrair_numero_nota(texto):
    numeros = set(re.sub(r"\D", "", m) for m in re.findall(r"N[º°.]\s*([\d.]+)", texto, re.I))
    if len(numeros) == 1:
        return next(iter(numeros))
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
        r"DESTINAT[ÁA]RIO\s*/\s*REMETENTE"
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
    recibo = re.search(r"Recebemos de\s+(.+?),\s*os produtos", texto, re.I)
    if recibo:
        return recibo.group(1).strip()
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
        r"DESTINAT[ÁA]RIO\s*/\s*REMETENTE",
        r"CÁLCULO DO IMPOSTO"
    )

def extrair_documento_destinatario(texto):
    bloco = extrair_bloco_destinatario(texto)

    if not bloco:
        return None

    documento = documento_unico(bloco)
    if documento:
        return documento
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

    tabular = campo_abaixo(bloco, r"NOME\s*/\s*RAZ[ÃA]O SOCIAL", r"\S(?:.*?\S)?(?= {2,}|$)")
    if tabular:
        return tabular
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
    tabular = campo_abaixo(texto, r"DATA D[AE] EMISS[ÃA]O", DATA)
    if tabular:
        return tabular
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
    tabular = campo_abaixo(texto, r"(?:VALOR|V\.)\s*TOTAL DA NOTA", DINHEIRO)
    if tabular:
        return tabular.replace("R$", "").strip()
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
        "vencimentos": re.findall(r"(?:VENCIMENTO|DT\.\s*VENC\.?)\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE),

        "valor_total": extrair_valor_total(texto)
    }