import xml.etree.ElementTree as ET


NAMESPACE = {
    "nfse": "http://www.abrasf.org.br/nfse.xsd"
}


def obter_texto(elemento, caminho):
    if elemento is None:
        return None

    campo = elemento.find(caminho, NAMESPACE)

    if campo is not None:
        return campo.text

    return None

def extrair_nfse_xml(caminho):
    arvore = ET.parse(caminho)
    raiz = arvore.getroot()

    inf_nfse = raiz.find(".//nfse:InfNfse", NAMESPACE)

    numero_nota = obter_texto(
        inf_nfse,
        "nfse:Numero"
    )

    data_emissao = obter_texto(
        inf_nfse,
        "nfse:DataEmissao"
    )

    prestador = raiz.find(
        ".//nfse:PrestadorServico",
        NAMESPACE
    )

    cnpj_prestador = obter_texto(
        prestador,
        "nfse:IdentificacaoPrestador/nfse:Cnpj"
    )

    razao_prestador = obter_texto(
        prestador,
        "nfse:RazaoSocial"
    )

    tomador = raiz.find(
        ".//nfse:TomadorServico",
        NAMESPACE
    )

    cnpj_tomador = obter_texto(
        tomador,
        "nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cnpj"
    )

    cpf_tomador = obter_texto(
        tomador,
        "nfse:IdentificacaoTomador/nfse:CpfCnpj/nfse:Cpf"
    )

    documento_tomador = (
        cnpj_tomador
        if cnpj_tomador
        else cpf_tomador
    )

    razao_tomador = obter_texto(
        tomador,
        "nfse:RazaoSocial"
    )

    valor_total = obter_texto(
        inf_nfse,
        "nfse:Servico/nfse:Valores/nfse:ValorServicos"
    )

    return {
        "tipo": "nfse",
        "numero_nota": numero_nota,

        "emitente": {
            "cnpj": cnpj_prestador,
            "razao_social": razao_prestador
        },

        "destinatario": {
            "cnpj_cpf": documento_tomador,
            "razao_social": razao_tomador
        },

        "data_emissao": data_emissao,
        "data_vencimento": None,
        "valor_total": valor_total
    }

if __name__ == "__main__":
    resultado = extrair_nfse_xml(
        "entrada/nfse_teste.xml"
    )

    print(resultado)