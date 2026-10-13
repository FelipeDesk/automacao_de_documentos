from pathlib import Path

from processamento.leitor import ler_pdf
from extratores.nfe_pdf import extrair_nfe_pdf
from extratores.nfse_pdf import extrair_nfse_pdf


FIXTURES = Path(__file__).parent / "fixtures"


def test_extrair_nfe_pdf():
    texto = ler_pdf(FIXTURES / "danfe_teste.pdf")

    resultado = extrair_nfe_pdf(texto)

    assert resultado["tipo"] == "nfe"
    assert resultado["numero_nota"] is not None
    assert resultado["emitente"]["cnpj"] is not None
    assert resultado["valor_total"] is not None


def test_extrair_nfse_pdf():
    texto = ler_pdf(FIXTURES / "danfse_teste.pdf")

    resultado = extrair_nfse_pdf(texto)

    assert resultado["tipo"] == "nfse"
    assert resultado["numero_nota"] == "87352173"
    assert resultado["data_emissao"] == "21/01/2026"
    assert resultado["valor_total"] == "162,57"