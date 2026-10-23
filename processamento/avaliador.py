"""Avaliação por regras; os indicadores não representam probabilidades."""
import math
from processamento.validador import validar_resultado


def avaliar_extracao(dados):
    campos = {
        'numero_nota': dados.get('numero_nota'),
        'emitente.cnpj': (dados.get('emitente') or {}).get('cnpj'),
        'valor_total': dados.get('valor_total'),
    }
    tipo = dados.get('tipo')
    if tipo in {'nfe', 'nfse'}:
        campos['data_emissao'] = dados.get('data_emissao')
        campos['destinatario.cnpj_cpf'] = (dados.get('destinatario') or {}).get('cnpj_cpf')
    if tipo == 'nfe':
        campos['chave_acesso'] = dados.get('chave_acesso')
    ausentes = [campo for campo, valor in campos.items() if valor is None or valor == '']
    validacoes = validar_resultado(dados)
    # Só penaliza identificadores presentes; ausências já entram na completude.
    presentes = {'cnpj_emitente': campos['emitente.cnpj'],
                 'documento_destinatario': (dados.get('destinatario') or {}).get('cnpj_cpf'),
                 'chave_acesso': dados.get('chave_acesso')}
    verificadas = {k: v for k, v in validacoes.items() if presentes.get(k)}
    suspeitas = [f'{k}_invalido' for k, valido in verificadas.items() if not valido]
    for campo in ('valor_total', 'valor_liquido', 'valor_iss'):
        valor = dados.get(campo)
        if valor is not None and (not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0):
            suspeitas.append(f'{campo}_invalido')
    bruto, liquido = dados.get('valor_total'), dados.get('valor_liquido')
    if isinstance(bruto, (int, float)) and isinstance(liquido, (int, float)) and liquido > bruto:
        suspeitas.append('liquido_maior_que_bruto')
    completude = round(100 * (len(campos) - len(ausentes)) / len(campos))
    validade = round(100 * sum(verificadas.values()) / len(verificadas)) if verificadas else None
    revisar = bool(ausentes or suspeitas)
    return {
        'status_extracao': 'revisao_necessaria' if revisar else 'completo',
        'campos_ausentes': ausentes,
        'inconsistencias': suspeitas,
        'completude': completude,
        'validade': validade,
        'confianca_estimada': 'baixa' if revisar else 'alta',
        'criterio_confianca': 'Heurística: alta somente com campos obrigatórios presentes e sem inconsistências detectadas; não é probabilidade.',
        'solicitar_segunda_tentativa': bool(ausentes),
        'elegivel_ia': bool(ausentes) and tipo in {'nfe', 'nfse'},
    }
