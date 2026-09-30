import json
from pathlib import Path
from extrator import extrair_cpfs, validar_cpf
from leitor import ler_documento

pasta_entrada = Path('entrada')
pasta_resultados = Path("resultados")

arquivos = pasta_entrada.iterdir()

for arquivo in arquivos:
    if not arquivo.is_file():
        continue

    conteudo = ler_documento(arquivo)

    if conteudo is None:
        print(f"Formato não suportado: {arquivo.name}")
        continue

    cpfs = extrair_cpfs(conteudo)

    cpfs_encontrados = []

    for cpf in cpfs:

        dados_cpf = {
            "numero": cpf,
            "valido": validar_cpf(cpf)
        }

        cpfs_encontrados.append(dados_cpf)

    resultado = {
        "arquivo": arquivo.name,
        "cpfs": cpfs_encontrados
    }

    nome_resultado = arquivo.stem + ".json"
    caminho_resultado = pasta_resultados / nome_resultado

    with open(caminho_resultado, "w", encoding="utf-8") as arquivo_json:

        json.dump(
            resultado,
            arquivo_json,
            indent=4,
            ensure_ascii=False
        )

    print(f"{arquivo.name} processado com sucesso.")