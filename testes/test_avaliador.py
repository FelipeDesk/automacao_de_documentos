from processamento.avaliador import avaliar_extracao


def test_extracao_completa():
    dados = {
        "numero_nota": "12345",
        "emitente": {"cnpj": "11222333000181"},
        "valor_total": 150.75,
    }

    resultado = avaliar_extracao(dados)

    assert resultado["status_extracao"] == "completo"
    assert resultado["campos_ausentes"] == []


def test_extracao_incompleta():
    dados = {
        "numero_nota": "12345",
        "emitente": {"cnpj": None},
        "valor_total": 150.75,
    }

    resultado = avaliar_extracao(dados)

    assert resultado["status_extracao"] == "revisao_necessaria"
    assert "emitente.cnpj" in resultado["campos_ausentes"]


def test_extracao_sem_emitente():
    dados = {
        "numero_nota": "12345",
        "emitente": None,
        "valor_total": 150.75,
    }

    resultado = avaliar_extracao(dados)

    assert resultado["status_extracao"] == "revisao_necessaria"


def test_valor_zero_nao_e_ausente():
    dados = {
        "numero_nota": "12345",
        "emitente": {"cnpj": "11222333000181"},
        "valor_total": 0,
    }

    resultado = avaliar_extracao(dados)

    assert "valor_total" not in resultado["campos_ausentes"]

def test_completo_mas_invalido_exige_revisao():
    resultado = avaliar_extracao({'numero_nota': '1', 'emitente': {'cnpj': '00000000000000'}, 'valor_total': 10})
    assert resultado['completude'] == 100
    assert resultado['validade'] == 0
    assert resultado['status_extracao'] == 'revisao_necessaria'
    assert not resultado['elegivel_ia']


def test_obrigatorios_por_tipo():
    resultado = avaliar_extracao({'tipo': 'nfe'})
    assert 'chave_acesso' in resultado['campos_ausentes']
    assert 'data_vencimento' not in resultado['campos_ausentes']
    assert resultado['elegivel_ia']
