from pathlib import Path
from pypdf import PdfReader

from ocr import aplicar_ocr_pagina_pdf


def texto_util(texto):
    if not texto:
        return False

    return len(texto.strip()) >= 20


def ler_pdf(caminho):
    leitor = PdfReader(caminho)

    partes_texto = []

    for numero_pagina, pagina in enumerate(leitor.pages):
        texto_pagina = pagina.extract_text() or ""

        if not texto_util(texto_pagina):
            texto_pagina = aplicar_ocr_pagina_pdf(
                caminho,
                numero_pagina
            )

        if texto_util(texto_pagina):
            partes_texto.append(texto_pagina)

    return "\n".join(partes_texto)


def ler_documento(caminho):
    caminho = Path(caminho)

    if caminho.suffix.lower() != ".pdf":
        return None, "formato_nao_suportado"

    texto = ler_pdf(caminho)

    if texto_util(texto):
        return texto, "sucesso"

    return None, "texto_nao_encontrado"