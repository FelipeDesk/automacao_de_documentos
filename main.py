import json
from pathlib import Path
from extrator import extrair_cpfs, validar_cpf, extrair_cnpjs, validar_cnpj, extrair_datas, validar_data, extrair_valores
from leitor import ler_documento
from leitor_xml import processar_xml
from normalizador import normalizar_resultado
from validador import validar_resultado
from extrator_nfe_pdf import extrair_nfe_pdf
from classificador_fiscal import identificar_tipo_pdf

pasta_entrada = Path('entrada')
pasta_resultados = Path("resultados")

arquivos = pasta_entrada.iterdir()

def salvar_resultado(resultado, arquivo, pasta_resultados):
    nome_resultado = arquivo.stem + ".json"
    caminho_resultado = pasta_resultados / nome_resultado

    with open(
        caminho_resultado,
        "w",
        encoding="utf-8"
    ) as arquivo_json:
        json.dump(
            resultado,
            arquivo_json,
            indent=4,
            ensure_ascii=False
        )

for arquivo in arquivos:
    if not arquivo.is_file():
        continue

    if arquivo.suffix.lower() == ".pdf":
        texto, status = ler_documento(arquivo)

        if status != "sucesso":
            print(f"Não foi possível ler: {arquivo.name}")
            continue

        tipo = identificar_tipo_pdf(texto)

        if tipo == "desconhecido":
            print(
                f"Documento ignorado: {arquivo.name} "
                f"(não identificado como nota fiscal)"
            )
            continue

        if tipo == "nfe":
            resultado = extrair_nfe_pdf(texto)

            resultado = normalizar_resultado(resultado)

            validacoes = validar_resultado(resultado)
            resultado["validacoes"] = validacoes

            salvar_resultado(
                resultado,
                arquivo,
                pasta_resultados
            )

            print(f"{arquivo.name} processado com sucesso.")
            continue

    conteudo, status = ler_documento(arquivo)

    if status == "formato_nao_suportado":
        print(f"Formato não suportado: {arquivo.name}")
        continue

    if status == "ocr_necessario":
        print(f"OCR necessário: {arquivo.name}")
        continue

    if status == "ocr_falhou":
        print(f"OCR não conseguiu extrair texto: {arquivo.name}")
        continue

    if status == "texto_nao_encontrado":
        print(f"Texto não encontrado: {arquivo.name}")
        continue

    cpfs = extrair_cpfs(conteudo)
    cnpjs = extrair_cnpjs(conteudo)
    datas = extrair_datas(conteudo)
    valores = extrair_valores(conteudo)

    cpfs_encontrados = []
    cnpjs_encontrados = []
    datas_encontradas = []

    for cpf in cpfs:

        dados_cpf = {
            "numero": cpf,
            "valido": validar_cpf(cpf)
        }

        cpfs_encontrados.append(dados_cpf)

    for cnpj in cnpjs:
        dados_cnpj = {
            "numero": cnpj,
            "valido": validar_cnpj(cnpj)
        }

        cnpjs_encontrados.append(dados_cnpj)

    for data in datas:
        dados_data = {
            "valor": data,
            "valida": validar_data(data)
        }

        datas_encontradas.append(dados_data)

    resultado = {
        "arquivo": arquivo.name,
        "cpfs": cpfs_encontrados,
        "cnpjs": cnpjs_encontrados,
        "datas": datas_encontradas,
        "valores": valores
    }

    salvar_resultado(
        resultado,
        arquivo,
        pasta_resultados
    )

    print(f"Processado com sucesso: {arquivo.name}")