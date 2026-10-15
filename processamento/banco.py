"""Persistência SQLite sem ORM; JSON preserva todos os campos normalizados."""
from contextlib import contextmanager
import json
import re
import sqlite3
from pathlib import Path


class Banco:
    def __init__(self, caminho):
        self.caminho = Path(caminho)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        with self.conectar() as conexao:
            conexao.execute('''CREATE TABLE IF NOT EXISTS notas (
                id TEXT PRIMARY KEY, chave_fiscal TEXT UNIQUE, tipo TEXT, numero_nota TEXT,
                cnpj_emitente TEXT, data_emissao TEXT, valor_total REAL, origem TEXT NOT NULL,
                metodo TEXT, status TEXT NOT NULL, processado_em TEXT NOT NULL, registro TEXT NOT NULL)''')

            conexao.execute('CREATE TABLE IF NOT EXISTS arquivos (hash TEXT PRIMARY KEY, nota_id TEXT NOT NULL REFERENCES notas(id))')
            conexao.execute('INSERT OR IGNORE INTO arquivos SELECT id, id FROM notas')

    @contextmanager
    def conectar(self):
        conexao = sqlite3.connect(self.caminho, timeout=30)
        conexao.row_factory = sqlite3.Row
        try:
            with conexao:
                yield conexao
        finally:
            conexao.close()

    def obter(self, identificador):
        with self.conectar() as conexao:
            linha = conexao.execute('SELECT registro FROM notas WHERE id = (SELECT nota_id FROM arquivos WHERE hash = ?)', (identificador,)).fetchone()
        return json.loads(linha['registro']) if linha else None

    def listar(self, tipo=None, busca='', limite=100, deslocamento=0):
        sql, parametros = 'SELECT registro FROM notas WHERE 1=1', []
        if tipo:
            sql += ' AND tipo = ?'
            parametros.append(tipo)
        if busca:
            sql += ' AND (numero_nota LIKE ? OR cnpj_emitente LIKE ?)'
            busca_cnpj = re.sub(r"\D", "", busca) or busca
            parametros.extend([f"%{busca}%", f"%{busca_cnpj}%"])
        sql += ' ORDER BY processado_em DESC, id LIMIT ? OFFSET ?'
        parametros.extend([limite, deslocamento])
        with self.conectar() as conexao:
            return [json.loads(linha['registro']) for linha in conexao.execute(sql, parametros)]

    def salvar(self, registro, atualizar=False):
        dados = registro.get('dados') or {}
        chave = dados.get('chave_acesso')
        # Chaves NF-e inválidas não são identidades confiáveis.
        if dados.get('tipo') == 'nfe' and not dados.get('validacoes', {}).get('chave_acesso'):
            chave = None
        fiscal = f"{dados.get('tipo')}:{chave}" if chave else None
        cnpj = re.sub(r'\D', '', (dados.get('emitente') or {}).get('cnpj') or '')
        with self.conectar() as conexao:
            conexao.execute('BEGIN IMMEDIATE')
            existente = conexao.execute('SELECT registro FROM notas WHERE id = ? OR chave_fiscal = ?', (registro['id'], fiscal)).fetchone()
            if existente:
                original = json.loads(existente['registro'])
                if atualizar and original['id'] == registro['id']:
                    conexao.execute('''UPDATE notas SET chave_fiscal=?, tipo=?, numero_nota=?,
                        cnpj_emitente=?, data_emissao=?, valor_total=?, origem=?, metodo=?, status=?,
                        processado_em=?, registro=? WHERE id=?''',
                        (fiscal, dados.get('tipo'), dados.get('numero_nota'), cnpj,
                         dados.get('data_emissao'), dados.get('valor_total'), registro['origem'],
                         dados.get('metadados', {}).get('metodo'), registro['status'], registro['processado_em'],
                         json.dumps(registro, ensure_ascii=False, allow_nan=False), registro['id']))
                    return registro
                conexao.execute('INSERT OR IGNORE INTO arquivos VALUES (?, ?)', (registro['id'], original['id']))
                return {**original, 'duplicado': True}
            conexao.execute('INSERT INTO notas VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (registro['id'], fiscal, dados.get('tipo'), dados.get('numero_nota'), cnpj,
                 dados.get('data_emissao'), dados.get('valor_total'), registro['origem'],
                 dados.get('metadados', {}).get('metodo'), registro['status'], registro['processado_em'],
                 json.dumps(registro, ensure_ascii=False, allow_nan=False)))
            conexao.execute('INSERT INTO arquivos VALUES (?, ?)', (registro['id'], registro['id']))
        return registro

    def excluir(self, identificador):
        """Remove a nota e todos os hashes de duplicatas na mesma transação."""
        with self.conectar() as conexao:
            conexao.execute('BEGIN IMMEDIATE')
            linha = conexao.execute('SELECT nota_id FROM arquivos WHERE hash = ?', (identificador,)).fetchone()
            if not linha:
                return None
            nota_id = linha['nota_id']
            hashes = [r['hash'] for r in conexao.execute('SELECT hash FROM arquivos WHERE nota_id = ?', (nota_id,))]
            conexao.execute('DELETE FROM arquivos WHERE nota_id = ?', (nota_id,))
            conexao.execute('DELETE FROM notas WHERE id = ?', (nota_id,))
            return hashes
