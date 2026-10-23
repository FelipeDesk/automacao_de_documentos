import json
from processamento.lote import processar_lote


def test_lote_isola_falhas_e_duplicatas(tmp_path):
    entrada = tmp_path / 'entrada'
    entrada.mkdir()
    (entrada / 'corrompido.pdf').write_bytes(b'invalido')
    (entrada / 'outro.xml').write_text('<outro/>')
    resumo = processar_lote(tmp_path)
    assert resumo['erro'] == 2
    assert not list(entrada.iterdir())
    (entrada / 'copia.pdf').write_bytes(b'invalido')
    assert processar_lote(tmp_path)['duplicado'] == 1
    assert len(list((tmp_path / 'resultados' / 'registros').glob('*.json'))) == 2


def test_incompleto_vai_para_revisao(tmp_path):
    entrada = tmp_path / 'entrada'
    entrada.mkdir()
    (entrada / 'incompleto.xml').write_text('<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe/></NFe>')
    assert processar_lote(tmp_path)['revisao_necessaria'] == 1
    assert len(list((tmp_path / 'revisao').iterdir())) == 1
    assert (tmp_path / 'resultados' / 'notas.csv').exists()
