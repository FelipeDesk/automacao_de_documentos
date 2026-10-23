"""Gera exclusivamente documentos fictícios para testes e demonstração."""
from pathlib import Path
import pymupdf

TEXTO_NFE = '''DANFE - DOCUMENTO FICTICIO SEM VALIDADE FISCAL
Documento Auxiliar da Nota Fiscal Eletrônica
NF-e N. 12345
CHAVE DE ACESSO
11111111111111111111111111111111111111111111
IDENTIFICAÇÃO DO EMITENTE
Empresa Ficticia de Testes
CNPJ 00.000.000/0000-00
DESTINATÁRIO / REMETENTE
NOME / RAZÃO SOCIAL Cliente Ficticio
CNPJ / CPF 000.000.000-00
DATA DA EMISSÃO 20/01/2026
CÁLCULO DO IMPOSTO
V. TOTAL DA NOTA 150,75
VENCIMENTO 20/02/2026
'''
TEXTO_NFSE = '''NFS-e - DOCUMENTO FICTICIO SEM VALIDADE FISCAL
Numero da nota: 87352173
Data de Emissao: 21/01/2026
DADOS DO PRESTADOR
CNPJ: 00.000.000/0000-00
Razao Social: Empresa Ficticia de Servicos
DADOS DO TOMADOR
CPF: 000.000.000-00
Nome: Cliente Ficticio
VALORES
VALOR TOTAL DOS SERVICOS: R$ 162,57
VALOR LIQUIDO DA NFS-E: R$ 157,57
VALOR DO ISS: R$ 5,00
'''
XML_NFE = '''<NFe xmlns="http://www.portalfiscal.inf.br/nfe"><infNFe Id="NFe11111111111111111111111111111111111111111111">
<ide><nNF>12345</nNF><dhEmi>2026-01-20T12:00:00-03:00</dhEmi></ide>
<emit><CNPJ>00000000000000</CNPJ><xNome>Empresa Ficticia de Testes</xNome></emit>
<dest><CPF>00000000000</CPF><xNome>Cliente Ficticio</xNome></dest>
<total><ICMSTot><vNF>150.75</vNF></ICMSTot></total>
<cobr><dup><dVenc>2026-02-20</dVenc></dup></cobr>
<infAdic><infCpl>DOCUMENTO FICTICIO SEM VALIDADE FISCAL</infCpl></infAdic>
</infNFe></NFe>'''
XML_NFSE = '''<CompNfse xmlns="http://www.abrasf.org.br/nfse.xsd"><Nfse><InfNfse>
<Numero>87352173</Numero><DataEmissao>2026-01-21</DataEmissao>
<PrestadorServico><IdentificacaoPrestador><Cnpj>00000000000000</Cnpj></IdentificacaoPrestador><RazaoSocial>Empresa Ficticia de Servicos</RazaoSocial></PrestadorServico>
<TomadorServico><IdentificacaoTomador><CpfCnpj><Cpf>00000000000</Cpf></CpfCnpj></IdentificacaoTomador><RazaoSocial>Cliente Ficticio</RazaoSocial></TomadorServico>
<Servico><Valores><ValorServicos>162.57</ValorServicos><ValorLiquidoNfse>157.57</ValorLiquidoNfse><ValorIss>5.00</ValorIss></Valores><Discriminacao>DOCUMENTO FICTICIO SEM VALIDADE FISCAL</Discriminacao></Servico>
</InfNfse></Nfse></CompNfse>'''


def gerar(pasta, incluir_imagens=False):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, texto in [('nfe_teste.xml', XML_NFE), ('nfse_teste.xml', XML_NFSE), ('xml_desconhecido.xml', '<contrato>Documento ficticio nao fiscal</contrato>')]:
        (pasta / nome).write_text(texto, encoding='utf-8')
    for nome, texto in [('danfe_teste.pdf', TEXTO_NFE), ('danfe_teste2.pdf', TEXTO_NFE.replace('12345', '12346')), ('danfse_teste.pdf', TEXTO_NFSE)]:
        with pymupdf.open() as documento:
            pagina = documento.new_page()
            pagina.insert_text((40, 50), texto, fontsize=12, lineheight=1.7)
            documento.save(pasta / nome)
            if incluir_imagens and nome == 'danfse_teste.pdf':
                pixmap = pagina.get_pixmap(dpi=180)
                pixmap.pil_save(pasta / 'nfse_imagem.png')
                pixmap.pil_save(pasta / 'nfse_imagem.jpg')
                with pymupdf.open() as scan:
                    scan.new_page().insert_image(pagina.rect, stream=pixmap.tobytes('png'))
                    scan.save(pasta / 'nfse_escaneada.pdf', deflate=True)
