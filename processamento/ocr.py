import os
import re
import shutil
from pathlib import Path
from io import BytesIO

import pymupdf
import pytesseract
from PIL import Image, ImageOps


def preparar_imagem(imagem):
    imagem = ImageOps.autocontrast(ImageOps.grayscale(ImageOps.exif_transpose(imagem)))
    if imagem.width < 2400:
        escala = 2 if imagem.width >= 1200 else min(3, 2400 / imagem.width)
        imagem = imagem.resize((int(imagem.width * escala), int(imagem.height * escala)), Image.Resampling.BICUBIC)
    # Limiar fixo apagava texto fino e números em fotos com sombra.
    return imagem


def configurar_tesseract():
    comando = os.getenv('TESSERACT_CMD') or shutil.which('tesseract')
    if not comando and os.name == 'nt':
        for raiz in (os.getenv('ProgramFiles'), os.getenv('LOCALAPPDATA')):
            if raiz:
                candidato = Path(raiz) / 'Tesseract-OCR' / 'tesseract.exe'
                if candidato.is_file():
                    comando = str(candidato)
                    break
    if comando:
        pytesseract.pytesseract.tesseract_cmd = comando


def refinar_campos_danfe(imagem, texto):
    """Relê regiões encontradas pelos rótulos, sem coordenadas fixas por fornecedor."""
    from processamento.validador import validar_chave_acesso
    dados = pytesseract.image_to_data(imagem, lang=os.getenv('OCR_LANG', 'por'),
                                     config='--psm 3', output_type=pytesseract.Output.DICT)
    palavras = [i for i, t in enumerate(dados['text']) if t.strip()]
    complementos = []
    for rotulo in ('VALOR TOTAL DA NOTA', 'CHAVE DE ACESSO'):
        tokens = rotulo.split()
        for pos in range(len(palavras) - len(tokens) + 1):
            indices = palavras[pos:pos + len(tokens)]
            if [dados['text'][i].upper() for i in indices] != tokens:
                continue
            altura = max(dados['height'][i] for i in indices)
            topo = min(dados['top'][i] for i in indices)
            if max(dados['top'][i] for i in indices) - topo > altura:
                continue
            esquerda = min(dados['left'][i] for i in indices)
            direita = max(dados['left'][i] + dados['width'][i] for i in indices)
            fim = imagem.width if rotulo == 'CHAVE DE ACESSO' else min(imagem.width, direita + (direita - esquerda) * .6)
            recorte = imagem.crop((max(0, esquerda - 12), max(0, topo - 4), int(fim),
                                   min(imagem.height, topo + altura * 5)))
            valores = []
            for modo in (6, 11):
                leitura = pytesseract.image_to_string(recorte, lang=os.getenv('OCR_LANG', 'por'), config=f'--psm {modo}')
                if rotulo == 'CHAVE DE ACESSO':
                    candidatos = re.findall(r'(?<!\d)(?:\d[ \t]*){44}(?!\d)', leitura)
                    valores.extend(c for v in candidatos if validar_chave_acesso(c := re.sub(r'\D', '', v)))
                else:
                    valores.extend(re.findall(r'\b\d[\d.]*,\d{2}(?!\d)', leitura))
            if len(set(valores)) == 1:
                complementos.append(f'{rotulo}: {valores[0]}')
    return texto + '\n' + '\n'.join(complementos)


def reconhecer(imagem):
    configurar_tesseract()
    imagem = preparar_imagem(imagem)
    texto = pytesseract.image_to_string(imagem, lang=os.getenv('OCR_LANG', 'por'), config='--psm 3 -c preserve_interword_spaces=1')
    if 'DANFE' in texto.upper():
        texto = refinar_campos_danfe(imagem, texto)
    return texto


def extrair_texto_imagem(caminho):
    with Image.open(caminho) as imagem:
        return reconhecer(imagem)


def aplicar_ocr_pagina_pdf(caminho, numero_pagina):
    with pymupdf.open(caminho) as documento:
        pixmap = documento[numero_pagina].get_pixmap(dpi=300)
        with Image.open(BytesIO(pixmap.tobytes('png'))) as imagem:
            return reconhecer(imagem)
