import json
from pathlib import Path

from leitor import ler_documento
from leitor_xml import processar_xml
from classificador_fiscal import identificar_tipo_pdf
from extrator_nfe_pdf import extrair_nfe_pdf
from extrator_nfse_pdf import extrair_nfse_pdf
from normalizador import normalizar_resultado
from validador import validar_resultado


BASE_DIR = Path(__file__).resolve().parent
PASTA_ENTRADA = BASE_DIR / "entrada"
PASTA_RESULTADOS = BASE_DIR / "resultados"


def salvar_resultado(resultado, arquivo):
    PASTA_RESULTADOS.mkdir(exist_ok=True)

    nome = f"{arquivo.stem}_{arquivo.suffix[1:].lower()}.json"
    caminho = PASTA_RESULTADOS / nome

    with open(caminho, "w", encoding="utf-8") as arquivo_json:
        json.dump(
            resultado,
            arquivo_json,
            indent=4,
            ensure_ascii=False
        )


def dados_minimos_presentes(resultado):
    emitente = resultado.get("emitente") or {}

    return (
        bool(resultado.get("numero_nota"))
        and bool(emitente.get("cnpj"))
        and resultado.get("valor_total") is not None
    )


def extrair_dados(arquivo):
    extensao = arquivo.suffix.lower()

    if extensao == ".xml":
        return processar_xml(arquivo)

    if extensao == ".pdf":
        texto, status = ler_documento(arquivo)

        if status != "sucesso":
            print(f"Não foi possível ler: {arquivo.name}")
            return None

        tipo = identificar_tipo_pdf(texto)

        if tipo == "nfe":
            return extrair_nfe_pdf(texto)

        if tipo == "nfse":
            return extrair_nfse_pdf(texto)

    return None


def processar_arquivo(arquivo):
    if arquivo.suffix.lower() not in {".xml", ".pdf"}:
        print(f"Formato ignorado: {arquivo.name}")
        return

    try:
        resultado = extrair_dados(arquivo)

        if resultado is None:
            print(f"Documento não reconhecido: {arquivo.name}")
            return

        resultado = normalizar_resultado(resultado)

        if not dados_minimos_presentes(resultado):
            print(f"Dados fiscais insuficientes: {arquivo.name}")
            return

        resultado["validacoes"] = validar_resultado(resultado)

        salvar_resultado(resultado, arquivo)

        print(f"Processado com sucesso: {arquivo.name}")

    except Exception as erro:
        print(f"Erro ao processar {arquivo.name}: {erro}")


def main():
    if not PASTA_ENTRADA.exists():
        print("Pasta de entrada não encontrada.")
        return

    for arquivo in sorted(PASTA_ENTRADA.iterdir()):
        if arquivo.is_file():
            processar_arquivo(arquivo)


if __name__ == "__main__":
    main()