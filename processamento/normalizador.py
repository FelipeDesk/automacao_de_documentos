import re
import math
from datetime import datetime

def normalizar_cnpj(cnpj):
    if not cnpj:
        return None

    numeros = re.sub(r"\D", "", cnpj)

    if len(numeros) != 14:
        return None

    return (
        f"{numeros[:2]}."
        f"{numeros[2:5]}."
        f"{numeros[5:8]}/"
        f"{numeros[8:12]}-"
        f"{numeros[12:]}"
    )

def normalizar_cpf(cpf):
    if not cpf:
        return None

    numeros = re.sub(r"\D", "", cpf)

    if len(numeros) != 11:
        return None

    return (
        f"{numeros[:3]}."
        f"{numeros[3:6]}."
        f"{numeros[6:9]}-"
        f"{numeros[9:]}"
    )

def normalizar_documento(documento):
    if not documento:
        return None

    numeros = re.sub(r"\D", "", documento)

    if len(numeros) == 11:
        return normalizar_cpf(numeros)

    if len(numeros) == 14:
        return normalizar_cnpj(numeros)

    return None

def normalizar_valor(valor):
    if valor is None:
        return None

    if isinstance(valor, (int, float)):
        numero = float(valor)
        return numero if math.isfinite(numero) else None

    valor = valor.strip()
    valor = valor.replace("R$", "").strip()

    if "," in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    try:
        numero = float(valor)
        return numero if math.isfinite(numero) else None

    except ValueError:
        return None

def normalizar_data(data):
    if not data:
        return None

    try:
        data_convertida = datetime.fromisoformat(data)

        return data_convertida.strftime(
            "%d/%m/%Y"
        )

    except ValueError:
        pass

    formatos = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y"
    ]

    for formato in formatos:
        try:
            data_convertida = datetime.strptime(
                data,
                formato
            )

            return data_convertida.strftime(
                "%d/%m/%Y"
            )

        except ValueError:
            continue

    return None

def normalizar_resultado(resultado):
    emitente = resultado.get("emitente") or {}
    destinatario = resultado.get("destinatario") or {}

    resultado_normalizado = {
        "tipo": resultado.get("tipo"),

        "numero_nota": resultado.get(
            "numero_nota"
        ),

        "chave_acesso": resultado.get(
            "chave_acesso"
        ),

        "emitente": {
            "cnpj": normalizar_cnpj(
                emitente.get("cnpj")
            ),

            "razao_social": emitente.get(
                "razao_social"
            )
        },

        "destinatario": {
            "cnpj_cpf": normalizar_documento(
                destinatario.get("cnpj_cpf")
            ),

            "razao_social": destinatario.get(
                "razao_social"
            )
        },

        "data_emissao": normalizar_data(
            resultado.get("data_emissao")
        ),

        "data_vencimento": normalizar_data(
            resultado.get("data_vencimento")
        ),

        "valor_total": normalizar_valor(
            resultado.get("valor_total")
        )
    }

    for campo in ("valor_liquido", "valor_iss", "base_calculo_iss", "aliquota_iss"):
        resultado_normalizado[campo] = normalizar_valor(resultado.get(campo))
    resultado_normalizado["vencimentos"] = [
        data for valor in resultado.get("vencimentos", [])
        if (data := normalizar_data(valor)) is not None
    ]
    if not resultado_normalizado["vencimentos"] and resultado_normalizado["data_vencimento"]:
        resultado_normalizado["vencimentos"] = [resultado_normalizado["data_vencimento"]]
    resultado_normalizado["iss_retido"] = resultado.get("iss_retido")
    return resultado_normalizado