from pypdf import PdfReader
from ocr import extrair_texto_imagem
from ocr import extrair_texto_imagem, aplicar_ocr_pagina_pdf

def texto_util(texto):
    if not texto:
        return False

    texto = texto.strip()

    if len(texto) < 20:
        return False

    return True

def ler_txt(caminho):
    return caminho.read_text(encoding="utf-8")


def ler_pdf(caminho):
    leitor = PdfReader(caminho)

    texto_completo = ""

    for numero_pagina, pagina in enumerate(leitor.pages):
    
        texto_pagina = pagina.extract_text()

        if texto_util(texto_pagina):
            texto_completo += texto_pagina + "\n"

        else:
            texto_ocr = aplicar_ocr_pagina_pdf(
                caminho,
                numero_pagina
            )

            if texto_util(texto_ocr):
                texto_completo += texto_ocr + "\n"

    return texto_completo


def ler_documento(caminho):

    extensao = caminho.suffix.lower()

    if extensao == ".txt":
        texto = ler_txt(caminho)

        return texto, "sucesso"

    if extensao == ".pdf":
        texto = ler_pdf(caminho)

        if texto_util(texto):
            return texto, "sucesso"

        return None, "ocr_falhou"

    if extensao in [".jpg", ".jpeg", ".png"]:
        texto = extrair_texto_imagem(caminho)

        if texto_util(texto):
            return texto, "sucesso"

        return None, "ocr_falhou"

    return None, "formato_nao_suportado"