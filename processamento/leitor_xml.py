import defusedxml.ElementTree as ET
from extratores.nfe_xml import extrair_nfe_xml
from extratores.nfse_xml import extrair_nfse_xml

def identificar_xml(caminho):
    arvore = ET.parse(caminho)
    raiz = arvore.getroot()

    tag_raiz = raiz.tag.lower()

    if "portalfiscal.inf.br/nfe" in tag_raiz:
        return "nfe"

    if "abrasf.org.br/nfse" in tag_raiz:
        return "nfse"

    return "desconhecido"

def processar_xml(caminho):
    tipo = identificar_xml(caminho)

    if tipo == "nfe":
        return extrair_nfe_xml(caminho)

    if tipo == "nfse":
        return extrair_nfse_xml(caminho)

    return None