import re
from datetime import datetime

def extrair_cpfs(texto):
    padrao_cpf = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'

    cpfs = re.findall(padrao_cpf, texto)

    return cpfs

def validar_cpf(cpf):

    if not cpf:
        return False

    # Remove pontos, hífen e qualquer caractere que não seja número
    cpf = re.sub(r"\D", "", cpf)

    # CPF precisa possuir exatamente 11 números
    if len(cpf) != 11:
        return False

    # Elimina CPFs com todos os números iguais
    if cpf == cpf[0] * 11:
        return False


    # PRIMEIRO DÍGITO

    soma = 0

    for i in range(9):
        soma += int(cpf[i]) * (10 - i)

    resto = soma % 11

    primeiro_digito = 0 if resto < 2 else 11 - resto

    if primeiro_digito != int(cpf[9]):
        return False


    # SEGUNDO DÍGITO

    soma = 0

    for i in range(10):
        soma += int(cpf[i]) * (11 - i)

    resto = soma % 11

    segundo_digito = 0 if resto < 2 else 11 - resto

    if segundo_digito != int(cpf[10]):
        return False

    return True


def extrair_cnpjs(texto):
    padrao_cnpj = r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"

    cnpjs = re.findall(padrao_cnpj, texto)

    return cnpjs

def validar_cnpj(cnpj):
    
    if not cnpj:
        return False
    
    cnpj = re.sub(r"\D", "", cnpj)

    if len(cnpj) != 14:
        return False

    if cnpj == cnpj[0] * 14:
        return False

    pesos_primeiro = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    soma = 0

    for i in range(12):
        soma += int(cnpj[i]) * pesos_primeiro[i]

    resto = soma % 11
    primeiro_digito = 0 if resto < 2 else 11 - resto

    if primeiro_digito != int(cnpj[12]):
        return False

    pesos_segundo = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    soma = 0

    for i in range(13):
        soma += int(cnpj[i]) * pesos_segundo[i]

    resto = soma % 11
    segundo_digito = 0 if resto < 2 else 11 - resto

    if segundo_digito != int(cnpj[13]):
        return False

    return True


def extrair_datas(texto):
    padrao_data = r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"

    datas = re.findall(padrao_data, texto)

    return datas

def validar_data(data):
    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y"
    ]

    for formato in formatos:
        try:
            datetime.strptime(data, formato)
            return True

        except ValueError:
            continue

    return False


def extrair_valores(texto):
    padrao_valor = r"R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})?"

    valores = re.findall(padrao_valor, texto)

    return valores

