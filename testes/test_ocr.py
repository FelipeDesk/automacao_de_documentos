import pymupdf
import pytest
from PIL import Image
from processamento.leitor import ler_documento


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
