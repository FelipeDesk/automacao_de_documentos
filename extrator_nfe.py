import xml.etree.ElementTree as ET

NAMESPACE = {"nfe": "http://www.portalfiscal.inf.br/nfe"}

def obter_texto(elemento, caminho):
    if elemento is None:
        return None

    campo = elemento.find(caminho, NAMESPACE)

    if campo is not None:
        return campo.text

    return None

def extrair_nfe_xml(caminho):
    arvore = ET.parse(caminho)
    raiz = arvore.getroot()

    ide = raiz.find(".//nfe:ide", NAMESPACE)
    emitente = raiz.find(".//nfe:emit", NAMESPACE)
    destinatario = raiz.find(".//nfe:dest", NAMESPACE)
    total = raiz.find(".//nfe:ICMSTot", NAMESPACE)
    inf_nfe = raiz.find(".//nfe:infNFe", NAMESPACE)
    duplicata = raiz.find(".//nfe:dup", NAMESPACE)

    numero_nota = obter_texto(
        ide,
        "nfe:nNF"
    )

    data_emissao = obter_texto(
        ide,
        "nfe:dhEmi"
    )

    cnpj_emitente = obter_texto(
        emitente,
        "nfe:CNPJ"
    )

    razao_emitente = obter_texto(
        emitente,
        "nfe:xNome"
    )

    cnpj_destinatario = obter_texto(
        destinatario,
        "nfe:CNPJ"
    )

    cpf_destinatario = obter_texto(
        destinatario,
        "nfe:CPF"
    )

    razao_destinatario = obter_texto(
        destinatario,
        "nfe:xNome"
    )

    documento_destinatario = (
        cnpj_destinatario
        if cnpj_destinatario
        else cpf_destinatario
    )

    valor_total = obter_texto(
        total,
        "nfe:vNF"
    )

    data_vencimento = obter_texto(
        duplicata,
        "nfe:dVenc"
    )

    chave_acesso = None

    if inf_nfe is not None:
        id_nfe = inf_nfe.get("Id")

        if id_nfe:
            chave_acesso = id_nfe.replace(
                "NFe",
                "",
                1
            )

    return {
        "tipo": "nfe",
        "numero_nota": numero_nota,
        "chave_acesso": chave_acesso,

        "emitente": {
            "cnpj": cnpj_emitente,
            "razao_social": razao_emitente
        },

        "destinatario": {
            "cnpj_cpf": documento_destinatario,
            "razao_social": razao_destinatario
        },

        "data_emissao": data_emissao,
        "data_vencimento": data_vencimento,
        "valor_total": valor_total
    }
