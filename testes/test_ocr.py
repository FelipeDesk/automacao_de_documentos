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
