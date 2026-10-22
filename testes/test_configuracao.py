"""Verifica a configuração na inicialização sem usar credenciais locais."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from processamento import configuracao


@pytest.mark.parametrize('modulo', ['api', 'main'])
def test_inicio_carrega_env_da_raiz_fora_do_diretorio(tmp_path, modulo):
    origem = Path(__file__).resolve().parents[1]
    projeto = tmp_path / 'projeto'
    projeto.mkdir()
    for pasta in ('processamento', 'extratores'):
        shutil.copytree(origem / pasta, projeto / pasta,
                        ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(origem / f'{modulo}.py', projeto / f'{modulo}.py')
    (projeto / '.env').write_text(
        'GEMINI_API_KEY="chave-ficticia"\nUPLOADS_POR_MINUTO=7\n'
        'DADOS_DIR="C:/dados com espacos"\n', encoding='utf-8-sig')
    ambiente = {k: v for k, v in os.environ.items()
                if k not in {'GEMINI_API_KEY', 'UPLOADS_POR_MINUTO', 'DADOS_DIR',
                             'PYTHON_DOTENV_DISABLED'}}
    ambiente['PYTHONPATH'] = str(projeto)
    resultado = subprocess.run(
        [sys.executable, '-c',
         f'import {modulo}; import os, json; '
         'print(json.dumps([os.getenv(k) for k in '
         '["GEMINI_API_KEY", "UPLOADS_POR_MINUTO", "DADOS_DIR"]]))'],
        cwd=tmp_path, env=ambiente, capture_output=True, text=True,
        check=True, timeout=30)
    assert json.loads(resultado.stdout) == ['chave-ficticia', '7', 'C:/dados com espacos']


def test_env_preserva_variaveis_explicitas(tmp_path, monkeypatch):
    (tmp_path / '.env').write_text('GEMINI_API_KEY=arquivo\n', encoding='utf-8')
    monkeypatch.setattr(configuracao, 'BASE_DIR', tmp_path)
    monkeypatch.setenv('GEMINI_API_KEY', 'ambiente')
    configuracao.carregar_configuracoes()
    assert os.environ['GEMINI_API_KEY'] == 'ambiente'


def test_env_ausente_permite_inicializacao(tmp_path, monkeypatch):
    monkeypatch.setattr(configuracao, 'BASE_DIR', tmp_path)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    assert not configuracao.carregar_configuracoes()
    assert 'GEMINI_API_KEY' not in os.environ
