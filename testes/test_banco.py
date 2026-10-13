from processamento.banco import Banco


def registro(identificador, chave='chave-ficticia'):
    return {'id': identificador, 'origem': 'ficticio.xml', 'status':'revisao_necessaria',
            'processado_em':'2026-01-01T00:00:00+00:00', 'duplicado':False,
            'dados':{'tipo':'nfse', 'numero_nota':'42', 'chave_acesso':chave,
                     'emitente':{'cnpj':'00.000.000/0000-00'}, 'valor_total':10}}


def test_persistencia_e_chave_unica(tmp_path):
    banco = Banco(tmp_path / 'notas.sqlite3')
    banco.salvar(registro('a'))
    assert banco.salvar(registro('b'))['duplicado']
    assert len(Banco(banco.caminho).listar()) == 1
    assert banco.obter('a')['dados']['numero_nota'] == '42'
    assert len(banco.listar(tipo='nfse', busca='000000')) == 1
    assert banco.listar(tipo='nfe') == []
    assert banco.listar(busca="' OR 1=1 --") == []


def test_sem_chave_nao_colide(tmp_path):
    banco = Banco(tmp_path / 'notas.sqlite3')
    banco.salvar(registro('a', None))
    banco.salvar(registro('b', None))
    assert len(banco.listar()) == 2
