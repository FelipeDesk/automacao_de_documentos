import pymupdf
import pytesseract

from PIL import Image
from io import BytesIO


pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extrair_texto_imagem(caminho):
    imagem = Image.open(caminho)

    texto = pytesseract.image_to_string(
        imagem,
        lang="por"
    )

    return texto


def aplicar_ocr_pagina_pdf(caminho, numero_pagina):
    documento = pymupdf.open(caminho)

    pagina = documento[numero_pagina]

    pixmap = pagina.get_pixmap(dpi=300)

    imagem = Image.open(
        BytesIO(pixmap.tobytes("png"))
    )

    texto = pytesseract.image_to_string(
        imagem,
        lang="por",
        config="--psm 6"
    )

    documento.close()

    return texto