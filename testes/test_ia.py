import json
from processamento.ia import completar_com_ia


def habilitar(monkeypatch):
    for chave, valor in {'IA_HABILITADA':'1', 'IA_ENVIO_AUTORIZADO':'1', 'OPENAI_API_KEY':'chave-ficticia', 'IA_MODELO':'modelo-mock'}.items():
        monkeypatch.setenv(chave, valor)


def test_ia_sem_autorizacao(monkeypatch):
    monkeypatch.delenv('IA_ENVIO_AUTORIZADO', raising=False)
    monkeypatch.setattr('processamento.ia.chamar_api', lambda *a: (_ for _ in ()).throw(AssertionError()))
    assert completar_com_ia({}, 'texto', {'elegivel_ia': True})[1]['chamadas'] == 0


def test_ia_evidencia_e_preservacao(monkeypatch):
    habilitar(monkeypatch)
    campos = [{'campo':'numero_nota','valor':'42','evidencia':'Nota 42'},
              {'campo':'valor_total','valor':'999','evidencia':'Inventado 999'},
              {'campo':'data_emissao','valor':'01/01/2026','evidencia':'texto inexistente'}]
    monkeypatch.setattr('processamento.ia.chamar_api', lambda *a: {'status':'completed', 'output':[{'content':[{'type':'output_text','text':json.dumps({'campos':campos})}]}]})
    dados, meta = completar_com_ia({'tipo':'nfse', 'valor_total':10}, 'Nota 42', {'elegivel_ia':True})
    assert dados['numero_nota'] == '42'
    assert dados['valor_total'] == 10
    assert 'data_emissao' not in dados
    assert meta['campos_aceitos'] == ['numero_nota']


def test_ia_timeout(monkeypatch):
    habilitar(monkeypatch)
    def falhar(*a):
        raise TimeoutError()
    monkeypatch.setattr('processamento.ia.chamar_api', falhar)
    dados, meta = completar_com_ia({'tipo':'nfse'}, 'Nota 42', {'elegivel_ia':True})
    assert meta['erro'] == 'TimeoutError'
    assert meta['chamadas'] == 1
