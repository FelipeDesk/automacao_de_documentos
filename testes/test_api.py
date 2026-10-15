from fastapi.testclient import TestClient
from api import criar_app

XML = b'<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe/></NFe>'


def test_upload_consulta_status_duplicado(tmp_path):
    with TestClient(criar_app(tmp_path)) as cliente:
        resposta = cliente.post('/api/upload', files={'arquivo':('../../nota.xml', XML, 'application/xml')})
        assert resposta.status_code == 200
        nota = resposta.json()
        assert nota['status'] == 'revisao_necessaria'
        assert nota['origem'] == 'nota.xml'
        assert cliente.get('/api/notas').json()[0]['id'] == nota['id']
        assert cliente.get(f"/api/notas/{nota['id']}").status_code == 200
        assert cliente.get(f"/api/processamentos/{nota['id']}").json()['status'] == 'revisao_necessaria'
        assert cliente.post('/api/upload', files={'arquivo':('copia.xml', XML)}).json()['duplicado']
        assert cliente.get('/api/notas/inexistente').status_code == 404
        assert cliente.get('/docs').status_code == 200
        assert cliente.get('/api/notas?tipo=outro').status_code == 422


def test_upload_invalido(tmp_path, monkeypatch):
    cliente = TestClient(criar_app(tmp_path))
    assert cliente.post('/api/upload', files={'arquivo':('nota.exe', b'abc')}).status_code == 415
    assert cliente.post('/api/upload', files={'arquivo':('nota.pdf', b'abc')}).status_code == 415
    assert cliente.post('/api/upload', files={'arquivo':('nota.xml', b'')}).status_code == 400
    monkeypatch.setattr('api.MAX_UPLOAD', 5)
    assert cliente.post('/api/upload', files={'arquivo':('nota.xml', XML)}).status_code == 413


def test_api_registra_xml_corrompido_e_rejeita_entidades(tmp_path):
    cliente = TestClient(criar_app(tmp_path))
    resposta = cliente.post('/api/upload', files={'arquivo':('ruim.xml', b'<NFe')})
    assert resposta.status_code == 200
    assert resposta.json()['status'] == 'erro'
    assert cliente.get('/api/notas').json()[0]['erro']
    assert cliente.post('/api/upload', files={'arquivo':('entidade.xml', b'<!DOCTYPE a><a/>')}).status_code == 400


def test_excluir_nota_remove_exportacoes_e_permite_reenvio(tmp_path):
    cliente = TestClient(criar_app(tmp_path))
    nota = cliente.post('/api/upload', files={'arquivo': ('nota.xml', XML)}).json()
    identificador = nota['id']
    assert cliente.delete(f'/api/notas/{identificador}').json() == {'excluida': True}
    assert cliente.get('/api/notas').json() == []
    assert cliente.get(f'/api/notas/{identificador}').status_code == 404
    assert cliente.get(f'/api/processamentos/{identificador}').status_code == 404
    assert not (tmp_path / 'resultados' / 'registros' / f'{identificador}.json').exists()
    assert identificador not in (tmp_path / 'resultados' / 'notas.csv').read_text(encoding='utf-8-sig')
    assert list((tmp_path / 'revisao').glob('*.xml'))  # original preservado
    assert cliente.delete(f'/api/notas/{identificador}').status_code == 404
    reenvio = cliente.post('/api/upload', files={'arquivo': ('nota.xml', XML)}).json()
    assert not reenvio['duplicado']
    assert len(cliente.get('/api/notas').json()) == 1
