"""Contrato da API pública sem estado fiscal compartilhado."""
import os
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from api import criar_app


FIXTURES = Path(__file__).parent / 'fixtures'
XML = (FIXTURES / 'nfe_teste.xml').read_bytes()


def enviar(cliente, nome='nota.xml', conteudo=XML, tipo='application/xml'):
    return cliente.post('/api/upload', files={'arquivo': (nome, conteudo, tipo)})


def test_upload_xml_retorna_json_sem_persistencia(tmp_path):
    with TestClient(criar_app(tmp_path)) as cliente:
        resposta = enviar(cliente, '../../nota.xml')
        assert resposta.status_code == 200
        nota = resposta.json()
        assert nota['origem'] == 'nota.xml'
        assert nota['dados']['tipo'] == 'nfe'
        assert nota['status'] in ('sucesso', 'revisao_necessaria')
        assert resposta.headers['cache-control'] == 'no-store'
        assert not list(tmp_path.iterdir())
        assert cliente.get('/api/notas').status_code == 404
        assert cliente.get(f"/api/notas/{nota['id']}/arquivo").status_code == 404
        assert cliente.delete(f"/api/notas/{nota['id']}").status_code == 404
        assert cliente.get('/docs').status_code == 200


def test_upload_pdf_real_retorna_dados_sem_persistencia(tmp_path):
    conteudo = (FIXTURES / 'danfe_teste.pdf').read_bytes()
    resposta = enviar(TestClient(criar_app(tmp_path)), 'danfe_teste.pdf', conteudo, 'application/pdf')
    assert resposta.status_code == 200
    assert resposta.json()['dados']['tipo'] == 'nfe'
    assert resposta.json()['status'] != 'erro'
    assert not list(tmp_path.iterdir())


def test_upload_conclui_quando_ia_completa_campos_validos(tmp_path, monkeypatch):
    def processar(_caminho):
        return {'tipo': 'nfe', 'avaliacao': {'status_extracao': 'completo',
                'campos_ausentes': [], 'inconsistencias': []},
                'metadados': {'ia': {'utilizada': True,
                                    'campos_aceitos': ['destinatario.cnpj_cpf']}}}

    monkeypatch.setattr('api.processar_documento', processar)
    resposta = enviar(TestClient(criar_app(tmp_path)))
    assert resposta.status_code == 200
    assert resposta.json()['status'] == 'sucesso'
    assert resposta.json()['dados']['metadados']['ia']['campos_aceitos']
    assert not list(tmp_path.iterdir())


@pytest.mark.ocr_real
@pytest.mark.skipif(os.getenv('TESTAR_OCR_REAL') != '1', reason='OCR real requer Tesseract e idioma por')
def test_upload_imagem_real_com_ocr_sem_persistencia(tmp_path, documento_ficticio):
    caminho = documento_ficticio('jpg')
    temporarios = tmp_path / 'temporarios'
    temporarios.mkdir()
    resposta = enviar(TestClient(criar_app(temporarios)), caminho.name,
                      caminho.read_bytes(), 'image/jpeg')
    assert resposta.status_code == 200
    assert resposta.json()['status'] != 'erro'
    assert resposta.json()['dados']['tipo'] == 'nfse'
    assert resposta.json()['dados']['metadados']['ocr_utilizado'] is True
    assert not list(temporarios.iterdir())


def test_upload_pdf_e_imagem_usam_arquivo_temporario_e_apagam_em_erro(tmp_path, monkeypatch):
    caminhos = []

    def processar(caminho):
        caminhos.append(Path(caminho))
        assert Path(caminho).is_file()
        raise ValueError('conteudo fiscal simulado')

    monkeypatch.setattr('api.processar_documento', processar)
    cliente = TestClient(criar_app(tmp_path))
    for nome, conteudo, tipo in (
        ('nota.pdf', b'%PDF-1.4\nconteudo', 'application/pdf'),
        ('nota.jpg', b'\xff\xd8imagem', 'image/jpeg'),
        ('nota.png', b'\x89PNG\r\n\x1a\nimagem', 'image/png'),
    ):
        resposta = enviar(cliente, nome, conteudo, tipo)
        assert resposta.status_code == 200
        assert resposta.json()['status'] == 'erro'
        assert not list(tmp_path.iterdir())
    assert len(caminhos) == 3
    assert all(not caminho.exists() for caminho in caminhos)


def test_api_nao_compartilha_resultados_entre_sessoes(tmp_path):
    app = criar_app(tmp_path)
    with TestClient(app) as primeira, TestClient(app) as segunda:
        nota = enviar(primeira).json()
        assert nota['dados']['tipo'] == 'nfe'
        for cliente in (primeira, segunda):
            assert cliente.get('/api/notas').status_code == 404
            assert cliente.get(f"/api/notas/{nota['id']}").status_code == 404
        assert not list(tmp_path.iterdir())


def test_validacao_de_extensao_mime_assinatura_tamanho_e_xml(tmp_path, monkeypatch):
    cliente = TestClient(criar_app(tmp_path))
    casos = (
        ('nota.exe', b'abc', 'application/octet-stream', 415),
        ('nota.pdf', b'abc', 'application/pdf', 415),
        ('nota.jpg', b'%PDF-1.4', 'image/jpeg', 415),
        ('nota.xml', b'', 'application/xml', 400),
        ('nota.xml', b'abc', 'application/xml', 415),
        ('nota.xml', b'<!DOCTYPE a><a/>', 'application/xml', 400),
        ('nota.xml', XML, 'image/png', 415),
    )
    for nome, conteudo, tipo, status in casos:
        assert enviar(cliente, nome, conteudo, tipo).status_code == status
    monkeypatch.setattr('api.MAX_UPLOAD', 5)
    assert enviar(cliente).status_code == 413
    assert not list(tmp_path.iterdir())


def test_limite_de_requisicoes_e_ip_nao_confiado(tmp_path):
    cliente = TestClient(criar_app(tmp_path, requisicoes_por_minuto=1))
    assert enviar(cliente).status_code == 200
    resposta = cliente.post('/api/upload', headers={'X-Forwarded-For': 'outro-ip'},
                            files={'arquivo': ('nota.xml', XML, 'application/xml')})
    assert resposta.status_code == 429
    assert resposta.headers['retry-after'] == '60'
    assert not list(tmp_path.iterdir())


def test_falha_no_processamento_nao_registra_dados_fiscais(tmp_path, monkeypatch, caplog):
    def falhar(_caminho):
        raise RuntimeError('CNPJ 12345678901234 e chave secreta')

    monkeypatch.setattr('api.processar_documento', falhar)
    resposta = enviar(TestClient(criar_app(tmp_path)))
    assert resposta.status_code == 200
    assert resposta.json()['status'] == 'erro'
    assert '12345678901234' not in resposta.text
    assert '12345678901234' not in caplog.text
    assert not list(tmp_path.iterdir())
