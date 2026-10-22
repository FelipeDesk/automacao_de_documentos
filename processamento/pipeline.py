"""Pipeline único de extração, compartilhado pelo lote e pela API."""
from pathlib import Path
from processamento.leitor import ler_documento
from processamento.leitor_xml import processar_xml
from processamento.classificador_fiscal import identificar_tipo_pdf
from processamento.normalizador import normalizar_resultado
from processamento.validador import validar_resultado
from processamento.avaliador import avaliar_extracao
from processamento.ia import completar_com_ia
from extratores.nfe_pdf import extrair_nfe_pdf
from extratores.nfse_pdf import extrair_nfse_pdf

VERSAO_EXTRACAO = 11

EXTENSOES = {'.xml', '.pdf', '.png', '.jpg', '.jpeg'}


def extrair_documento(arquivo):
    arquivo = Path(arquivo)
    meta = {'ocr_utilizado': False, 'metodo': 'xml'}
    texto = None
    if arquivo.suffix.lower() == '.xml':
        dados = processar_xml(arquivo)
    else:
        texto, status = ler_documento(arquivo, meta)
        if status != 'sucesso':
            raise ValueError(status)
        tipo = identificar_tipo_pdf(texto)
        extrator = {'nfe': extrair_nfe_pdf, 'nfse': extrair_nfse_pdf}.get(tipo)
        dados = extrator(texto) if extrator else None
        meta['metodo'] = 'ocr' if meta['ocr_utilizado'] else 'texto'
    return dados, texto, meta


def processar_documento(arquivo):
    dados, texto, meta = extrair_documento(arquivo)
    if dados is None:
        raise ValueError('documento_nao_fiscal_ou_layout_desconhecido')
    resultado = normalizar_resultado(dados)
    avaliacao = avaliar_extracao(resultado)
    resultado, ia = completar_com_ia(resultado, texto, avaliacao, arquivo)
    resultado = normalizar_resultado(resultado)
    resultado['validacoes'] = validar_resultado(resultado)
    resultado['avaliacao'] = avaliar_extracao(resultado)
    resultado['metadados'] = {**meta, 'ia': ia}
    return resultado
