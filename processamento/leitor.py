from pathlib import Path
from pypdf import PdfReader
from processamento.ocr import aplicar_ocr_pagina_pdf, extrair_texto_imagem


def texto_util(texto):
    return bool(texto and len(texto.strip()) >= 20)


def ler_pdf(caminho, metadados=None):
    partes = []
    for numero, pagina in enumerate(PdfReader(caminho).pages):
        texto = (pagina.extract_text(extraction_mode='layout') or '') if pagina.get('/Contents') is not None else ''
        if not texto_util(texto):
            texto = aplicar_ocr_pagina_pdf(caminho, numero)
            if metadados is not None:
                metadados['ocr_utilizado'] = True
        if texto_util(texto):
            partes.append(texto)
    return '\n'.join(partes)


def ler_documento(caminho, metadados=None):
    caminho = Path(caminho)
    if metadados is not None:
        metadados['ocr_utilizado'] = False
    if caminho.suffix.lower() == '.pdf':
        texto = ler_pdf(caminho, metadados)
    elif caminho.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
        texto = extrair_texto_imagem(caminho)
        if metadados is not None:
            metadados['ocr_utilizado'] = True
    else:
        return None, 'formato_nao_suportado'
    return (texto, 'sucesso') if texto_util(texto) else (None, 'texto_nao_encontrado')
