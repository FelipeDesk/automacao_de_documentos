"""Entrada CLI e funções de compatibilidade com o projeto original."""
import logging
import os
from pathlib import Path
from processamento.pipeline import extrair_documento, processar_documento
from processamento.lote import gravar_json, processar_lote

BASE_DIR = Path(__file__).resolve().parent
PASTA_ENTRADA = BASE_DIR / 'entrada'
PASTA_RESULTADOS = BASE_DIR / 'resultados'
logger = logging.getLogger(__name__)


def salvar_resultado(resultado, arquivo):
    gravar_json(PASTA_RESULTADOS / f'{arquivo.stem}_{arquivo.suffix[1:].lower()}.json', resultado)


def extrair_dados(arquivo):
    return extrair_documento(arquivo)[0]


def processar_arquivo(arquivo):
    # Compatibilidade: extração individual não move o arquivo de origem.
    try:
        resultado = processar_documento(arquivo)
        salvar_resultado(resultado, arquivo)
        return resultado
    except Exception as erro:
        logger.error('falha_extracao=%s', type(erro).__name__)
        return None


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    return processar_lote(Path(os.getenv('DADOS_DIR', str(BASE_DIR))))


if __name__ == '__main__':
    main()
