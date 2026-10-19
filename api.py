"""API pública: cada upload é processado e descartado na própria requisição."""
import os
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore, Lock
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, UploadFile

from processamento.pipeline import EXTENSOES, processar_documento

MAX_UPLOAD = 20 * 1024 * 1024
ASSINATURAS = {
    '.pdf': b'%PDF-', '.png': b'\x89PNG\r\n\x1a\n',
    '.jpg': b'\xff\xd8', '.jpeg': b'\xff\xd8',
}
TIPOS = {
    '.xml': {'application/xml', 'text/xml'},
    '.pdf': {'application/pdf'},
    '.png': {'image/png'},
    '.jpg': {'image/jpeg'}, '.jpeg': {'image/jpeg'},
}


class LimiteUploads:
    """Conta apenas requisições por IP; nunca guarda documentos nem resultados."""

    def __init__(self, por_minuto):
        self.por_minuto = por_minuto
        self.eventos = {}
        self.trava = Lock()

    def aceitar(self, cliente):
        agora = time.monotonic()
        with self.trava:
            for endereco, eventos in list(self.eventos.items()):
                while eventos and eventos[0] <= agora - 60:
                    eventos.popleft()
                if not eventos:
                    del self.eventos[endereco]
            eventos = self.eventos.setdefault(cliente, deque())
            if len(eventos) >= self.por_minuto:
                return False
            eventos.append(agora)
            return True


def _validar(conteudo, extensao, tipo):
    if len(conteudo) > MAX_UPLOAD:
        raise HTTPException(413, 'Arquivo excede 20 MB')
    if not conteudo:
        raise HTTPException(400, 'Arquivo vazio')
    # Alguns navegadores enviam octet-stream quando não reconhecem XML.
    tipo = (tipo or '').split(';', 1)[0].strip().lower()
    if tipo and tipo not in TIPOS[extensao] | {'application/octet-stream'}:
        raise HTTPException(415, 'Tipo MIME incompatível com a extensão')
    if extensao in ASSINATURAS and not conteudo.startswith(ASSINATURAS[extensao]):
        raise HTTPException(415, 'Conteúdo incompatível com a extensão')
    if extensao == '.xml':
        inicio = conteudo.removeprefix(b'\xef\xbb\xbf').lstrip()
        if not inicio.startswith(b'<'):
            raise HTTPException(415, 'Conteúdo incompatível com XML')
        if b'<!DOCTYPE' in conteudo.upper() or b'<!ENTITY' in conteudo.upper():
            raise HTTPException(400, 'Declarações DTD e entidades não são permitidas')


def criar_app(temporarios_dir=None, *, requisicoes_por_minuto=None, simultaneos=None):
    """O diretório opcional serve para testar a limpeza; produção usa o temp do SO."""
    if requisicoes_por_minuto is None:
        requisicoes_por_minuto = max(1, int(os.getenv('UPLOADS_POR_MINUTO', '10')))
    if simultaneos is None:
        simultaneos = max(1, int(os.getenv('UPLOADS_SIMULTANEOS', '2')))
    app = FastAPI(title='Extração temporária de notas fiscais', version='2.0.0')
    limite = LimiteUploads(requisicoes_por_minuto)
    vagas = BoundedSemaphore(simultaneos)

    @app.middleware('http')
    async def impedir_cache(request: Request, call_next):
        resposta = await call_next(request)
        if request.url.path.startswith('/api/'):
            resposta.headers['Cache-Control'] = 'no-store'
            resposta.headers['X-Content-Type-Options'] = 'nosniff'
        return resposta

    @app.post('/api/upload')
    def upload(request: Request, arquivo: UploadFile):
        reservou_vaga = False
        try:
            # Não aceitar cabeçalhos de IP informados pelo próprio cliente.
            cliente = request.client.host if request.client else 'desconhecido'
            if not limite.aceitar(cliente):
                raise HTTPException(429, 'Limite de uploads por minuto excedido', headers={'Retry-After': '60'})
            reservou_vaga = vagas.acquire(blocking=False)
            if not reservou_vaga:
                raise HTTPException(429, 'Muitos documentos em processamento', headers={'Retry-After': '5'})
            nome = Path((arquivo.filename or '').replace('\\', '/')).name
            extensao = Path(nome).suffix.lower()
            if extensao not in EXTENSOES:
                raise HTTPException(415, 'Formato permitido: XML, PDF, JPG, JPEG ou PNG')
            conteudo = arquivo.file.read(MAX_UPLOAD + 1)
            _validar(conteudo, extensao, arquivo.content_type)
            registro = {
                'id': uuid4().hex,
                'origem': nome,
                'status': 'erro',
                'dados': None,
                'erro': None,
                'processado_em': datetime.now(timezone.utc).isoformat(),
            }
            try:
                with TemporaryDirectory(prefix='nota-', dir=temporarios_dir) as temporario:
                    caminho = Path(temporario) / f'documento{extensao}'
                    caminho.write_bytes(conteudo)
                    dados = processar_documento(caminho)
                registro['dados'] = dados
                registro['status'] = ('sucesso' if dados['avaliacao']['status_extracao'] == 'completo'
                                      else 'revisao_necessaria')
            except Exception as erro:
                registro['erro'] = (f'Falha de leitura ou extração ({type(erro).__name__}). '
                                    'Verifique formato, integridade, layout e configuração de OCR.')
            return registro
        finally:
            arquivo.file.close()
            if reservou_vaga:
                vagas.release()

    return app


app = criar_app()
