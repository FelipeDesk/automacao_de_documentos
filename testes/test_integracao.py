from pathlib import Path
import json

from main import salvar_resultado
from main import extrair_dados
from processamento.normalizador import normalizar_resultado
from processamento.validador import validar_resultado


FIXTURES = Path(__file__).parent / "fixtures"


def test_processamento_completo_nfe_xml():
    caminho = FIXTURES / "nfe_teste.xml"

    # 1. Extrai os dados do documento
    dados = extrair_dados(caminho)

    assert dados is not None

    # 2. Normaliza os dados
    resultado = normalizar_resultado(dados)

    # 3. Valida os dados
    resultado["validacoes"] = validar_resultado(resultado)

    # 4. Verifica o resultado final
    assert resultado["tipo"] == "nfe"
    assert resultado["numero_nota"]
    assert resultado["emitente"]["cnpj"]
    assert isinstance(resultado["valor_total"], (int, float))
    assert isinstance(resultado["validacoes"], dict)


def test_salvar_resultado_json(tmp_path, monkeypatch):
    # Dados fictícios para o teste
    dados = {
        "tipo": "nfe",
        "numero_nota": "12345",
        "valor_total": 150.75
    }

    # Simula um arquivo de entrada
    arquivo = Path("nota_teste.xml")

    # Redireciona a pasta de resultados para uma pasta temporária
    monkeypatch.setattr("main.PASTA_RESULTADOS", tmp_path)

    # Executa a função real do projeto
    salvar_resultado(dados, arquivo)

    # Caminho esperado do JSON gerado
    caminho_json = tmp_path / "nota_teste_xml.json"

    # Verifica se o arquivo foi criado
    assert caminho_json.exists()

    # Lê o conteúdo do arquivo
    with open(caminho_json, "r", encoding="utf-8") as arquivo_json:
        resultado = json.load(arquivo_json)

    # Verifica se os dados foram salvos corretamente
    assert resultado["tipo"] == "nfe"
    assert resultado["numero_nota"] == "12345"
    assert resultado["valor_total"] == 150.75

import json

from main import processar_arquivo


def test_processar_arquivo_com_avaliacao(tmp_path, monkeypatch):
    # Redireciona os resultados para uma pasta temporária
    monkeypatch.setattr("main.PASTA_RESULTADOS", tmp_path)

    # Utiliza nosso XML fictício de teste
    caminho = FIXTURES / "nfe_teste.xml"

    # Executa o fluxo principal
    processar_arquivo(caminho)

    # Verifica se o JSON foi gerado
    caminho_json = tmp_path / "nfe_teste_xml.json"

    assert caminho_json.exists()

    # Lê o resultado salvo
    with open(caminho_json, "r", encoding="utf-8") as arquivo:
        resultado = json.load(arquivo)

    # Verifica se o diagnóstico foi incluído
    assert "validacoes" in resultado
    assert "avaliacao" in resultado

    assert resultado["avaliacao"]["status_extracao"] in (
        "completo",
        "revisao_necessaria",
    )

    assert isinstance(
        resultado["avaliacao"]["campos_ausentes"], list
    )