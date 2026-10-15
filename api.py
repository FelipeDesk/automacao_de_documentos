"""API local síncrona: a resposta do upload já contém o resultado do processamento."""
import logging
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, UploadFile
from processamento.banco import Banco
from processamento.lote import processar_recebido, exportar_csv
from processamento.pipeline import EXTENSOES

MAX_UPLOAD = 20 * 1024 * 1024


def criar_app(base=None):
    base = Path(base or os.getenv('DADOS_DIR', Path(__file__).resolve().parent))
    app = FastAPI(title='Notas fiscais locais', version='1.0.0')
    trava = Lock()

    @app.get('/api/notas')
    def listar_notas(tipo: Literal['nfe', 'nfse'] | None = None, busca: str = '',
                     limite: int = Query(100, ge=1, le=500), deslocamento: int = Query(0, ge=0)):
        return Banco(base / 'notas.sqlite3').listar(tipo, busca, limite, deslocamento)

    @app.get('/api/notas/{identificador}')
    def consultar_nota(identificador: str):
        registro = Banco(base / 'notas.sqlite3').obter(identificador)
        if registro is None:
            raise HTTPException(404, 'Nota não encontrada')
        return registro

    @app.get('/api/processamentos/{identificador}')
    def consultar_status(identificador: str):
        registro = consultar_nota(identificador)
        return {k: registro.get(k) for k in ('id', 'status', 'erro', 'processado_em')}

    @app.delete('/api/notas/{identificador}')
    def excluir_nota(identificador: str):
        with trava:
            hashes = Banco(base / 'notas.sqlite3').excluir(identificador)
            if hashes is None:
                raise HTTPException(404, 'Nota não encontrada')
            pasta = (base / 'resultados' / 'registros').resolve()
            for digest in hashes:
                caminho = (pasta / f'{digest}.json').resolve()
                if caminho.parent == pasta:
                    caminho.unlink(missing_ok=True)
            exportar_csv(base)
        return {'excluida': True}

    @app.post('/api/upload')
    def upload(arquivo: UploadFile):
        nome = Path((arquivo.filename or '').replace('\\', '/')).name
        extensao = Path(nome).suffix.lower()
        try:
            if extensao not in EXTENSOES:
                raise HTTPException(415, 'Formato permitido: XML, PDF, JPG, JPEG ou PNG')
            conteudo = arquivo.file.read(MAX_UPLOAD + 1)
            if len(conteudo) > MAX_UPLOAD:
                raise HTTPException(413, 'Arquivo excede 20 MB')
            if not conteudo:
                raise HTTPException(400, 'Arquivo vazio')
            assinatura = {'.pdf': b'%PDF-', '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8', '.jpeg': b'\xff\xd8'}
            if extensao in assinatura and not conteudo.startswith(assinatura[extensao]):
                raise HTTPException(415, 'Conteúdo incompatível com a extensão')
            if extensao == '.xml' and (b'<!DOCTYPE' in conteudo.upper() or b'<!ENTITY' in conteudo.upper()):
                raise HTTPException(400, 'Declarações DTD e entidades não são permitidas')
            uploads = base / 'uploads'
            uploads.mkdir(parents=True, exist_ok=True)
            with trava, TemporaryDirectory(dir=uploads) as temporario:
                caminho = Path(temporario) / nome
                caminho.write_bytes(conteudo)
                registro = processar_recebido(caminho, base)
                pasta = {'sucesso':'processados', 'revisao_necessaria':'revisao', 'erro':'erros'}[registro['status']]
                destino = base / pasta / f"{registro['id']}{extensao}"
                if destino.exists():
                    destino = base / 'duplicados' / f'{uuid4().hex}{extensao}'
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(caminho), str(destino))
                return registro
        finally:
            arquivo.file.close()

    return app


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
app = criar_app()
