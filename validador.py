from extrator import validar_cpf, validar_cnpj
import re

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
    emitente = resultado.get("emitente", {})
    destinatario = resultado.get("destinatario", {})

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