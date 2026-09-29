from pathlib import Path
from extrator import extrair_cpf

pasta_entrada = Path('entrada')
arquivos = pasta_entrada.glob('*.txt')

for arquivo in arquivos:
    conteudo = arquivo.read_text(encoding='utf-8')

    cpf = extrair_cpf(conteudo)

    if cpf:
        print(f'CPF encontrado: {cpf}')
    else:
        print('Nenhum CPF encontrado.')