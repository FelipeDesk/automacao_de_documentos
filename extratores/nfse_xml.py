import defusedxml.ElementTree as ET


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
    if eh_nfse_paulistana(raiz):
        return extrair_nfse_paulistana(raiz)

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
        "valor_total": valor_total,
        "valor_liquido": obter_texto(inf_nfse, "nfse:Servico/nfse:Valores/nfse:ValorLiquidoNfse"),
        "valor_iss": obter_texto(inf_nfse, "nfse:Servico/nfse:Valores/nfse:ValorIss"),
        "base_calculo_iss": obter_texto(inf_nfse, "nfse:Servico/nfse:Valores/nfse:BaseCalculo")
    }

def eh_nfse_paulistana(raiz):
    nomes = {elemento.tag.rsplit("}", 1)[-1] for elemento in raiz.iter()}
    return {"ChaveNFe", "NumeroNFe", "CPFCNPJPrestador", "ValorServicos", "DataEmissaoNFe"}.issubset(nomes)


def extrair_nfse_paulistana(raiz):
    # O formato municipal chama NFS-e de NFe, sem o namespace da NF-e de produtos.
    for elemento in raiz.iter():
        elemento.tag = elemento.tag.rsplit("}", 1)[-1]
    notas = [e for e in raiz.iter('NFe') if e.find('ChaveNFe') is not None]
    if len(notas) != 1:
        raise ValueError('esperada_uma_nfse_por_xml')
    nota = notas[0]
    def campo(caminho):
        valor = nota.findtext(caminho)
        return valor.strip() if valor and valor.strip() else None
    aliquota = campo('AliquotaServicos')
    return {
        'tipo': 'nfse', 'numero_nota': campo('ChaveNFe/NumeroNFe'),
        'chave_acesso': None,
        'emitente': {'cnpj': campo('CPFCNPJPrestador/CNPJ'), 'razao_social': campo('RazaoSocialPrestador')},
        'destinatario': {'cnpj_cpf': campo('CPFCNPJTomador/CNPJ') or campo('CPFCNPJTomador/CPF'), 'razao_social': campo('RazaoSocialTomador')},
        'data_emissao': campo('DataEmissaoNFe'), 'data_vencimento': None,
        'valor_total': campo('ValorServicos'), 'valor_liquido': campo('ValorLiquidoNFe'),
        'valor_iss': campo('ValorISS'), 'base_calculo_iss': campo('BaseCalculo'),
        'aliquota_iss': float(aliquota) * 100 if aliquota else None,
        'iss_retido': {'true': 'SIM', 'false': 'NÃO'}.get((campo('ISSRetido') or '').lower()),
    }
