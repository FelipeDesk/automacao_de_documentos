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
