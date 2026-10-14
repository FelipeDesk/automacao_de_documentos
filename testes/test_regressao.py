import csv
import json
import os
from pathlib import Path
import pytest
from testes.conftest import TEXTO_NFSE
from processamento.pipeline import processar_documento
from processamento.lote import processar_lote, processar_recebido
from processamento.normalizador import normalizar_resultado
from processamento.validador import validar_chave_acesso
from extratores.nfe_xml import extrair_nfe_xml
from extratores.nfe_pdf import extrair_nfe_pdf


@pytest.mark.parametrize('extensao', ['png', 'jpg', 'jpeg', 'pdf'])
def test_pipeline_ocr(documento_ficticio, monkeypatch, extensao):
    arquivo = documento_ficticio(extensao, escaneado=True)
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_string', lambda *a, **k: TEXTO_NFSE)
    dados = processar_documento(arquivo)
    assert dados['numero_nota'] == '42'
    assert dados['valor_total'] == 100
    assert dados['valor_liquido'] == 95
    assert dados['metadados']['ocr_utilizado']
    assert dados['avaliacao']['status_extracao'] == 'revisao_necessaria'


@pytest.mark.ocr_real
@pytest.mark.skipif(os.getenv('TESTAR_OCR_REAL') != '1', reason='OCR real é opt-in; requer Tesseract e idioma por')
@pytest.mark.parametrize('extensao', ['png', 'jpg', 'pdf'])
def test_tesseract_real(documento_ficticio, extensao):
    dados = processar_documento(documento_ficticio(extensao, escaneado=True))
    assert dados['numero_nota'] == '42'
    assert dados['valor_total'] == 100
    assert dados['metadados']['ocr_utilizado']


def test_pdf_texto_sem_ocr(documento_ficticio):
    dados = processar_documento(documento_ficticio('pdf'))
    assert not dados['metadados']['ocr_utilizado']
    assert dados['valor_total'] == 100
    assert dados['valor_liquido'] == 95
    assert dados['data_vencimento'] is None


@pytest.mark.parametrize('conteudo', [b'<xml quebrado', b'\x00\xff', b'<contrato/>', b'<!DOCTYPE a [<!ENTITY b "texto">]><a>&b;</a>'])
def test_erro_xml_registrado(tmp_path, conteudo):
    arquivo = tmp_path / 'invalido.xml'
    arquivo.write_bytes(conteudo)
    registro = processar_recebido(arquivo, tmp_path)
    assert registro['status'] == 'erro'
    assert registro['erro']
    assert registro['dados'] is None


def test_multiplos_vencimentos_xml_e_pdf(tmp_path):
    arquivo = tmp_path / 'parcelas.xml'
    arquivo.write_text('''<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe><cobr>
    <dup><dVenc>2026-02-01</dVenc></dup><dup><dVenc>2026-03-01</dVenc></dup>
    </cobr></infNFe></NFe>''')
    dados = normalizar_resultado(extrair_nfe_xml(arquivo))
    assert dados['vencimentos'] == ['01/02/2026', '01/03/2026']
    assert dados['data_vencimento'] == '01/02/2026'
    dados = extrair_nfe_pdf('VENCIMENTO 01/02/2026\nDT. VENC. 01/03/2026')
    assert dados['vencimentos'] == ['01/02/2026', '01/03/2026']


def test_nao_finitos_e_blocos_ausentes():
    dados = normalizar_resultado({'emitente':None, 'destinatario':None, 'valor_total':'NaN'})
    assert dados['valor_total'] is None
    assert dados['emitente']['cnpj'] is None
    assert not validar_chave_acesso('0' * 44)


def test_sucesso_csv_json_sqlite_e_movimentacao(tmp_path):
    entrada = tmp_path / 'entrada'
    entrada.mkdir()
    arquivo = entrada / 'ficticia.xml'
    # Identificadores sintéticos de teste, sem associação a empresas ou pessoas.
    arquivo.write_text('''<CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd"><Nfse><InfNfse>
    <Numero>42</Numero><DataEmissao>2026-01-20</DataEmissao>
    <PrestadorServico><IdentificacaoPrestador><Cnpj>11222333000181</Cnpj></IdentificacaoPrestador>
    <RazaoSocial>Empresa Ficticia</RazaoSocial></PrestadorServico>
    <TomadorServico><IdentificacaoTomador><CpfCnpj><Cpf>52998224725</Cpf></CpfCnpj></IdentificacaoTomador></TomadorServico>
    <Servico><Valores><ValorServicos>100.00</ValorServicos></Valores></Servico>
    </InfNfse></Nfse></CompNfse>''')
    assert processar_lote(tmp_path)['sucesso'] == 1
    assert not arquivo.exists()
    assert len(list((tmp_path / 'processados').iterdir())) == 1
    jsons = list((tmp_path / 'resultados' / 'registros').glob('*.json'))
    assert json.loads(jsons[0].read_text(encoding='utf-8'))['status'] == 'sucesso'
    with (tmp_path / 'resultados' / 'notas.csv').open(encoding='utf-8-sig', newline='') as arq:
        linhas = list(csv.DictReader(arq, delimiter=';'))
    assert len(linhas) == 1
    assert linhas[0]['numero_nota'] == '42'
    assert (tmp_path / 'notas.sqlite3').exists()
