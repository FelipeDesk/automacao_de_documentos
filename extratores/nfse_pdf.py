import re
import unicodedata
from extratores.campos_layout import campo_abaixo, documento_unico, DINHEIRO, DATA

def buscar_campo(texto, padroes):
    for padrao in padroes:
        resultado = re.search(
            padrao,
            texto,
            re.IGNORECASE
        )

        if resultado:
            return resultado.group(1).strip()

    return None

def extrair_numero_nfse(texto):
    padroes = [
        r"N[ÚU]MERO (?:DA )?NFS-E\s*:?\s*(\d+)",
        r"N[ÚU]MERO DA NOTA\s*:?\s*(\d+)",
        r"NFS-E\s*N[º°.]?\s*(\d+)"
    ]

    return campo_abaixo(texto, r"N[ÚU]MERO (?:DA NOTA|(?:DA )?NFS-E)", r"\b\d+\b") or buscar_campo(texto, padroes)

def extrair_chave_nfse(texto):
    padrao = r"(?:CHAVE DE ACESSO DA NFS-E|IDENTIFICADOR NACIONAL)\s*:?\s*([\d \t]+)"

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE
    )

    if not resultado:
        return None

    chave = re.sub(r"\D", "", resultado.group(1))

    return chave if chave else None

def extrair_secao(texto, inicios, fins):
    inicio_padrao = "|".join(inicios)
    fim_padrao = "|".join(fins)

    padrao = (
        rf"(?:{inicio_padrao})"
        rf"(.*?)"
        rf"(?={fim_padrao}|\Z)"
    )

    resultado = re.search(
        padrao,
        texto,
        re.IGNORECASE | re.DOTALL
    )

    if not resultado:
        return None

    return resultado.group(1).strip()

def extrair_bloco_prestador(texto):
    return extrair_secao(
        texto,
        [
            r"DADOS DO PRESTADOR",
            r"PRESTADOR DE SERVIÇOS",
            r"PRESTADOR DO SERVIÇO",
            r"EMITENTE DA NFS-e"
        ],
        [
            r"DADOS DO TOMADOR",
            r"TOMADOR DE SERVIÇOS",
            r"TOMADOR DO SERVIÇO",
            r"INTERMEDI[ÁA]RIO DE SERVIÇOS",
            r"DISCRIMINAÇÃO D[OE]S? SERVIÇOS"
        ]
    )

def extrair_bloco_tomador(texto):
    return extrair_secao(
        texto,
        [
            r"DADOS DO TOMADOR",
            r"TOMADOR DE SERVIÇOS",
            r"TOMADOR DO SERVIÇO"
        ],
        [
            r"INTERMEDI[ÁA]RIO DE SERVIÇOS",
            r"DISCRIMINAÇÃO D[OE]S? SERVIÇOS",
            r"DESCRIÇÃO DOS SERVIÇOS",
            r"VALOR TOTAL DOS SERVIÇOS",
            r"VALORES"
        ]
    )

def extrair_documento_bloco(bloco):
    if not bloco:
        return None

    padroes = [
        r"CNPJ\s*/\s*CPF\s*:?\s*([\d./-]+)",
        r"CPF\s*/\s*CNPJ\s*:?\s*([\d./-]+)",
        r"CNPJ\s*:?\s*([\d./-]+)",
        r"CPF\s*:?\s*([\d./-]+)"
    ]

    return documento_unico(bloco) or buscar_campo(bloco, padroes)

def extrair_razao_social_bloco(bloco):
    if not bloco:
        return None

    padroes = [
        r"RAZÃO SOCIAL\s*:?[ \t]*([^\r\n]+)",
        r"NOME EMPRESARIAL\s*:?[ \t]*([^\r\n]+)",
        r"NOME\s*:?[ \t]*([^\r\n]+)"
    ]

    valor = buscar_campo(bloco, padroes)
    return re.split(r" {2,}", valor)[0].strip() if valor else None

def extrair_prestador(texto):
    bloco = extrair_bloco_prestador(texto)

    return {
        "cnpj": extrair_documento_bloco(bloco),
        "razao_social": extrair_razao_social_bloco(bloco)
    }


def extrair_tomador(texto):
    bloco = extrair_bloco_tomador(texto)

    return {
        "cnpj_cpf": extrair_documento_bloco(bloco),
        "razao_social": extrair_razao_social_bloco(bloco)
    }

def extrair_data_emissao_nfse(texto):
    padroes = [
        r"Emissão da NFS-e\s*(\d{2}/\d{2}/\d{4})",
        r"Data (?:e Hora )?de Emissão\s*:?\s*(\d{2}/\d{2}/\d{4})",
        r"Data da Emissão\s*:?\s*(\d{2}/\d{2}/\d{4})"
    ]

    return campo_abaixo(texto, r"Data (?:e Hora )?d[ae] Emissão", DATA) or buscar_campo(texto, padroes)

def extrair_valor_total_nfse(texto):
    tabela = campo_abaixo(texto, r"(?<!Unit\. )VALOR (?:TOTAL D[OE]S? SERVI[ÇC]OS?|SERVI[ÇC]O)\b", DINHEIRO)
    if tabela:
        return tabela.replace("R$", "").strip()
    padroes = [
        r"VALOR (?:TOTAL D[OE]S? SERVI[ÇC]OS?|DOS SERVI[ÇC]OS|DO SERVI[ÇC]O)\s*[:=]?\s*(?:R\$\s*)?([\d.,]+)",
        r"VALOR TOTAL DA NFS-E.*?VALOR DO SERVIÇO.*?\n\s*R\$\s*([\d.,]+)",
        r"VALOR TOTAL DOS SERVIÇOS\s*:?\s*(?:R\$\s*)?([\d.,]+)"
    ]

    for padrao in padroes:
        resultado = re.search(
            padrao,
            texto,
            re.IGNORECASE | re.DOTALL
        )

        if resultado:
            return resultado.group(1)

    return None

def extrair_nfse_pdf(texto):
    # Normaliza acentos preservando caixa e nomes para aceitar OCR sem diacriticos.
    texto = unicodedata.normalize("NFC", texto)
    for sem, com in [("SERVICOS", "SERVIÇOS"), ("SERVICO", "SERVIÇO"), ("RAZAO", "RAZÃO"), ("EMISSAO", "EMISSÃO"), ("LIQUIDO", "LÍQUIDO"), ("DISCRIMINACAO", "DISCRIMINAÇÃO")]:
        texto = re.sub(sem, com, texto, flags=re.IGNORECASE)
    totais = extrair_secao(
        texto, [r"(?m:^[ \t]*VALORES[ \t]*$)"],
        [r"RETENÇÕES FEDERAIS", r"VALORES IBS/CBS", r"OUTRAS INFORMAÇÕES"]
    ) or texto
    return {
        "tipo": "nfse",
        "numero_nota": extrair_numero_nfse(texto),
        "chave_acesso": extrair_chave_nfse(texto),

        "emitente": extrair_prestador(texto),
        "destinatario": extrair_tomador(texto),

        "data_emissao": extrair_data_emissao_nfse(texto),
        "data_vencimento": None,
        "valor_total": extrair_valor_total_nfse(totais),
        "valor_liquido": campo_abaixo(totais, r"VALOR L[ÍI]QUIDO", DINHEIRO) or buscar_campo(totais, [r"VALOR LÍQUIDO(?: DA NFS-E| DA NOTA)?\s*:?\s*(?:R\$\s*)?([\d.,]+)"]),
        "valor_iss": campo_abaixo(totais, r"VALOR (?:DO )?ISS\b", DINHEIRO) or buscar_campo(totais, [r"(?:VALOR DO ISS(?:QN)?|ISS(?:QN)?)\s*:?\s*(?:R\$\s*)?([\d.,]+)"]),
        "base_calculo_iss": campo_abaixo(totais, r"BASE DE C[ÁA]LCULO", DINHEIRO) or buscar_campo(totais, [r"BASE DE CÁLCULO(?: DO ISS)?\s*:?\s*(?:R\$\s*)?([\d.,]+)"]),
        "aliquota_iss": campo_abaixo(totais, r"(?:AL[ÍI]QUOTA|ALIQ\. ISS)\s*\(%\)", r"\d+,\d+%?") or buscar_campo(totais, [r"AL[ÍI]QUOTA(?: DO ISS)?\s*:?\s*([\d.,]+)\s*%"]),
        "iss_retido": buscar_campo(texto, [r"ISS RETIDO\s*:?\s*(SIM|NÃO|NAO)"])
    }
