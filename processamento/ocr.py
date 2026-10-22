import os
import re
import shutil
from pathlib import Path
from io import BytesIO

import pymupdf
import pytesseract
from PIL import Image, ImageOps

from processamento.validador import validar_chave_acesso, validar_cnpj, validar_documento


def preparar_imagem(imagem):
    imagem = ImageOps.autocontrast(ImageOps.grayscale(ImageOps.exif_transpose(imagem)))
    if imagem.width < 2400:
        escala = 2 if imagem.width >= 1200 else min(3, 2400 / imagem.width)
        imagem = imagem.resize((int(imagem.width * escala), int(imagem.height * escala)), Image.Resampling.BICUBIC)
    # Limiar fixo apagava texto fino e números em fotos com sombra.
    return imagem


def configurar_tesseract():
    comando = os.getenv('TESSERACT_CMD') or shutil.which('tesseract')
    if not comando and os.name == 'nt':
        for raiz in (os.getenv('ProgramFiles'), os.getenv('LOCALAPPDATA')):
            if raiz:
                candidato = Path(raiz) / 'Tesseract-OCR' / 'tesseract.exe'
                if candidato.is_file():
                    comando = str(candidato)
                    break
    if comando:
        pytesseract.pytesseract.tesseract_cmd = comando


def remover_grade(imagem):
    """Remove traços longos em uma cópia; mantém o original para reler o cabeçalho."""
    cinza = ImageOps.grayscale(ImageOps.exif_transpose(imagem))
    largura, altura = cinza.size
    origem = cinza.tobytes()
    destino = bytearray(origem)
    horizontais = 0
    for vertical in (False, True):
        comprimento, faixas = (altura, largura) if vertical else (largura, altura)
        minimo = max(30, int(altura * .04)) if vertical else max(60, int(largura * .08))
        for faixa in range(faixas):
            inicio = None
            for pos in range(comprimento + 1):
                indice = pos * largura + faixa if vertical else faixa * largura + pos
                escuro = pos < comprimento and origem[indice] < 100
                if escuro and inicio is None:
                    inicio = pos
                if not escuro and inicio is not None:
                    if pos - inicio >= minimo:
                        horizontais += not vertical
                        for ponto in range(inicio, pos):
                            destino[ponto * largura + faixa if vertical else faixa * largura + ponto] = 255
                    inicio = None
        # Sem evidência de uma grade, evita processamento adicional em fotos.
        if not vertical and horizontais < 4:
            return None
    return Image.frombytes('L', cinza.size, bytes(destino))


def refinar_campos_danfe(imagem, texto):
    """Relê as células do cabeçalho a partir dos rótulos e das linhas do DANFE."""
    dados = pytesseract.image_to_data(imagem, lang=os.getenv('OCR_LANG', 'por'),
                                     config='--psm 3', output_type=pytesseract.Output.DICT)
    palavras = [i for i, t in enumerate(dados['text']) if t.strip()]
    complementos = []
    for rotulo in ('VALOR TOTAL DA NOTA', 'CHAVE DE ACESSO'):
        tokens = rotulo.split()
        for pos in range(len(palavras) - len(tokens) + 1):
            indices = palavras[pos:pos + len(tokens)]
            if [dados['text'][i].upper() for i in indices] != tokens:
                continue
            altura = max(dados['height'][i] for i in indices)
            topo = min(dados['top'][i] for i in indices)
            if max(dados['top'][i] for i in indices) - topo > altura:
                continue
            esquerda = min(dados['left'][i] for i in indices)
            direita = max(dados['left'][i] + dados['width'][i] for i in indices)
            fim = imagem.width if rotulo == 'CHAVE DE ACESSO' else min(imagem.width, direita + (direita - esquerda) * .6)
            # A primeira dezena da chave pode começar à esquerda do rótulo.
            margem = max(12, int(imagem.width * .03)) if rotulo == 'CHAVE DE ACESSO' else 12
            recorte = imagem.crop((max(0, esquerda - margem), max(0, topo - 15), int(fim),
                                   min(imagem.height, topo + altura * 6)))
            valores = []
            for modo in (6, 11):
                leitura = pytesseract.image_to_string(recorte, lang=os.getenv('OCR_LANG', 'por'), config=f'--psm {modo}')
                if rotulo == 'CHAVE DE ACESSO':
                    candidatos = re.findall(r'(?<!\d)(?:\d[ \t]*){44}(?!\d)', leitura)
                    valores.extend(c for v in candidatos if validar_chave_acesso(c := re.sub(r'\D', '', v)))
                else:
                    valores.extend(re.findall(r'\b\d[\d.]*,\d{2}(?!\d)', leitura))
            if len(set(valores)) == 1:
                complementos.append(f'{rotulo}: {valores[0]}')
    titulo_dest = next((i for i in palavras if re.match(r'DESTINAT', dados['text'][i], re.I)), None)
    if titulo_dest is not None:
        y_dest = dados['top'][titulo_dest]
        x_dest = dados['left'][titulo_dest]
        # A linha do emitente fica imediatamente acima do título do destinatário.
        faixa_emitente = imagem.crop((int(imagem.width * .58), max(0, y_dest - int(imagem.height * .08)),
                                      imagem.width, max(0, y_dest - 8)))
        leitura_emitente = pytesseract.image_to_string(faixa_emitente, lang=os.getenv('OCR_LANG', 'por'), config='--psm 6')
        cnpjs = {v.replace(' ', '') for v in re.findall(
            r'(?<!\d)\d{2}\.\d{3}\.\d{3}/\d{4}-\d\s?\d(?!\d)', leitura_emitente)
            if validar_cnpj(v)}
        if len(cnpjs) == 1:
            complementos.append(f'CNPJ EMITENTE: {next(iter(cnpjs))}')

        # Os três campos compartilham a mesma linha física; o OCR integral
        # frequentemente entrelaça os valores de colunas diferentes.
        y_inicio = y_dest + max(5, int(imagem.height * .01))
        y_fim = min(imagem.height, y_dest + int(imagem.height * .055))
        rotulo_doc = next((i for i in palavras if re.search(r'CNPJ.?CPF', dados['text'][i], re.I)
                           and y_dest <= dados['top'][i] < y_fim), None)
        rotulo_data = next((i for i in palavras if dados['text'][i].upper() == 'DATA'
                            and y_dest <= dados['top'][i] < y_fim), None)
        x_doc = dados['left'][rotulo_doc] if rotulo_doc is not None else int(imagem.width * .62)
        x_data = dados['left'][rotulo_data] if rotulo_data is not None else int(imagem.width * .78)

        def ler_celula(esquerda, direita):
            if direita <= esquerda or y_fim <= y_inicio:
                return ''
            recorte = imagem.crop((max(0, esquerda), y_inicio, min(imagem.width, direita), y_fim))
            return pytesseract.image_to_string(recorte, lang=os.getenv('OCR_LANG', 'por'), config='--psm 6')

        nome_texto = ler_celula(x_dest - 40, x_doc - 20)
        nomes = [re.sub(r'^[^A-ZÀ-Ú]+', '', linha.strip()).strip()
                 for linha in nome_texto.splitlines() if len(linha.split()) >= 3
                 and not re.search(r'NOME|RAZ.O|SOCIAL|CNPJ', linha, re.I)]
        doc_texto = ler_celula(x_doc - 40, x_data - 20)
        documentos = {v for v in re.findall(r'(?<!\d)(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})(?!\d)', doc_texto)
                      if validar_documento(v)}
        data_texto = ler_celula(x_data - 40, imagem.width - int(imagem.width * .04))
        datas = set(re.findall(r'(?<!\d)\d{2}/\d{2}/\d{4}(?!\d)', data_texto))
        if len(nomes) == 1 or len(documentos) == 1 or len(datas) == 1:
            complementos.append('DESTINATARIO/REMETENTE')
            if len(nomes) == 1:
                complementos.extend(('NOME/RAZÃO SOCIAL', nomes[0]))
            if len(documentos) == 1:
                complementos.extend(('CNPJ/CPF', next(iter(documentos))))
            if len(datas) == 1:
                complementos.extend(('DATA DA EMISSÃO', next(iter(datas))))
            complementos.append('CÁLCULO DO IMPOSTO')
    return texto + '\n' + '\n'.join(complementos)


def refinar_cabecalho_nfse(imagem, texto):
    """Relê o número e a emissão em cabeçalhos com NFS-e no canto superior."""
    dados = pytesseract.image_to_data(imagem, lang=os.getenv('OCR_LANG', 'por'),
                                     config='--psm 3', output_type=pytesseract.Output.DICT)
    rotulos = [i for i, palavra in enumerate(dados['text'])
               if re.fullmatch(r'NFS-?e', palavra.strip(), re.I)
               and dados['top'][i] < imagem.height * .1
               and dados['left'][i] > imagem.width * .65]
    if not rotulos:
        return texto
    i = min(rotulos, key=lambda indice: dados['top'][indice])
    esquerda = max(0, dados['left'][i] - int(imagem.width * .15))
    fim = min(imagem.height, dados['top'][i] + int(imagem.height * .09))
    recorte = imagem.crop((esquerda, 0, imagem.width, fim))
    leitura = pytesseract.image_to_string(recorte, lang=os.getenv('OCR_LANG', 'por'), config='--psm 6')
    numeros = set(re.findall(r'(?m)^\s*(\d{4,10})\s*$', leitura))
    datas = set(re.findall(r'(?<!\d)\d{2}/\d{2}/\d{4}(?!\d)', leitura))
    complementos = []
    if len(numeros) == 1:
        complementos.append(f'NÚMERO NFS-E: {next(iter(numeros))}')
    if len(datas) == 1:
        complementos.append(f'DATA DA EMISSÃO: {next(iter(datas))}')
    return texto + ('\n' + '\n'.join(complementos) if complementos else '')


def reconhecer(imagem):
    configurar_tesseract()
    original = imagem
    imagem = preparar_imagem(imagem)
    texto = pytesseract.image_to_string(imagem, lang=os.getenv('OCR_LANG', 'por'), config='--psm 3 -c preserve_interword_spaces=1')
    if 'DANFE' in texto.upper():
        texto = refinar_campos_danfe(imagem, texto)
    elif (re.search(r'\bN\s*F\s*-\s*E\b', texto, re.I)
          and re.search(r'SEFAZ|NOTA FISCAL INDICADA', texto, re.I)):
        # Em capturas compactas o modo automático pode ler "N F-e", mas
        # perder o título DANFE e a chave na grade do cabeçalho. Uma segunda
        # leitura da página e do cabeçalho recupera essas células sem usar IA.
        alternativo = pytesseract.image_to_string(imagem, lang=os.getenv('OCR_LANG', 'por'),
            config='--psm 6 -c preserve_interword_spaces=1')
        cabecalho = imagem.crop((int(imagem.width * .42), int(imagem.height * .13),
                                 imagem.width, int(imagem.height * .36)))
        leitura_cabecalho = pytesseract.image_to_string(cabecalho, lang=os.getenv('OCR_LANG', 'por'),
            config='--psm 6')
        if ('DANFE' in alternativo.upper() or 'DANFE' in leitura_cabecalho.upper()
                or re.search(r'CHAVE DE ACESSO', leitura_cabecalho, re.I)):
            texto += '\n' + alternativo + '\n' + leitura_cabecalho
    elif 'NFS-E' in texto.upper():
        texto = refinar_cabecalho_nfse(imagem, texto)
    if 'DANFE' in texto.upper():
        sem_grade = remover_grade(original)
        if sem_grade is not None:
            limpo = pytesseract.image_to_string(preparar_imagem(sem_grade),
                lang=os.getenv('OCR_LANG', 'por'), config='--psm 3 -c preserve_interword_spaces=1')
            # A leitura sem bordas recupera valores antes unidos às linhas.
            # O cabeçalho original ainda fornece número e chave de acesso.
            texto = limpo + '\n' + texto
    return texto


def extrair_texto_imagem(caminho):
    with Image.open(caminho) as imagem:
        return reconhecer(imagem)


def aplicar_ocr_pagina_pdf(caminho, numero_pagina):
    with pymupdf.open(caminho) as documento:
        pixmap = documento[numero_pagina].get_pixmap(dpi=300)
        with Image.open(BytesIO(pixmap.tobytes('png'))) as imagem:
            return reconhecer(imagem)
