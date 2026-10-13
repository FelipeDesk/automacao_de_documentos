from pathlib import Path

from processamento.leitor_xml import processar_xml


FIXTURES = Path(__file__).parent / "fixtures"


def test_extrair_nfe_xml():
    caminho = FIXTURES / "nfe_teste.xml"

    resultado = processar_xml(caminho)

    assert resultado is not None
    assert resultado["tipo"] == "nfe"
    assert resultado["numero_nota"] is not None
    assert resultado["emitente"]["cnpj"] is not None
    assert resultado["valor_total"] is not None


def test_extrair_nfse_xml():
    caminho = FIXTURES / "nfse_teste.xml"

    resultado = processar_xml(caminho)

    assert resultado is not None
    assert resultado["tipo"] == "nfse"
    assert resultado["numero_nota"] is not None
    assert resultado["emitente"]["cnpj"] is not None
    assert resultado["valor_total"] is not None

def test_xml_desconhecido():
    caminho = FIXTURES / "xml_desconhecido.xml"

    resultado = processar_xml(caminho)

    assert resultado is None