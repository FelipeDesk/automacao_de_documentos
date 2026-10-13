from processamento.classificador_fiscal import identificar_tipo_pdf


def test_identificar_nfe():
    texto = """
    DANFE
    Documento Auxiliar da Nota Fiscal Eletrônica
    CHAVE DE ACESSO
    DESTINATÁRIO / REMETENTE
    """

    resultado = identificar_tipo_pdf(texto)

    assert resultado == "nfe"


def test_identificar_nfse():
    texto = """
    DANFSe
    Documento Auxiliar da NFS-e
    EMITENTE DA NFS-e
    TOMADOR DO SERVIÇO
    """

    resultado = identificar_tipo_pdf(texto)

    assert resultado == "nfse"


def test_documento_desconhecido():
    texto = """
    CONTRATO DE PRESTAÇÃO DE SERVIÇOS
    Documento particular entre duas empresas.
    """

    resultado = identificar_tipo_pdf(texto)

    assert resultado == "desconhecido"