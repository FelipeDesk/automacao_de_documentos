from pathlib import Path
from extrator import extrair_cpfs, validar_cpf

pasta_entrada = Path('entrada')
arquivos = pasta_entrada.glob('*.txt')

for arquivo in arquivos:
    conteudo = arquivo.read_text(encoding='utf-8')

    cpfs = extrair_cpfs(conteudo)

    print(f"\nArquivo: {arquivo.name}")

    if cpfs:
        
        for cpf in cpfs:
            if validar_cpf(cpf):
                print(f"CPF válido: {cpf}")
            else:
                print(f"CPF inválido: {cpf}")
    else:
        print('Nenhum CPF encontrado.')