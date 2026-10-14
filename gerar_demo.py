"""Gera arquivos de demonstração sintéticos (nenhum dado fiscal real)."""
import argparse
from pathlib import Path
from testes.dados_ficticios import gerar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saida', type=Path, default=Path('exemplos'))
    args = parser.parse_args()
    gerar(args.saida, incluir_imagens=True)


if __name__ == '__main__':
    main()
