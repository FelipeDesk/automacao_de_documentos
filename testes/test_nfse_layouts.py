from extratores.nfse_pdf import extrair_nfse_pdf
from processamento.normalizador import normalizar_resultado


def test_bruto_liquido_separados():
    dados = normalizar_resultado(extrair_nfse_pdf('''NFS-e Numero da nota: 42
DADOS DO PRESTADOR
CNPJ: 00.000.000/0000-00
RAZAO SOCIAL: Empresa Ficticia
DADOS DO TOMADOR
CPF: 000.000.000-00
VALORES
VALOR TOTAL DOS SERVICOS: R$ 100,00
VALOR LIQUIDO DA NFS-E: R$ 95,00
VALOR DO ISS: R$ 5,00
ALIQUOTA: 5%
'''))
    assert dados['valor_total'] == 100
    assert dados['valor_liquido'] == 95
    assert dados['valor_iss'] == 5
    assert dados['emitente']['razao_social'] == 'Empresa Ficticia'


def test_liquido_nao_substitui_bruto():
    dados = extrair_nfse_pdf('NFS-e VALOR LÍQUIDO DA NFS-E: R$ 95,00')
    assert dados['valor_total'] is None
    assert dados['valor_liquido'] == '95,00'
