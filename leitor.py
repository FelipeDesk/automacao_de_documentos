from pypdf import PdfReader

def ler_txt(caminho):
    return caminho.read_text(encoding="utf-8")


def ler_pdf(caminho):
    leitor = PdfReader(caminho)

    texto = ""

    for pagina in leitor.pages:
        texto_pagina = pagina.extract_text()

        if texto_pagina:
            texto += texto_pagina + "\n"

    return texto

def ler_documento(caminho):

    extensao = caminho.suffix.lower()

    if extensao == ".txt":
        return ler_txt(caminho)

    if extensao == ".pdf":
        return ler_pdf(caminho)

    return None