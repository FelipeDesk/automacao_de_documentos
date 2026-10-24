import pymupdf
import pytest
from PIL import Image
from processamento.leitor import ler_documento


def test_remocao_grade_preserva_original_e_tracos_curtos():
    from PIL import ImageDraw
    from processamento.ocr import remover_grade
    imagem = Image.new('L', (400, 300), 255)
    desenho = ImageDraw.Draw(imagem)
    for y in (20, 80, 140, 200):
        desenho.line((10, y, 390, y), fill=0)
    desenho.line((10, 20, 10, 200), fill=0)
    desenho.line((40, 40, 46, 40), fill=0)
    original = imagem.tobytes()
    limpa = remover_grade(imagem)
    assert imagem.tobytes() == original
    assert limpa.getpixel((100, 80)) == 255
    assert limpa.getpixel((10, 100)) == 255
    assert limpa.getpixel((43, 40)) == 0
    assert remover_grade(Image.new('L', (400, 300), 255)) is None


@pytest.mark.parametrize('ext', ['png', 'jpg', 'jpeg'])
def test_imagem(tmp_path, monkeypatch, ext):
    arquivo = tmp_path / f'nota.{ext}'
    Image.new('RGB', (800, 600), 'white').save(arquivo)
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_string', lambda *a, **k: 'NFS-e ficticia numero da nota 42')
    meta = {}
    assert ler_documento(arquivo, meta)[1] == 'sucesso'
    assert meta['ocr_utilizado']


def test_pdf_misto(tmp_path, monkeypatch):
    arquivo = tmp_path / 'misto.pdf'
    with pymupdf.open() as pdf:
        pdf.new_page().insert_text((50, 50), 'Documento fiscal ficticio com texto extraivel')
        pdf.new_page()
        pdf.save(arquivo)
    chamadas = []
    def ocr(caminho, pagina):
        chamadas.append(pagina)
        return 'NFS-e ficticia reconhecida por OCR'
    monkeypatch.setattr('processamento.leitor.aplicar_ocr_pagina_pdf', ocr)
    meta = {}
    assert ler_documento(arquivo, meta)[1] == 'sucesso'
    assert chamadas == [1]
    assert meta['ocr_utilizado']


def test_descobre_tesseract_windows_sem_variavel(tmp_path, monkeypatch):
    from processamento.ocr import configurar_tesseract
    exe = tmp_path / 'Tesseract-OCR' / 'tesseract.exe'
    exe.parent.mkdir()
    exe.touch()
    monkeypatch.delenv('TESSERACT_CMD', raising=False)
    monkeypatch.setenv('ProgramFiles', str(tmp_path))
    monkeypatch.setattr('processamento.ocr.shutil.which', lambda _: None)
    monkeypatch.setattr('processamento.ocr.os.name', 'nt')
    monkeypatch.setattr('processamento.ocr.pytesseract.pytesseract.tesseract_cmd', 'tesseract')
    configurar_tesseract()
    import pytesseract
    assert pytesseract.pytesseract.tesseract_cmd == str(exe)


@pytest.mark.parametrize('leituras,esperado', [(['123,45', '123,45'], True), (['123,45', '128,45'], False)])
def test_rele_total_pela_posicao_do_rotulo(monkeypatch, leituras, esperado):
    from processamento.ocr import refinar_campos_danfe
    dados = {'text': ['VALOR', 'TOTAL', 'DA', 'NOTA'], 'left': [50, 110, 170, 200],
             'top': [100]*4, 'height': [15]*4, 'width': [50, 50, 20, 40]}
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_data', lambda *a, **k: dados)
    respostas = iter(leituras)
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_string', lambda *a, **k: next(respostas))
    texto = refinar_campos_danfe(Image.new('L', (500, 500)), 'DANFE')
    assert ('VALOR TOTAL DA NOTA: 123,45' in texto) is esperado


def test_rele_celulas_do_cabecalho_danfe_sem_misturar_colunas(monkeypatch):
    from processamento.ocr import refinar_campos_danfe
    from extratores.nfe_pdf import extrair_nfe_pdf
    palavras = ['CHAVE', 'DE', 'ACESSO', 'DESTINATARIO/REM', 'CNPJCPF', 'DATA']
    dados = {'text': palavras, 'left': [2070, 2150, 2186, 589, 1999, 2497],
             'top': [225, 225, 225, 682, 700, 700], 'height': [20] * 6,
             'width': [70, 30, 84, 285, 94, 61]}
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_data', lambda *a, **k: dados)
    leituras = iter([
        'CHAVE DE ACESSO\n3525 1047 9609 5008 9351 5501 1000 8095 2810 5612 9695',
        '',
        'CNPJ\n47.960.950/0893-51',
        'NOME/RAZÃO SOCIAL\nSANDRA SANTIADO DE SOUZA SANTIAGO',
        'CNPJ/CPF\n168.227.168-40',
        'DATA EMISSÃO\n09/10/2025',
    ])
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_string', lambda *a, **k: next(leituras))
    texto = refinar_campos_danfe(Image.new('L', (3200, 1800)), 'DANFE\nMAGAZINE LUIZA SA')
    nota = extrair_nfe_pdf(texto)
    assert nota['chave_acesso'] == '35251047960950089351550110008095281056129695'
    assert nota['emitente']['cnpj'] == '47.960.950/0893-51'
    assert nota['destinatario']['cnpj_cpf'] == '168.227.168-40'
    assert nota['data_emissao'] == '09/10/2025'


def test_rele_numero_nfse_no_canto_superior(monkeypatch):
    from processamento.ocr import refinar_cabecalho_nfse
    dados = {'text': ['NFS-e'], 'left': [2200], 'top': [27]}
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_data', lambda *a, **k: dados)
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_string',
                        lambda *a, **k: 'Número NFS-e\n507800\nData e Hora de Emissão\n03/08/2025 12:46:47')
    texto = refinar_cabecalho_nfse(Image.new('L', (2373, 2403)), 'NFS-e\nRPS N° 507795')
    assert 'NÚMERO NFS-E: 507800' in texto
    assert 'DATA DA EMISSÃO: 03/08/2025' in texto


def test_rele_cabecalho_danfe_compacto_quando_titulo_falha(monkeypatch):
    from processamento.ocr import reconhecer
    leituras = iter([
        'N F-e\nConsulta de autenticidade no site da Sefaz',
        'DANFE\nDESTINATARIO/REMETENTE\nFATURA/DUPLICATA',
        'CHAVE DE ACESSO\n3526 1011 2223 3300 0181 5500 1000 1234 5611 2345 6784',
    ])
    monkeypatch.setattr('processamento.ocr.pytesseract.image_to_string', lambda *a, **k: next(leituras))
    texto = reconhecer(Image.new('RGB', (782, 666), 'white'))
    assert 'DANFE' in texto
    assert 'CHAVE DE ACESSO' in texto
