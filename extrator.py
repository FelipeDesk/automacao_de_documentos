import re

def extrair_cpfs(texto):
    padrao_cpf = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'

    cpfs = re.findall(padrao_cpf, texto)

    return cpfs

def validar_cpf(cpf):

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