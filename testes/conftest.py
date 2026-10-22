"""Fixtures construídas em memória, sem documentos de pessoas ou empresas reais."""
from pathlib import Path
import pymupdf
import pytest

TEXTO_NFSE = '''NFS-e - DOCUMENTO FICTICIO SEM VALIDADE FISCAL
Numero da nota: 42
Data de Emissao: 20/01/2026
DADOS DO PRESTADOR
CNPJ: 00.000.000/0000-00
Razao Social: Empresa Ficticia
DADOS DO TOMADOR
CPF: 000.000.000-00
Nome: Cliente Ficticio
VALORES
VALOR TOTAL DOS SERVICOS: R$ 100,00
VALOR LIQUIDO DA NFS-E: R$ 95,00
VALOR DO ISS: R$ 5,00
'''


@pytest.fixture(autouse=True)
def impedir_ia_externa(monkeypatch):
    monkeypatch.setenv('IA_HABILITADA', '0')
    def bloquear(*args, **kwargs):
        raise AssertionError('Chamadas externas proibidas na suíte de testes')
    monkeypatch.setattr('processamento.ia.urllib.request.urlopen', bloquear)


@pytest.fixture
def documento_ficticio(tmp_path):
    def criar(extensao, escaneado=False):
        caminho = tmp_path / f'ficticio.{extensao}'
        with pymupdf.open() as documento:
            pagina = documento.new_page()
            pagina.insert_text((40, 50), TEXTO_NFSE, fontsize=13, lineheight=1.7)
            if extensao == 'pdf' and not escaneado:
                documento.save(caminho)
            else:
                imagem = pagina.get_pixmap(dpi=180)
                if extensao == 'pdf':
                    with pymupdf.open() as digitalizado:
                        digitalizado.new_page().insert_image(pagina.rect, stream=imagem.tobytes('png'))
                        digitalizado.save(caminho)
                else:
                    imagem.pil_save(caminho)
        return caminho
    return criar
