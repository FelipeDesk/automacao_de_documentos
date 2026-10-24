"""Configuração local do backend, independente do diretório de execução."""
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]


def carregar_configuracoes():
    """Lê o .env da raiz; variáveis explícitas do ambiente têm prioridade."""
    return load_dotenv(BASE_DIR / '.env', override=False, encoding='utf-8-sig')
