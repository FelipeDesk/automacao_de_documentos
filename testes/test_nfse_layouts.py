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


def test_nfse_foto_cpf_com_espaco_e_tabela_de_valores():
    texto = '''NFS-e\nNÚMERO NFS-E: 507800\nDATA DA EMISSÃO: 03/08/2025
PRESTADOR DE SERVIÇOS
CNPJ/CPF: 07.594.978/0150-19
Nome/Razão Social: Empresa de Ginástica SA
TOMADOR DE SERVIÇOS
CNPJ/CPF: 531.932 898-25
Nome/Razão Social: Cliente Exemplo
VALORES
Valor Serviço  Desc. Cond.  Desc. Incond.  Deduções  Base de Cálculo  Alig. ISS (%)  Valor ISS  ISSQN Retido  Valor Liquido  ISS Retido  Trib. Aprox.
R$ 99,90  R$ 0,00  R$ 0,00  R$ 0,00  R$ 99,90  2,0000  R$ 2,00  R$ 0,00  R$ 99,90  NÃO  R$ 11,24
RETENÇÕES FEDERAIS'''
    dados = normalizar_resultado(extrair_nfse_pdf(texto))
    assert dados['numero_nota'] == '507800'
    assert dados['destinatario']['cnpj_cpf'] == '531.932.898-25'
    assert dados['valor_total'] == dados['valor_liquido'] == 99.9
    assert dados['base_calculo_iss'] == 99.9
    assert dados['valor_iss'] == 2
