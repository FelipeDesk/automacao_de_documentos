"""Organização local, exportação e isolamento de falhas por documento."""
import csv
import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from processamento.pipeline import EXTENSOES, processar_documento
from processamento.banco import Banco

logger = logging.getLogger(__name__)


def gravar_json(caminho, dados):
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix('.tmp')
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporario.replace(caminho)


def ler_registros(base):
    return Banco(Path(base) / 'notas.sqlite3').listar(limite=-1)


def celula_segura(valor):
    if isinstance(valor, str) and valor.lstrip().startswith(('=', '+', '-', '@')):
        return "'" + valor
    return valor


def exportar_csv(base):
    destino = Path(base) / 'resultados' / 'notas.csv'
    destino.parent.mkdir(parents=True, exist_ok=True)
    campos = ['id', 'tipo', 'numero_nota', 'cnpj_emitente', 'documento_destinatario', 'data_emissao',
              'data_vencimento', 'valor_total', 'valor_liquido', 'valor_iss', 'status', 'metodo', 'ia_utilizada']
    temporario = destino.with_suffix('.tmp')
    with temporario.open('w', newline='', encoding='utf-8-sig') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, delimiter=';')
        escritor.writeheader()
        for registro in ler_registros(base):
            dados = registro.get('dados')
            if not dados:
                continue
            linha = {campo: dados.get(campo) for campo in campos}
            linha.update(id=registro['id'], status=registro['status'],
                         cnpj_emitente=dados['emitente']['cnpj'], documento_destinatario=dados['destinatario']['cnpj_cpf'],
                         metodo=dados['metadados']['metodo'], ia_utilizada=dados['metadados']['ia']['utilizada'])
            escritor.writerow({k: celula_segura(v) for k, v in linha.items()})
    temporario.replace(destino)


def processar_recebido(arquivo, base):
    arquivo, base = Path(arquivo), Path(base)
    digest = hashlib.sha256(arquivo.read_bytes()).hexdigest()
    destino = base / 'resultados' / 'registros' / f'{digest}.json'
    banco = Banco(base / 'notas.sqlite3')
    existente = banco.obter(digest)
    if existente:
        gravar_json(destino, existente)
        exportar_csv(base)
        return {**existente, 'duplicado': True}
    registro = {'id': digest, 'origem': arquivo.name, 'status': 'erro', 'dados': None,
                'erro': None, 'processado_em': datetime.now(timezone.utc).isoformat(), 'duplicado': False}
    try:
        if arquivo.suffix.lower() not in EXTENSOES:
            raise ValueError('formato_nao_suportado')
        dados = processar_documento(arquivo)
        registro['dados'] = dados
        registro['status'] = 'sucesso' if dados['avaliacao']['status_extracao'] == 'completo' else 'revisao_necessaria'
    except Exception as erro:
        registro['erro'] = f'Falha de leitura ou extração ({type(erro).__name__}). Verifique formato, integridade, layout e configuração de OCR.'
    registro = banco.salvar(registro)
    destino = base / 'resultados' / 'registros' / f"{registro['id']}.json"
    gravar_json(destino, registro)
    exportar_csv(base)
    logger.info('documento=%s metodo=%s status=%s', digest[:12], (registro['dados'] or {}).get('metadados', {}).get('metodo', 'indisponivel'), registro['status'])
    return registro


def processar_lote(base):
    base = Path(base)
    for nome in ('entrada', 'processados', 'erros', 'revisao', 'resultados'):
        (base / nome).mkdir(parents=True, exist_ok=True)
    resumo = dict(sucesso=0, erro=0, revisao_necessaria=0, duplicado=0)
    for arquivo in sorted((base / 'entrada').iterdir()):
        if not arquivo.is_file():
            continue
        try:
            registro = processar_recebido(arquivo, base)
            chave = 'duplicado' if registro['duplicado'] else registro['status']
            pasta = {'sucesso': 'processados', 'erro': 'erros', 'revisao_necessaria': 'revisao'}[registro['status']]
            destino = base / pasta / f"{registro['id']}{arquivo.suffix.lower()}"
            if destino.exists():
                # Preserva cada entrada duplicada sem sobrescrever documentos.
                pasta_duplicados = base / 'duplicados'
                pasta_duplicados.mkdir(exist_ok=True)
                from uuid import uuid4
                destino = pasta_duplicados / f'{uuid4().hex}{arquivo.suffix.lower()}'
            shutil.move(str(arquivo), str(destino))
            resumo[chave] += 1
        except Exception as erro:
            resumo['erro'] += 1
            logger.error('falha_operacional=%s; arquivo preservado na entrada', type(erro).__name__)
    gravar_json(base / 'resultados' / 'resumo.json', resumo)
    logger.info('resumo=%s', resumo)
    return resumo
