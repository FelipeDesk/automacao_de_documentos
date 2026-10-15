import re
from extratores.campos_layout import campo_abaixo, documento_unico, DINHEIRO, DATA

def extrair_chave_acesso(texto):
    chaves = set(re.sub(r"\s", "", m.group()) for m in re.finditer(r"(?<!\d)(?:\d{4}[ \t]+){10}\d{4}(?!\d)|(?<!\d)\d{44}(?!\d)", texto))
    if len(chaves) == 1 and re.search("CHAVE DE ACESSO", texto, re.I):
        return next(iter(chaves))
    padrao = r"CHAVE DE ACESSO\s*:?\s*([0-9 \t]+)"

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
    cabecalho = re.split(r"NATUREZA DA OPERA[ÇC][ÃA]O|NOME\s*/?\s*RAZ[ÃA]O", texto, flags=re.I)[0]
    candidatos = set(re.sub(r"\D", "", m) for m in re.findall(r"\bN[º°a .]*\s*(\d{3}[. ]\d{3}[. ]\d{3})\b", cabecalho, re.I))
    if len(candidatos) == 1:
        return next(iter(candidatos))
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
    bloco = extrair_bloco(
        texto,
        r"IDENTIFICAÇÃO DO EMITENTE",
        r"DESTINAT[ÁA]RIO\s*/\s*REMETENTE"
    )
    if bloco:
        return bloco
    # DANFEs sem o título "Identificação do emitente": CNPJ antes do destinatário.
    partes = re.split(r"DESTINAT[ÁA]RIO\s*/\s*REMETENTE|NOME\s*/?\s*RAZ[ÃA]O SOCIAL", texto, maxsplit=1, flags=re.I)
    return partes[0] if len(partes) == 2 else None

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

    for linha in linhas:
        empresa = re.search(r'(.+?\b(?:S[/.]?\s*A\.?|LTDA))(?= {3,}|$)', linha.strip(), re.I)
        if empresa:
            return re.sub(r'\s+', ' ', empresa.group(1)).strip()
    return linhas[0].strip() if re.search(r'IDENTIFICAÇÃO DO EMITENTE', texto, re.I) else None

def extrair_bloco_destinatario(texto):
    return extrair_bloco(
        texto,
        r"DESTINAT[ÁA]RIO\s*/\s*REMETENTE",
        r"CÁLCULO DO IMPOSTO"
    ) or extrair_bloco(texto, r"(?=NOME\s*/?\s*RAZ[ÃA]O SOCIAL)",
                       r"(?:C[ÁA]LCULO DO IMPOSTO|BASE DE|VALOR DO ICMS)")

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

    tabular = campo_abaixo(bloco, r"NOME\s*/?\s*RAZ[ÃA]O SOCIAL", r"\S(?:.*?\S)?(?= {2,}|$)")
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
    tabular = campo_abaixo(texto, r"DATA\s*(?:D[AE] )?EMIS[S]?[ÃA]O", DATA)
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
    explicito = re.search(rf"VALOR TOTAL DA NOTA\s*:\s*({DINHEIRO})", texto, re.I)
    if explicito:
        return explicito.group(1)
    tabular = campo_abaixo(texto, r"(?:VALOR|V\.)\s*TOTAL DA NOTA", DINHEIRO)
    if tabular:
        return tabular.replace("R$", "").strip()
    padrao = r"(?:VALOR|V\.)\s*TOTAL DA NOTA\s*:?\s*([\d.,]+)"

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
