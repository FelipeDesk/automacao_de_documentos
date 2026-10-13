import os
from io import BytesIO

import pymupdf
import pytesseract
from PIL import Image, ImageOps, ImageFilter, ImageStat


def preparar_imagem(imagem):
    imagem = ImageOps.exif_transpose(imagem).convert('RGB')
    if imagem.width < 1200:
        escala = min(3, 1200 / imagem.width)
        imagem = imagem.resize((int(imagem.width * escala), int(imagem.height * escala)), Image.Resampling.LANCZOS)
    cinza = ImageOps.grayscale(imagem)
    if ImageStat.Stat(cinza).stddev[0] < 40:
        cinza = ImageOps.autocontrast(cinza).filter(ImageFilter.MedianFilter(3))
        return cinza.point(lambda pixel: 255 if pixel > 150 else 0)
    return imagem


def reconhecer(imagem):
    comando = os.getenv('TESSERACT_CMD')
    if comando:
        pytesseract.pytesseract.tesseract_cmd = comando
    return pytesseract.image_to_string(preparar_imagem(imagem), lang=os.getenv('OCR_LANG', 'por'), config='--psm 3')


def extrair_texto_imagem(caminho):
    with Image.open(caminho) as imagem:
        return reconhecer(imagem)


def aplicar_ocr_pagina_pdf(caminho, numero_pagina):
    with pymupdf.open(caminho) as documento:
        pixmap = documento[numero_pagina].get_pixmap(dpi=300)
        with Image.open(BytesIO(pixmap.tobytes('png'))) as imagem:
            return reconhecer(imagem)
