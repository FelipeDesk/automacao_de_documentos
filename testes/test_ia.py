import json
import pytest
from io import BytesIO
from urllib.error import HTTPError
from PIL import Image
from processamento.ia import chamar_gemini, completar_com_ia


def habilitar(monkeypatch):
    monkeypatch.setattr('processamento.ia.time.sleep', lambda _: None)
    monkeypatch.delenv('IA_ENVIO_IMAGEM', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    for chave, valor in {'IA_HABILITADA':'1', 'IA_ENVIO_AUTORIZADO':'1', 'GEMINI_API_KEY':'chave-ficticia'}.items():
        monkeypatch.setenv(chave, valor)


def test_ia_sem_autorizacao(monkeypatch):
    monkeypatch.delenv('IA_ENVIO_AUTORIZADO', raising=False)
    monkeypatch.setattr('processamento.ia.chamar_gemini', lambda *a: (_ for _ in ()).throw(AssertionError()))
    assert completar_com_ia({}, 'texto', {'elegivel_ia': True})[1]['chamadas'] == 0


def test_ia_evidencia_e_preservacao(monkeypatch):
    habilitar(monkeypatch)
    campos = [{'campo':'numero_nota','valor':'42','evidencia':'Nota 42'},
              {'campo':'valor_total','valor':'999','evidencia':'Inventado 999'},
              {'campo':'data_emissao','valor':'01/01/2026','evidencia':'texto inexistente'}]
    monkeypatch.setattr('processamento.ia.chamar_gemini', lambda *a: {'status':'completed', 'output':[{'content':[{'type':'output_text','text':json.dumps({'campos':campos})}]}]})
    dados, meta = completar_com_ia({'tipo':'nfse', 'valor_total':10}, 'Nota 42', {'elegivel_ia':True})
    assert dados['numero_nota'] == '42'
    assert dados['valor_total'] == 10
    assert 'data_emissao' not in dados
    assert meta['campos_aceitos'] == ['numero_nota']


def test_ia_timeout(monkeypatch):
    habilitar(monkeypatch)
    def falhar(*a):
        raise TimeoutError()
    monkeypatch.setattr('processamento.ia.chamar_gemini', falhar)
    dados, meta = completar_com_ia({'tipo':'nfse'}, 'Nota 42', {'elegivel_ia':True})
    assert meta['erro'] == 'TimeoutError'
    assert meta['chamadas'] == 3


def test_ia_erro_http_mostra_codigo_sem_expor_mensagem(monkeypatch):
    habilitar(monkeypatch)
    corpo = json.dumps({'error': {'code': 'insufficient_quota', 'type': 'invalid_request_error',
                                   'message': 'A mensagem pode conter dados fiscais'}}).encode()
    def falhar(*_args):
        raise HTTPError('https://generativelanguage.googleapis.com', 429, 'Too Many Requests', {}, BytesIO(corpo))
    monkeypatch.setattr('processamento.ia.chamar_gemini', falhar)
    dados, meta = completar_com_ia({'tipo': 'nfe'}, 'Nota 42', {'elegivel_ia': True})
    assert dados == {'tipo': 'nfe'}
    assert meta['erro'] == 'HTTP 429 (insufficient_quota)'
    assert meta['status_http'] == 429
    assert 'dados fiscais' not in str(meta)


def test_ia_visao_exige_autorizacao_separada_e_revisa_evidencia(tmp_path, monkeypatch):
    habilitar(monkeypatch)
    foto = tmp_path / 'nota.jpg'
    Image.new('RGB', (80, 50), 'white').save(foto)
    capturados = []
    def responder(payload, _chave, _modelo):
        capturados.append(payload)
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text',
            'text': json.dumps({'campos': [{'campo': 'numero_nota', 'valor': '42',
                                           'evidencia': 'NFS-e 42'}]})}]}]}
    monkeypatch.setattr('processamento.ia.chamar_gemini', responder)
    dados = {'tipo': 'nfse'}
    _, meta_texto = completar_com_ia(dados, 'NFS-e incompleta', {'elegivel_ia': True}, foto)
    assert not meta_texto['imagem_enviada']
    assert not meta_texto['campos_aceitos']
    assert len(capturados[-1]['contents'][0]['parts']) == 1

    monkeypatch.setenv('IA_ENVIO_IMAGEM', '1')
    resultado, meta_visao = completar_com_ia(dados, 'NFS-e incompleta', {'elegivel_ia': True}, foto)
    assert resultado['numero_nota'] == '42'
    assert meta_visao['campos_aceitos'] == ['numero_nota']
    assert meta_visao['imagem_enviada']
    conteudo = capturados[-1]['contents'][0]['parts']
    assert conteudo[1]['inline_data']['mime_type'] == 'image/jpeg'
    assert conteudo[1]['inline_data']['data']


def test_ia_json_invalido(monkeypatch):
    habilitar(monkeypatch)
    monkeypatch.setattr('processamento.ia.chamar_gemini', lambda *a: {'status':'completed', 'output':[{'content':[{'type':'output_text','text':'não é JSON'}]}]})
    original = {'tipo':'nfse'}
    dados, meta = completar_com_ia(original, 'Nota 42', {'elegivel_ia':True})
    assert dados == original
    assert meta['erro'] == 'JSONDecodeError'
    assert meta['chamadas'] == 1


def test_ia_repete_503_e_completa_sem_manter_erro(monkeypatch):
    habilitar(monkeypatch)
    chamadas, esperas = [], []
    monkeypatch.setattr('processamento.ia.time.sleep', esperas.append)
    monkeypatch.setattr('processamento.ia.random.uniform', lambda *_: 0)
    def responder(payload, chave, modelo):
        chamadas.append(payload)
        if len(chamadas) < 3:
            raise HTTPError('https://generativelanguage.googleapis.com', 503, '', {},
                            BytesIO(b'{"error":{"status":"UNAVAILABLE"}}'))
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text',
                'text': '{"campos":[{"campo":"numero_nota","valor":"42","evidencia":"Nota 42"}]}'}]}]}
    monkeypatch.setattr('processamento.ia.chamar_gemini', responder)
    dados, meta = completar_com_ia({'tipo': 'nfse', 'valor_total': 10}, 'Nota 42', {'elegivel_ia': True})
    assert dados['numero_nota'] == '42'
    assert dados['valor_total'] == 10
    assert meta['chamadas'] == 3
    assert meta['erro'] is None
    assert meta['modelo'] == 'gemini-3.6-flash'
    assert meta['modelos_tentados'] == ['gemini-3.6-flash']
    assert meta['falhas'] == [
        {'tentativa': 1, 'modelo': 'gemini-3.6-flash', 'status_http': 503},
        {'tentativa': 2, 'modelo': 'gemini-3.6-flash', 'status_http': 503}]
    assert esperas == [1, 2]
    assert chamadas[0] == chamadas[1] == chamadas[2]


def test_ia_503_persistente_tenta_modelo_reserva(monkeypatch):
    habilitar(monkeypatch)
    modelos = []
    def responder(_payload, _chave, modelo):
        modelos.append(modelo)
        if modelo == 'gemini-3.6-flash':
            raise HTTPError('https://generativelanguage.googleapis.com', 503, '', {}, BytesIO(b'{}'))
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text',
                'text': '{"campos":[{"campo":"numero_nota","valor":"42","evidencia":"Nota 42"}]}'}]}]}
    monkeypatch.setattr('processamento.ia.chamar_gemini', responder)
    dados, meta = completar_com_ia({'tipo': 'nfse'}, 'Nota 42', {'elegivel_ia': True})
    assert dados['numero_nota'] == '42'
    assert meta['chamadas'] == 4
    assert meta['erro'] is None
    assert meta['modelo'] == 'gemini-3.5-flash-lite'
    assert meta['modelos_tentados'] == ['gemini-3.6-flash', 'gemini-3.5-flash-lite']
    assert modelos == ['gemini-3.6-flash'] * 3 + ['gemini-3.5-flash-lite']


def test_ia_503_em_ambos_modelos_preserva_diagnostico(monkeypatch):
    habilitar(monkeypatch)
    def falhar(*_):
        raise HTTPError('https://generativelanguage.googleapis.com', 503, '', {},
                        BytesIO(b'{"error":{"status":"UNAVAILABLE","message":"privado"}}'))
    monkeypatch.setattr('processamento.ia.chamar_gemini', falhar)
    original = {'tipo': 'nfse'}
    dados, meta = completar_com_ia(original, 'Nota 42', {'elegivel_ia': True})
    assert dados == original
    assert meta['chamadas'] == 5
    assert meta['erro'] == 'HTTP 503 (UNAVAILABLE)'
    assert meta['modelos_tentados'] == ['gemini-3.6-flash', 'gemini-3.5-flash-lite']
    assert 'privado' not in json.dumps(meta)


def test_ia_nao_inventa_valor_liquido_a_partir_do_total(monkeypatch):
    habilitar(monkeypatch)
    campos = [{'campo': 'valor_liquido', 'valor': '29,36',
               'evidencia': 'VALOR TOTAL DA NOTA 29,36'}]
    monkeypatch.setattr('processamento.ia.chamar_gemini', lambda *a: {
        'status': 'completed', 'output': [{'content': [{'type': 'output_text',
        'text': json.dumps({'campos': campos})}]}]})
    dados, meta = completar_com_ia({'tipo': 'nfe'}, 'VALOR TOTAL DA NOTA 29,36',
                                   {'elegivel_ia': True})
    assert dados.get('valor_liquido') is None
    assert meta['campos_aceitos'] == []


@pytest.mark.parametrize('status', [400, 401, 403, 404])
def test_ia_nao_repete_erro_permanente(monkeypatch, status):
    habilitar(monkeypatch)
    def falhar(*_):
        raise HTTPError('https://generativelanguage.googleapis.com', status, '', {}, BytesIO(b'{}'))
    monkeypatch.setattr('processamento.ia.chamar_gemini', falhar)
    _, meta = completar_com_ia({'tipo': 'nfse'}, 'Nota 42', {'elegivel_ia': True})
    assert meta['chamadas'] == 1
    assert meta['status_http'] == status


@pytest.mark.parametrize('prazo,chamadas,esperas', [('5', 3, [5, 5]), ('120', 1, [])])
def test_ia_respeita_retry_after(monkeypatch, prazo, chamadas, esperas):
    habilitar(monkeypatch)
    esperas_reais = []
    monkeypatch.setattr('processamento.ia.time.sleep', esperas_reais.append)
    def falhar(*_):
        raise HTTPError('https://generativelanguage.googleapis.com', 429, '',
                        {'Retry-After': prazo}, BytesIO(b'{}'))
    monkeypatch.setattr('processamento.ia.chamar_gemini', falhar)
    _, meta = completar_com_ia({'tipo': 'nfse'}, 'Nota 42', {'elegivel_ia': True})
    assert meta['chamadas'] == chamadas
    assert esperas_reais == esperas
    assert meta['erro'] == 'HTTP 429'


def test_gemini_seleciona_chave_modelo_e_schema(monkeypatch):
    habilitar(monkeypatch)
    monkeypatch.setenv('GEMINI_API_KEY', 'chave-gemini-ficticia')
    capturados = []
    def responder(payload, chave, modelo):
        capturados.append((payload, chave, modelo))
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text',
            'text': json.dumps({'campos': [{'campo': 'numero_nota', 'valor': '42',
                                           'evidencia': 'Nota 42'}]})}]}], 'usage': {}}
    monkeypatch.setattr('processamento.ia.chamar_gemini', responder)
    resultado, meta = completar_com_ia({'tipo': 'nfse'}, 'Nota 42', {'elegivel_ia': True})
    assert resultado['numero_nota'] == '42'
    assert meta['provedor'] == 'gemini'
    assert capturados[0][1:] == ('chave-gemini-ficticia', 'gemini-3.6-flash')
    payload = capturados[0][0]
    assert payload['generationConfig']['responseMimeType'] == 'application/json'
    assert payload['generationConfig']['responseJsonSchema']['properties']['campos']['type'] == 'array'
    assert payload['contents'][0]['parts'][0]['text'].endswith('"texto": "Nota 42"}')
    assert 'chave-gemini-ficticia' not in json.dumps(payload)


def test_gemini_enviou_foto_somente_com_autorizacao(tmp_path, monkeypatch):
    habilitar(monkeypatch)
    monkeypatch.setenv('GEMINI_API_KEY', 'chave-ficticia')
    foto = tmp_path / 'nota.jpg'
    Image.new('RGB', (80, 50), 'white').save(foto)
    capturados = []
    def responder(payload, *_args):
        capturados.append(payload)
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text',
            'text': '{"campos": []}'}]}], 'usage': {}}
    monkeypatch.setattr('processamento.ia.chamar_gemini', responder)
    completar_com_ia({'tipo': 'nfe'}, 'Nota 42', {'elegivel_ia': True}, foto)
    assert len(capturados[-1]['contents'][0]['parts']) == 1
    monkeypatch.setenv('IA_ENVIO_IMAGEM', '1')
    _, meta = completar_com_ia({'tipo': 'nfe'}, 'Nota 42', {'elegivel_ia': True}, foto)
    imagem = capturados[-1]['contents'][0]['parts'][1]['inline_data']
    assert imagem['mime_type'] == 'image/jpeg'
    assert len(imagem['data']) > 100
    assert meta['imagem_enviada']


def test_gemini_transporte_e_uso(monkeypatch):
    capturados = []
    def urlopen(requisicao, timeout):
        capturados.append((requisicao, timeout))
        return BytesIO(json.dumps({'candidates': [{'content': {'parts': [
            {'text': '{"campos": []}'}]}, 'finishReason': 'STOP'}],
            'usageMetadata': {'promptTokenCount': 12, 'candidatesTokenCount': 8,
                              'totalTokenCount': 20}}).encode())
    monkeypatch.setattr('processamento.ia.urllib.request.urlopen', urlopen)
    resposta = chamar_gemini({'contents': []}, 'segredo-ficticio', 'gemini-3.6-flash')
    requisicao, timeout = capturados[0]
    assert requisicao.full_url.endswith('/models/gemini-3.6-flash:generateContent')
    assert 'segredo-ficticio' not in requisicao.full_url
    assert requisicao.get_header('X-goog-api-key') == 'segredo-ficticio'
    assert timeout == 45
    assert resposta['status'] == 'completed'
    assert resposta['usage']['total_tokens'] == 20


def test_gemini_erro_cota_nao_expoe_mensagem(monkeypatch):
    habilitar(monkeypatch)
    monkeypatch.setenv('GEMINI_API_KEY', 'chave-ficticia')
    corpo = json.dumps({'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED',
                                   'message': 'Dados fiscais privados'}}).encode()
    def falhar(*_args):
        raise HTTPError('https://generativelanguage.googleapis.com', 429,
                        'Too Many Requests', {}, BytesIO(corpo))
    monkeypatch.setattr('processamento.ia.chamar_gemini', falhar)
    _, meta = completar_com_ia({'tipo': 'nfse'}, 'Nota 42', {'elegivel_ia': True})
    assert meta['erro'] == 'HTTP 429 (RESOURCE_EXHAUSTED)'
    assert 'Dados fiscais' not in str(meta)


def test_pipeline_aciona_gemini_quando_falta_campo(monkeypatch, tmp_path):
    from processamento.pipeline import processar_documento
    habilitar(monkeypatch)
    monkeypatch.setenv('GEMINI_API_KEY', 'chave-ficticia')
    arquivo = tmp_path / 'nota.pdf'
    arquivo.write_bytes(b'%PDF-ficticio')
    monkeypatch.setattr('processamento.pipeline.extrair_documento', lambda *_: (
        {'tipo': 'nfse', 'emitente': {}, 'destinatario': {}, 'valor_total': 10},
        'Nota 42\nValor total R$ 10,00', {'metodo': 'texto', 'ocr_utilizado': False}))
    chamados = []
    def responder(payload, chave, modelo):
        chamados.append((payload, chave, modelo))
        return {'status': 'completed', 'output': [{'content': [{'type': 'output_text',
            'text': '{"campos":[{"campo":"numero_nota","valor":"42","evidencia":"Nota 42"}]}'
        }]}], 'usage': {}}
    monkeypatch.setattr('processamento.ia.chamar_gemini', responder)
    dados = processar_documento(arquivo)
    assert len(chamados) == 1
    assert dados['numero_nota'] == '42'
    assert dados['metadados']['ia']['provedor'] == 'gemini'
    assert dados['metadados']['ia']['chamadas'] == 1
    assert dados['avaliacao']['status_extracao'] == 'revisao_necessaria'


def test_ia_nao_chama_se_completa(monkeypatch):
    habilitar(monkeypatch)
    assert completar_com_ia({'tipo':'nfse'}, 'Nota 42', {'elegivel_ia':False})[1]['chamadas'] == 0


def test_ia_completa_campos_validos_conclui_extracao(tmp_path, monkeypatch):
    from processamento.pipeline import processar_documento
    habilitar(monkeypatch)
    arquivo = tmp_path / 'nota.pdf'
    arquivo.write_bytes(b'%PDF-ficticio')
    monkeypatch.setattr('processamento.pipeline.extrair_documento', lambda *_: (
        {'tipo': 'nfse', 'numero_nota': '42', 'emitente': {'cnpj': '11222333000181'},
         'destinatario': {}, 'valor_total': 100, 'data_emissao': '20/01/2026'},
        'Nota 42', {'metodo': 'texto', 'ocr_utilizado': False}))
    def completar(dados, *args):
        dados['destinatario']['cnpj_cpf'] = '529.982.247-25'
        return dados, {'utilizada': True, 'chamadas': 1,
                       'campos_aceitos': ['destinatario.cnpj_cpf'], 'erro': None}
    monkeypatch.setattr('processamento.pipeline.completar_com_ia', completar)
    dados = processar_documento(arquivo)
    assert dados['avaliacao']['status_extracao'] == 'completo'
    assert dados['avaliacao']['campos_ausentes'] == []
    assert dados['avaliacao']['inconsistencias'] == []
    assert dados['metadados']['ia']['campos_aceitos'] == ['destinatario.cnpj_cpf']
    assert 'confianca_estimada' not in dados['avaliacao']
    assert 'criterio_confianca' not in dados['avaliacao']
