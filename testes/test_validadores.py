from processamento.validador import validar_cpf, validar_cnpj


def test_cpf_valido():
    assert validar_cpf("529.982.247-25") is True


def test_cpf_invalido():
    assert validar_cpf("123.456.789-00") is False


def test_cpf_ausente():
    assert validar_cpf(None) is False


def test_cnpj_invalido():
    assert validar_cnpj("11.111.111/1111-11") is False


def test_cnpj_ausente():
    assert validar_cnpj(None) is False