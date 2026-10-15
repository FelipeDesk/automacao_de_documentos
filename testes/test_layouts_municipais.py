"""Regressões sintéticas dos layouts em colunas e do XML municipal."""
import hashlib
import json
import pytest
from extratores.campos_layout import campo_abaixo, DINHEIRO
from extratores.nfe_pdf import extrair_nfe_pdf
from extratores.nfse_pdf import extrair_nfse_pdf
from processamento.normalizador import normalizar_resultado
from processamento.pipeline import processar_documento, VERSAO_EXTRACAO
from processamento.lote import processar_recebido
from processamento.banco import Banco


def linha(*colunas):
    return ''.join(valor.ljust(largura) for valor, largura in colunas).rstrip()


@pytest.mark.parametrize('rotulo', ['VALOR TOTAL DA NOTA (R$)', 'VALOR BRUTO', 'VALOR TOTAL DA NFS-E'])
def test_total_nota_nfse_inline_ou_abaixo(rotulo):
    for separador in ('     ', '\n'):
        dados = normalizar_resultado(extrair_nfse_pdf(f'NFS-e\n{rotulo}{separador}123,45'))
        assert dados['valor_total'] == 123.45


@pytest.mark.parametrize('separador', ['    ', ' | '])
def test_ocr_nao_desloca_deducao_para_liquido_vazio(separador):
    texto = f'Valor Líquido (R$)    Valor Total das Deduções (R$){separador}Base de Cálculo (R$)\n0,00    123,45\nVALOR TOTAL DA NOTA (R$)    123,45'
    dados = normalizar_resultado(extrair_nfse_pdf(texto))
    assert dados['valor_liquido'] is None
    assert dados['valor_total'] == 123.45


def test_foto_danfe_sem_titulo_emitente_e_chave_ilegivel():
    texto = '\n'.join([
        'DANFE\nCHAVE DE ACESSO\nchave ilegivel', 'EMPRESA  FICTICIA SA',
        'N a 000.000.876', 'CNPJ\n11.222.333/0001-81',
        linha(('NOME RAZÃO SOCIAL', 40), ('CNPJ/CPF', 30), ('DATA EMISÃO', 25)),
        linha(('Pessoa Ficticia', 40), ('529.982.247-25', 30), ('02/02/2026', 25)),
        'BASE DE CÁLCULO DO ICMS', 'VALOR TOTAL DA NOTA: 123,45',
    ])
    dados = normalizar_resultado(extrair_nfe_pdf(texto))
    from processamento.avaliador import avaliar_extracao
    assert dados['emitente']['razao_social'] == 'EMPRESA FICTICIA SA'
    assert dados['valor_total'] == 123.45
    assert dados['numero_nota'] == '000000876'
    assert avaliar_extracao(dados)['campos_ausentes'] == ['chave_acesso']


def test_nfse_cabecalho_em_colunas_sem_confundir_rps():
    texto = '\n'.join([
        linha(('PREFEITURA FICTICIA', 70), ('Número NFS-e', 25)),
        linha(('', 70), ('876', 25)),
        linha(('NFS-e', 70), ('Data e Hora de Emissão', 25)),
        linha(('', 70), ('02/02/2026 10:00:00', 25)),
        'RPS Nº: 875  Emitido em: 01/02/2026',
        'PRESTADOR DE SERVIÇOS',
        'CNPJ / CPF: 11.222.333/0001-81  Inscrição Municipal: 555',
        'Nome/Razão Social: Empresa Ficticia',
        'TOMADOR DE SERVIÇOS',
        'CPF/CNPJ: 529.982.247-25  Inscrição Municipal: ----',
        'Nome/Razão Social: Pessoa Ficticia',
        'INTERMEDIÁRIO DE SERVIÇOS',
        'CPF/CNPJ: 00.000.000/0000-00',
        'DISCRIMINAÇÃO DE SERVIÇOS',
        'VALOR TOTAL DO SERVIÇO = R$ 200,00',
        linha(('Valor Total das Deduções (R$)', 35), ('Base de Cálculo (R$)', 30), ('Alíquota (%)', 20), ('Valor do ISS (R$)', 25), ('Crédito (R$)', 20)),
        linha(('0,00', 35), ('200,00', 30), ('3,00%', 20), ('6,00', 25), ('0,00', 20)),
    ])
    dados = normalizar_resultado(extrair_nfse_pdf(texto))
    assert dados['numero_nota'] == '876'
    assert dados['data_emissao'] == '02/02/2026'
    assert dados['valor_total'] == 200
    assert dados['valor_liquido'] is None
    assert dados['valor_iss'] == 6
    assert dados['base_calculo_iss'] == 200
    assert dados['aliquota_iss'] == 3
    assert dados['destinatario']['cnpj_cpf'] == '529.982.247-25'
    assert dados['destinatario']['razao_social'] == 'Pessoa Ficticia'


def test_totais_em_colunas_preservam_bruto_liquido_iss():
    texto = '\n'.join([
        'NFS-e\nVALORES',
        linha(('Valor Serviço', 20), ('Deduções', 20), ('Base de Cálculo', 24), ('Aliq. ISS (%)', 20), ('Valor ISS', 20), ('Valor Liquido', 20)),
        linha(('R$ 300,00', 20), ('R$ 0,00', 20), ('R$ 300,00', 24), ('2,0000', 20), ('R$ 6,00', 20), ('R$ 294,00', 20)),
    ])
    dados = normalizar_resultado(extrair_nfse_pdf(texto))
    assert (dados['valor_total'], dados['valor_liquido'], dados['valor_iss']) == (300, 294, 6)
    assert dados['aliquota_iss'] == 2


def test_campo_tabular_nao_rouba_valor_da_proxima_linha():
    assert campo_abaixo('VALOR TOTAL DOS SERVIÇOS: R$ 100,00\nVALOR LÍQUIDO: R$ 90,00', 'VALOR TOTAL DOS SERVIÇOS', DINHEIRO) is None
    assert campo_abaixo('VALOR TOTAL DOS SERVIÇOS\nVALOR LÍQUIDO: R$ 90,00', 'VALOR TOTAL DOS SERVIÇOS', DINHEIRO) is None


def test_danfe_colunas():
    texto = '\n'.join([
        'Recebemos de Empresa Ficticia, os produtos constantes da nota fiscal',
        'NF-e N° 000.000.876',
        'IDENTIFICAÇÃO DO EMITENTE',
        'CNPJ', '11.222.333/0001-81',
        'CHAVE DE ACESSO', '1111 1111 1111 1111 1111 1111 1111 1111 1111 1111 1111',
        'DANFE NOTA FISCAL ELETRÔNICA',
        'DESTINATÁRIO/REMETENTE',
        linha(('NOME/RAZÃO SOCIAL', 40), ('CNPJ/CPF/IdEstrangeiro', 30), ('DATA DE EMISSÃO', 25)),
        linha(('Pessoa Ficticia', 40), ('529.982.247-25', 30), ('02/02/2026', 25)),
        'CÁLCULO DO IMPOSTO',
        linha(('VALOR DO FRETE', 30), ('VALOR DO IPI', 30), ('VALOR TOTAL DA NOTA', 30)),
        linha(('0,00', 30), ('0,00', 30), ('300,00', 30)),
    ])
    dados = normalizar_resultado(extrair_nfe_pdf(texto))
    assert dados['numero_nota'] == '000000876'
    assert dados['emitente']['razao_social'] == 'Empresa Ficticia'
    assert dados['destinatario']['razao_social'] == 'Pessoa Ficticia'
    assert dados['data_emissao'] == '02/02/2026'
    assert dados['valor_total'] == 300
    assert dados['data_vencimento'] is None


XML = '''<RetornoConsulta><Cabecalho><Sucesso>true</Sucesso></Cabecalho><NFe>
<ChaveNFe><InscricaoPrestador>555</InscricaoPrestador><NumeroNFe>876</NumeroNFe><CodigoVerificacao>TESTE123</CodigoVerificacao></ChaveNFe>
<DataEmissaoNFe>2026-02-02T10:00:00</DataEmissaoNFe><ChaveRPS><NumeroRPS>875</NumeroRPS></ChaveRPS>
<CPFCNPJPrestador><CNPJ>11222333000181</CNPJ></CPFCNPJPrestador><RazaoSocialPrestador>Empresa Ficticia</RazaoSocialPrestador>
<ValorServicos>300.00</ValorServicos><AliquotaServicos>0.02</AliquotaServicos><ValorISS>6.00</ValorISS><ISSRetido>false</ISSRetido>
<CPFCNPJTomador><CPF>52998224725</CPF></CPFCNPJTomador><RazaoSocialTomador>Pessoa Ficticia</RazaoSocialTomador>
</NFe></RetornoConsulta>'''


@pytest.mark.parametrize('namespace', ['', ' xmlns="http://www.prefeitura.sp.gov.br/nfe"'])
def test_xml_municipal_sem_confundir_nfe(tmp_path, namespace):
    arquivo = tmp_path / 'ficticio.xml'
    arquivo.write_text(XML.replace('<RetornoConsulta>', f'<RetornoConsulta{namespace}>'), encoding='utf-8')
    dados = processar_documento(arquivo)
    assert dados['tipo'] == 'nfse'
    assert dados['numero_nota'] == '876'
    assert dados['valor_iss'] == 6
    assert dados['valor_liquido'] is None
    assert dados['aliquota_iss'] == 2
    assert dados['iss_retido'] == 'NÃO'
    assert dados['avaliacao']['status_extracao'] == 'completo'


def test_reenvio_reavalia_resultado_antigo_sem_criar_duplicata(tmp_path, monkeypatch):
    arquivo = tmp_path / 'ficticio.xml'
    arquivo.write_text(XML, encoding='utf-8')
    digest = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    banco = Banco(tmp_path / 'notas.sqlite3')
    banco.salvar({'id':digest,'origem':arquivo.name,'status':'erro','dados':None,'erro':'layout antigo',
                  'processado_em':'2026-01-01T00:00:00+00:00','duplicado':False})
    novo = processar_recebido(arquivo, tmp_path)
    assert novo['status'] == 'sucesso'
    assert novo['versao_extracao'] == VERSAO_EXTRACAO
    assert novo['id'] == digest
    assert len(banco.listar()) == 1
    assert banco.obter(digest)['erro'] is None
    salvo = json.loads((tmp_path/'resultados'/'registros'/f'{digest}.json').read_text(encoding='utf-8'))
    assert salvo['status'] == 'sucesso'
    def nao_extrair(*a):
        raise AssertionError('Resultado atual deve ser reutilizado')
    monkeypatch.setattr('processamento.lote.processar_documento', nao_extrair)
    assert processar_recebido(arquivo,tmp_path)['duplicado']


def test_total_da_nota_tem_prioridade_sobre_item_individual():
    texto = '\n'.join([
        'NFS-e',
        linha(('Valor Serviço (R$)', 25), ('Valor ISS (R$)', 25)),
        linha(('R$ 100,00', 25), ('R$ 2,00', 25)),
        'VALORES',
        linha(('Valor Serviço', 25), ('Valor ISS', 25), ('Valor Liquido', 25)),
        linha(('R$ 300,00', 25), ('R$ 6,00', 25), ('R$ 294,00', 25)),
        'VALORES IBS/CBS',
        'Valor CBS  R$ 0,00',
    ])
    dados = normalizar_resultado(extrair_nfse_pdf(texto))
    assert (dados['valor_total'],dados['valor_iss'],dados['valor_liquido']) == (300,6,294)
