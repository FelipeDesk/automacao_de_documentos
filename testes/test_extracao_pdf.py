from pathlib import Path

from processamento.leitor import ler_pdf
from extratores.nfe_pdf import extrair_nfe_pdf
from extratores.nfse_pdf import extrair_nfse_pdf
from processamento.normalizador import normalizar_resultado
from processamento.avaliador import avaliar_extracao


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


def test_danfe_compacto_recupera_campos_sem_rotulos_perfeitos():
    texto = '''Recebemos de FORNECEDOR FICTICIO, os produtos constantes da nota fiscal indicada ao lado:
Valor Total: R$29,36, Destinatario: CLIENTE FICTICIO
N F-e
DANFE
Nº 000.123.456
CHAVE DE ACESSO
3526 1011 2223 3300 0181 5500 1000 1234 5611 2345 6784
IDENTIFICAÇÃO DO EMITENTE
11.222.333/0001-81
DESTINAT�RIO/REMETENTE
CLIENTE FICTICIO DA SILVA            111.444.777-35        07/10/2026
Rua Exemplo 123                     07/10/2026
FATURA/DUPLICATA
'''
    dados = normalizar_resultado(extrair_nfe_pdf(texto))
    assert dados['numero_nota'] == '000123456'
    assert dados['chave_acesso'] == '35261011222333000181550010001234561123456784'
    assert dados['destinatario']['cnpj_cpf'] == '111.444.777-35'
    assert dados['destinatario']['razao_social'] == 'CLIENTE FICTICIO DA SILVA'
    assert dados['data_emissao'] == '07/10/2026'
    assert dados['valor_total'] == 29.36
    assert avaliar_extracao(dados)['status_extracao'] == 'completo'
