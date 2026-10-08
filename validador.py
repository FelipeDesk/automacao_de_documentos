import re

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

def validar_documento(documento):
    if not documento:
        return False

    numeros = re.sub(r"\D", "", documento)

    if len(numeros) == 11:
        return validar_cpf(numeros)

    if len(numeros) == 14:
        return validar_cnpj(numeros)

    return False

def validar_chave_acesso(chave):
    if not chave:
        return False

    chave = re.sub(r"\D", "", chave)

    if len(chave) != 44:
        return False

    numeros = chave[:43]
    digito_informado = int(chave[43])

    peso = 2
    soma = 0

    for numero in reversed(numeros):
        soma += int(numero) * peso

        peso += 1

        if peso > 9:
            peso = 2

    resto = soma % 11
    digito_calculado = 11 - resto

    if digito_calculado >= 10:
        digito_calculado = 0

    return digito_calculado == digito_informado

def validar_resultado(resultado):
    emitente = resultado.get("emitente") or {}
    destinatario = resultado.get("destinatario") or {}

    tipo = resultado.get("tipo")

    validacoes = {
        "cnpj_emitente": validar_cnpj(
            emitente.get("cnpj")
        ),

        "documento_destinatario": validar_documento(
            destinatario.get("cnpj_cpf")
        )
    }

    if tipo == "nfe":
        validacoes["chave_acesso"] = validar_chave_acesso(
            resultado.get("chave_acesso")
        )

    return validacoes