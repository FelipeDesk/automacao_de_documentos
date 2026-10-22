# Automação de notas fiscais

Extração de **NF-e e NFS-e** em XML, PDF, PNG e JPEG. Na aplicação web, a API FastAPI processa cada upload em um diretório temporário e devolve JSON; o React mantém lista, prévias, busca, filtros e exportações JSON/CSV **somente na memória da aba**. O SQLite permanece como recurso opcional do processamento em lote local (`main.py`), sem participação na API pública. IA opcional apenas para extrações incompletas e mediante autorização explícita.

O painel usa tema escuro com cantos retos. As capturas em `docs/` mostram versões anteriores da interface e servem apenas como histórico do projeto.

## Instalação

Ambiente verificado: Windows, Python 3.14, Node.js 24 e Tesseract com o idioma `por`. Use Python 3.12+ e Node.js 22.12+; outras versões/sistemas não foram verificados nesta entrega. A mudança para processamento temporário não exige dependências novas: o SQLite já é parte da biblioteca padrão e permanece apenas no lote local.

Na raiz do projeto, no PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm --prefix frontend ci
```

Copie `.env.example` para `.env` na raiz e ajuste as configurações antes de iniciar. O backend lê esse arquivo automaticamente; veja a seção de IA para preencher a chave.

Para executar apenas o backend, `requirements.txt` é suficiente. A aplicação web não usa banco de dados. SQLite faz parte do Python e é usado somente pelo modo de lote local. Não é necessário instalar servidor de banco nem SDK de IA.

### Tesseract

Instale o Tesseract e os dados de idioma português (`por`), conforme a [documentação de instalação](https://tesseract-ocr.github.io/tessdoc/Installation.html). No Windows, configure no `.env` o caminho correspondente à sua instalação:

```dotenv
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
OCR_LANG=por
```

No Linux, os pacotes usuais são `tesseract-ocr` e `tesseract-ocr-por`. Se o executável estiver no `PATH`, `TESSERACT_CMD` é dispensável. No Windows, o sistema também procura a instalação em `ProgramFiles/Tesseract-OCR` e `LOCALAPPDATA/Tesseract-OCR`. Sem Tesseract, XML e PDFs com texto continuam funcionando; imagens e páginas escaneadas registram erro de OCR.

## Executar a aplicação

Terminal 1, na raiz:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```powershell
npm --prefix frontend run dev
```

Abra [a interface](http://127.0.0.1:5173) e [o Swagger](http://127.0.0.1:8000/docs). O Vite encaminha `/api` ao backend local. Faça upload de um ou mais arquivos ou use drag & drop. Pesquise por CNPJ/número, filtre NF-e/NFS-e e abra **Ver detalhes** para comparar os dados extraídos com o arquivo original: foto, PDF ou XML.

A API é síncrona: `POST /api/upload` retorna o status final e os dados estruturados. O backend apaga o arquivo temporário ao concluir, inclusive após erro. A interface conserva os resultados e arquivos originais apenas em memória para prévia, busca, filtro, exclusão e exportação. Recarregar ou fechar a aba descarta tudo; exporte antes de sair. Cada aba mantém seu próprio estado e não existe rota pública para listar, consultar ou baixar resultados de outras pessoas. A API não usa `localStorage`, `sessionStorage`, SQLite ou as pastas operacionais do lote. O navegador pode fazer cache de recursos estáticos, mas respostas `/api/` recebem `Cache-Control: no-store`.

Para publicar a demonstração, sirva frontend e backend sob a mesma origem e TLS. Não publique `entrada/`, `resultados/`, `processados/`, `revisao/`, `erros/`, `duplicados/`, `uploads/` nem `notas.sqlite3` como conteúdo estático. Configure o proxy para limitar também o tamanho do corpo HTTP; a validação da API lê até 20 MB + 1 byte do arquivo. O limite de requisições da aplicação é básico, por IP e por processo; em implantação com múltiplos workers ou atrás de proxy, aplique limites também no proxy. Não há login nem histórico compartilhado.

Para gerar e verificar o build:

```powershell
npm --prefix frontend run build
npm --prefix frontend run preview
```

O preview também requer a API na porta 8000. Para usar outra porta em desenvolvimento, defina `API_PROXY_TARGET` no terminal do Vite antes de iniciá-lo. A pasta `frontend/dist/` não contém backend e não deve ser publicada isoladamente esperando processamento fiscal.

## Processamento em lote

Coloque cópias dos documentos em `entrada/` e execute:

```powershell
.\.venv\Scripts\python.exe main.py
```

As pastas são criadas automaticamente. Defina `DADOS_DIR` no `.env` para isolar os dados operacionais:

```dotenv
DADOS_DIR=C:/dados/notas-demo
```

`DADOS_DIR` é usado somente pelo lote local. A API pública ignora essa variável. Por padrão, o lote usa a raiz do projeto.

| Destino | Conteúdo |
| --- | --- |
| `processados/` | Documentos sem ausências obrigatórias ou inconsistências detectadas |
| `revisao/` | Extrações que ainda têm campos essenciais ausentes ou inconsistências após a IA |
| `erros/` | Arquivos que não puderam ser lidos/classificados/extraídos |
| `duplicados/` | Cópias adicionais preservadas quando o destino já existe |
| `resultados/registros/<id>.json` | Resultado por nota, origem, status, erro e horário UTC |
| `resultados/notas.csv` | Consolidado com uma linha por nota extraída, inclusive em revisão |
| `resultados/resumo.json` | Contadores da última execução do lote |
| `notas.sqlite3` | Notas e associação dos hashes dos arquivos |

Documentos são movidos apenas depois da persistência/exportação. Se ocorrer falha operacional, o lote continua e mantém a entrada para recuperação. Falhas de extração também ficam registradas no banco/JSON; não viram linhas fiscais fictícias no CSV. A função legada `main.processar_arquivo()` permanece disponível para extrair/exportar um arquivo individual sem movê-lo.

A duplicidade é identificada por SHA-256 do conteúdo e, quando disponível, chave fiscal. Chaves NF-e com dígito inválido não são usadas como identidade. Arquivos com falha/revisão também são lembrados para evitar repetições e chamadas de IA. Ao reenviar um arquivo em erro/revisão registrado por uma versão antiga do extrator, o sistema reavalia e atualiza a mesma nota, sem criar outra linha. Resultados da versão atual continuam protegidos contra duplicação. Para repetir a mesma versão após mudar apenas configurações, utilize um novo `DADOS_DIR`. Sem chave confiável, representações diferentes da mesma nota podem exigir conferência manual.

## Exemplos fictícios

A pasta `exemplos/` contém NF-e/NFS-e XML, PDFs com texto, PDF escaneado, JPG, PNG e XML não fiscal. Todos os nomes e identificadores são fictícios. Identificadores zerados e chaves repetidas são intencionais: essas notas devem ir para **revisão**, não ser consideradas fiscalmente válidas.

```powershell
.\.venv\Scripts\python.exe gerar_demo.py
# Ou gere diretamente em uma pasta de demonstração isolada:
.\.venv\Scripts\python.exe gerar_demo.py --saida C:/dados/notas-demo/entrada
```

O gerador sobrescreve somente os nomes de exemplo conhecidos no destino indicado. Não aponte para uma pasta com documentos de produção que tenham esses nomes.

## Arquitetura

```mermaid
flowchart TD
    A[Upload React] --> B[FastAPI: validação e arquivo temporário]
    B --> C[Pipeline compartilhado]
    C --> D{Formato}
    D -->|XML| E[Parser seguro + extratores XML]
    D -->|PDF| F[Texto por página]
    F -->|Página sem texto útil| G[OCR Tesseract]
    D -->|Imagem| G
    F --> H[Classificação + regex e contexto]
    G --> H
    E --> I[Normalização e validação]
    H --> I
    I --> J[Avaliação por regras]
    J -->|Incompleto e envio autorizado| K[IA: JSON e evidência literal]
    K --> I2[Revalidação e revisão humana]
    J --> L[Resposta JSON sem persistência]
    I2 --> L
    L --> M[React: memória da aba]
    M --> N[Prévia, busca, filtros e exportação local]
```

- `extratores/`: regras de NF-e/NFS-e em XML e texto de PDFs/imagens; reaproveitadas do projeto original.
- `processamento/leitor.py` e `ocr.py`: leitura por página e OCR com `--psm 3`, renderização de PDF a 300 DPI e pré-processamento condicional.
- Em DANFEs com grade, uma cópia sem linhas longas recupera valores ligados às bordas das células. A leitura original continua disponível para número e chave; o arquivo original não é alterado. A extração tolera espaços do OCR dentro de CPF/CNPJ e lê vencimentos na tabela de duplicatas.
- `normalizador.py`, `validador.py`, `avaliador.py`: datas/valores/identificadores, dígitos verificadores e diagnóstico.
- `pipeline.py`: coordena extração local, normalização, IA opcional e reavaliação; não move arquivos.
- `ia.py`: extração opcional pelo Gemini 3.6 Flash com retentativas limitadas, com esquema JSON, evidências e métricas.
- `lote.py` e `banco.py`: processamento em lote e persistência SQLite **opcionais para execução local**; nunca importados por `api.py`.
- `api.py`: valida uploads, limita requisições, chama o pipeline e devolve o resultado sem salvar dados.
- `frontend/`: interface responsiva e estado temporário por aba, sem biblioteca visual adicional.

### Mapa dos arquivos

Esta é a ordem sugerida de leitura para estudar o projeto web: `frontend/src/main.tsx` → `api.py` → `processamento/pipeline.py` → leitores/extratores → normalização/avaliação. Para estudar o modo local com persistência, siga `main.py` → `processamento/lote.py` → `processamento/banco.py`.

| Arquivo | Responsabilidade |
| --- | --- |
| `api.py` | Cria o FastAPI; valida upload, tipo MIME/assinatura/tamanho, limita requisições, processa em diretório temporário e devolve JSON. |
| `main.py` | Entrada do processamento em lote e funções de compatibilidade para um arquivo. |
| `gerar_demo.py` | Gera exemplos fictícios para estudo, sem dados reais. |
| `processamento/pipeline.py` | Coordena leitura, extração, normalização, avaliação e eventual tentativa com IA. Define formatos e versão do extrator. |
| `processamento/leitor.py` | Extrai texto de PDF e imagem; recorre ao OCR em páginas sem texto útil. |
| `processamento/leitor_xml.py` | Reconhece a estrutura do XML e escolhe o extrator correspondente. |
| `processamento/ocr.py` | Prepara imagens, encontra o Tesseract e relê regiões de DANFE. |
| `processamento/classificador_fiscal.py` | Identifica NF-e ou NFS-e no texto de PDF/foto. |
| `processamento/normalizador.py` | Converte datas, CPF/CNPJ e valores para um formato comum. |
| `processamento/validador.py` | Verifica dígitos de CPF, CNPJ e chave de acesso. |
| `processamento/avaliador.py` | Aponta campos obrigatórios ausentes e inconsistências; determina necessidade de revisão. |
| `processamento/ia.py` | Executa o fallback opcional, limitado a campos ausentes e evidências literais. |
| `processamento/lote.py` | Identifica duplicatas, processa arquivos, organiza pastas e exporta JSON/CSV. |
| `processamento/banco.py` | Cria e consulta o SQLite; persiste, atualiza e exclui notas e hashes associados. |
| `extratores/campos_layout.py` | Lê campos de tabelas em colunas sem atribuir números a rótulos errados. |
| `extratores/nfe_pdf.py` | Extrai campos de DANFE em texto de PDF ou OCR. |
| `extratores/nfse_pdf.py` | Extrai campos de NFS-e em texto de PDF ou OCR. |
| `extratores/nfe_xml.py` | Extrai NF-e do XML do Portal Fiscal. |
| `extratores/nfse_xml.py` | Extrai NFS-e de XML ABRASF ou municipal paulistano. |
| `frontend/src/main.tsx` | Tela React: upload, lista em memória, filtros, detalhes/prévia local, exclusão e exportações JSON/CSV. |
| `frontend/src/style.css` | Layout responsivo, cores do tema escuro e estados visuais. |
| `frontend/index.html` | Documento HTML inicial, metadados e ponto de montagem do React. |
| `frontend/vite.config.ts` | Configura o proxy `/api` do Vite para o FastAPI local; aceita `API_PROXY_TARGET`. |
| `frontend/tsconfig.json` | Regras de compilação e checagem do TypeScript. |
| `frontend/src/vite-env.d.ts` | Tipos do ambiente Vite usados pelo frontend. |
| `frontend/package.json` | Scripts de desenvolvimento/build e dependências declaradas. |
| `frontend/package-lock.json` | Versões exatas resolvidas pelo npm para instalação reproduzível. |
| `requirements.txt` | Bibliotecas Python necessárias para executar a aplicação. |
| `requirements-dev.txt` | Dependências adicionais da suíte de testes. |
| `.env.example` | Exemplo de variáveis de ambiente; não é carregado automaticamente. |
| `.gitignore` | Impede que banco, credenciais, caches e documentos operacionais entrem no Git. |
| `pytest.ini` | Registra a marca dos testes opcionais com OCR real. |
| `testes/__init__.py` | Torna os utilitários de teste importáveis como pacote. |
| `testes/conftest.py` | Fixtures comuns; bloqueia chamadas externas de IA durante a suíte. |
| `testes/dados_ficticios.py` | Cria os documentos sintéticos usados no gerador e nos testes. |
| `testes/test_api.py` | Exercita validação, limite, isolamento e limpeza da API temporária. |
| `testes/test_banco.py` | Exercita persistência SQLite e identificação de duplicatas. |
| `testes/test_ia.py` | Verifica autorizações, resposta estruturada e evidências sem chamada externa real. |
| `testes/test_avaliador.py` | Verifica completude, validade e necessidade de revisão. |
| `testes/test_validadores.py` | Verifica CPF, CNPJ, chave de acesso e regras de dígito. |
| `testes/test_ocr.py` | Verifica leitura de imagens, PDFs escaneados e descoberta do Tesseract. |
| `testes/test_classificador.py` | Verifica o reconhecimento de NF-e/NFS-e no texto. |
| `testes/test_extracao_pdf.py` | Exercita os extratores de PDF com exemplos sintéticos. |
| `testes/test_extracao_xml.py` | Exercita os extratores de XML e formatos desconhecidos. |
| `testes/test_nfse_layouts.py` | Verifica variações de apresentação da NFS-e. |
| `testes/test_layouts_municipais.py` | Verifica colunas e XML municipal, inclusive regressões. |
| `testes/test_lote.py` | Exercita processamento em lote e organização de pastas. |
| `testes/test_integracao.py` | Verifica o fluxo de ponta a ponta entre componentes. |
| `testes/test_regressao.py` | Protege casos de erro já corrigidos. |
| `testes/fixtures/nfe_teste.xml` | NF-e XML fictícia para verificar o extrator. |
| `testes/fixtures/nfse_teste.xml` | NFS-e XML fictícia para verificar o extrator. |
| `testes/fixtures/xml_desconhecido.xml` | XML sem estrutura fiscal reconhecida. |
| `testes/fixtures/danfe_teste.pdf` | DANFE fictício de referência. |
| `testes/fixtures/danfe_teste2.pdf` | Segundo layout de DANFE fictício. |
| `testes/fixtures/danfse_teste.pdf` | Layout de NFS-e fictícia. |
| `exemplos/nfe_teste.xml` | NF-e XML fictícia para execução manual. |
| `exemplos/nfse_teste.xml` | NFS-e XML fictícia para execução manual. |
| `exemplos/xml_desconhecido.xml` | Exemplo de XML não fiscal. |
| `exemplos/danfe_teste.pdf` | Exemplo de DANFE em PDF. |
| `exemplos/danfe_teste2.pdf` | Exemplo de outro layout de DANFE. |
| `exemplos/danfse_teste.pdf` | Exemplo de NFS-e em PDF. |
| `exemplos/nfse_escaneada.pdf` | Exemplo de PDF escaneado que requer OCR. |
| `exemplos/nfse_imagem.jpg` | Foto fictícia de NFS-e para testar OCR JPEG. |
| `exemplos/nfse_imagem.png` | Imagem fictícia de NFS-e para testar OCR PNG. |
| `docs/RELATORIO.md` | Relatório das fases, decisões e validações do projeto. |
| `docs/interface.jpg` | Captura histórica da interface em desktop. |
| `docs/interface-mobile.jpg` | Captura histórica da interface estreita. |

`entrada/`, `processados/`, `revisao/`, `erros/`, `duplicados/`, `resultados/` e `notas.sqlite3` pertencem exclusivamente ao lote local. `uploads/` é legado e não é usado pela API pública. `.venv/`, `frontend/node_modules/` e `frontend/dist/` são artefatos de instalação/build.

O formato original (`tipo`, `numero_nota`, `emitente`, `destinatario`, datas e `valor_total`) foi preservado. Foram acrescentados campos de líquido/ISS, `vencimentos`, validações, avaliação e metadados. `valor_total` representa **valor bruto**. `data_vencimento` mantém o primeiro vencimento encontrado; `vencimentos` preserva todas as datas identificadas. Ausência é `null`, nunca um valor inventado. A resposta da API e os registros do lote envolvem esses dados na propriedade `dados` e acrescentam status e origem.

### Regras de qualidade

Campos obrigatórios comuns: número, CNPJ do emitente e valor bruto. Para NF-e/NFS-e identificadas, também data de emissão e documento do destinatário; NF-e exige chave. Vencimento não é obrigatório. Algumas operações legitimamente não identificam destinatário; a regra conservadora ainda as encaminha para revisão.

- **Completude:** percentual dos campos obrigatórios presentes; valor zero conta como presente.
- **Validade:** percentual dos identificadores presentes que passam nas verificações matemáticas. Não verifica existência cadastral, autorização fiscal ou assinatura.
- Valor negativo, líquido superior ao bruto e identificadores inválidos exigem revisão. Valores não finitos são normalizados para ausência.
- Campos ausentes habilitam uma segunda tentativa via IA, somente para tipo fiscal já reconhecido e com texto disponível. Apenas identificador inválido não provoca chamada de IA.

## IA opcional e economia de tokens

O backend carrega automaticamente o `.env` da raiz ao iniciar pela API (`uvicorn api:app`) ou pelo lote (`main.py`), mesmo quando o diretório de execução é outro. A leitura ocorre antes da configuração dos limites de upload e dos módulos de processamento. Variáveis já definidas no ambiente têm prioridade sobre o arquivo.

Em uma nova instalação, copie `.env.example` para `.env` (sem sobrescrever um arquivo existente):

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edite o `.env` uma vez, preenchendo sua chave do [Google AI Studio](https://aistudio.google.com/app/apikey) e habilitando o uso de IA quando desejar:

```dotenv
GEMINI_API_KEY=sua-chave-aqui
IA_HABILITADA=1
IA_ENVIO_AUTORIZADO=1
IA_ENVIO_IMAGEM=0
```

O único provedor é Gemini. O modelo principal é [`gemini-3.6-flash`](https://ai.google.dev/gemini-api/docs/models/gemini-3.6-flash); após HTTP 503 persistente, o sistema tenta [`gemini-3.5-flash-lite`](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite). Não há seleção de provedor ou modelo por variável. A configuração inicial mantém o processamento local (`IA_HABILITADA=0` e `IA_ENVIO_AUTORIZADO=0`); a chave começa vazia. Para enviar também fotos ao fallback, defina `IA_ENVIO_IMAGEM=1`.

Reinicie o backend após editar o arquivo. Se ainda houver variáveis antigas no PowerShell, abra um novo terminal para usar os valores do `.env`. O `.env` e suas variantes estão protegidos pelo `.gitignore`; apenas `.env.example`, sem credenciais, é versionado. A chave é usada somente pelo backend. Consulte as [condições e preços do Gemini](https://ai.google.dev/gemini-api/docs/pricing) para seu modelo e conta.

**Quando a IA é acionada:** a decisão ocorre em `processamento/pipeline.py` depois da primeira extração local e da avaliação por regras. A chamada acontece apenas quando **todas** estas condições são verdadeiras:

1. O documento foi reconhecido como NF-e ou NFS-e e há texto de PDF ou OCR disponível. XML é extraído localmente e não fornece texto ao fallback.
2. Falta pelo menos um campo **obrigatório** avaliado por `processamento/avaliador.py`: número, CNPJ do emitente, valor bruto, data de emissão ou documento do destinatário; NF-e exige também a chave. Campos opcionais ausentes, como valor líquido/ISS, não bastam.
3. `IA_HABILITADA=1` **e** `IA_ENVIO_AUTORIZADO=1`, além de `GEMINI_API_KEY` preenchida no `.env` ou no ambiente.
4. O texto contém linhas com contexto fiscal suficientes para montar o trecho enviado.

Um identificador apenas inválido, sem campo obrigatório ausente, solicita revisão sem chamar IA. Se qualquer condição falhar, `metadados.ia.utilizada` fica `false` e não há requisição externa. A API pública não tem cache de notas: cada novo envio é processado novamente e pode gerar uma nova chamada de IA quando configurada. O cache por duplicidade existe apenas no lote local.

Só habilite as opções depois de autorizar o envio dos dados envolvidos e verificar o tratamento adequado das informações. A autorização por ambiente se aplica aos documentos processados nessa execução. `IA_ENVIO_IMAGEM=1` é uma autorização separada para enviar fotos JPEG/PNG inteiras, além do texto OCR, apenas quando a extração local estiver incompleta. Os testes automatizados usam respostas simuladas, sem envio externo.

A integração Gemini usa [`generateContent` com saída JSON estruturada](https://ai.google.dev/gemini-api/docs/structured-output) por `generationConfig.responseMimeType` e `responseJsonSchema`, seguida pelo filtro local de evidências e validações. Consulte `metadados.ia.provedor`, `chamadas`, `erro` e `campos_aceitos` nos detalhes.

Para economizar, XML/texto/OCR e regex têm prioridade. O fallback recebe somente campos ausentes e trechos fiscais (até 12 mil caracteres), faz até três tentativas no modelo principal somente em falhas temporárias e limita a saída a 1.800 tokens. Se o 3.6 Flash persistir em HTTP 503, há até duas tentativas adicionais no 3.5 Flash-Lite. Esse trecho pode conter nomes, identificadores e valores presentes no documento. Sem `IA_ENVIO_IMAGEM=1`, não envia imagens. Com ela, envia uma cópia JPEG reduzida da foto inteira (até 2048 px), que pode consumir tokens adicionais não cobertos pela estimativa simples de caracteres. Documentos completos, não fiscais ou sem texto não acionam a IA. Extrações XML não têm fallback externo nesta versão.

Erros temporários (HTTP 408, 429, 500, 502, 503 e 504), timeout e falhas de conexão permitem até três tentativas no modelo principal, com intervalos de 1 e 2 segundos acrescidos de pequena variação aleatória. A integração respeita `Retry-After` de até 30 segundos; prazos maiores encerram a tentativa atual para não manter o upload esperando pela quota. Apenas HTTP 503 persistente ativa o modelo reserva. Erros de autenticação, parâmetros ou modelo (400/401/403/404) não são repetidos. Se todas as tentativas falharem, o resultado local é preservado. Os detalhes da interface mostram os modelos tentados, o número de tentativas e se a imagem foi enviada.

A resposta deve citar evidência literal, conter o valor nessa evidência e preencher apenas campos ausentes permitidos. No modo texto, a evidência precisa constar do OCR. No modo foto, identificadores, datas e valores também passam por verificações locais; mesmo assim, a evidência visual gerada pela IA não pode ser conferida automaticamente contra os pixels. Valores existentes são preservados. Quando os campos essenciais ficam completos e válidos após a IA, o status é `Concluída`; ainda é prudente conferir os dados antes de utilizá-los. JSON inválido, recusa/resposta incompleta, timeout ou falha de rede preservam a extração local. Erros HTTP mostram o status e o código de máquina devolvido pela API (por exemplo, `HTTP 429 (RESOURCE_EXHAUSTED)`), sem expor a chave, a mensagem livre nem o documento. Esse código indica que uma cota ou limite da API foi atingido.

Os metadados registram provedor, modelo, número de chamadas, histórico de falhas, envio de imagem, uso de IA, campos aceitos, erro, estimativa simples de tokens de entrada e tokens retornados pela API. Custo estimado é calculado somente se forem definidos `IA_PRECO_ENTRADA_MILHAO` e `IA_PRECO_SAIDA_MILHAO` em USD; configure esses valores conforme os preços do modelo na sua conta.

## API

| Método | Rota | Uso |
| --- | --- | --- |
| POST | `/api/upload` | Multipart com campo `arquivo`; limite de 20 MB |
| GET | `/docs` | Swagger automático |

Valida extensão, MIME declarado, tamanho, arquivo vazio, assinatura de PDF/imagem e início de XML. O MIME do cliente não é usado como prova única de formato. A rota rejeita declarações DTD/entidades identificadas no conteúdo; o parser também impede expansão de entidades. O nome do upload não escolhe o caminho temporário. Um upload aceito que falha na extração retorna HTTP 200 com `status=erro`; erros de validação usam HTTP 400, 413 ou 415. O limite básico usa `UPLOADS_POR_MINUTO` (padrão 10 por IP/processo) e `UPLOADS_SIMULTANEOS` (padrão 2 por processo); excesso retorna HTTP 429. Arquivos temporários do processamento são apagados no sucesso e no erro. Não há processamento assíncrono em segundo plano.

A interface oferece exclusão com confirmação, filtros de status, busca por emitente/CNPJ/número/arquivo, ordenação e resumo financeiro das notas concluídas. Nos detalhes, o arquivo mantido na memória da aba aparece ao lado dos dados em telas largas e acima deles em telas estreitas. Exportar JSON ou CSV cria um download no próprio navegador, sem chamar a API. O CSV neutraliza células que poderiam ser interpretadas como fórmulas em planilhas. Após excluir, a prévia desaparece e é possível reenviar o documento.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest -q
# OCR real opcional:
$env:TESTAR_OCR_REAL = '1'
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run build
```

Os testes automatizados cobrem extração local, disparo simulado do Gemini, upload da API, limpeza do diretório temporário, isolamento das rotas e limite de requisições, sem enviar notas a um serviço externo. Para confirmar uma resposta real do Gemini, preencha a chave e as autorizações no `.env` e reinicie o backend e envie uma nota incompleta. Os PDFs, XML e `malaguNFE2.jpg` fornecidos anteriormente passaram na extração local; a foto antiga `malaguNFE.jpg` ainda requer revisão da chave de acesso, pois o OCR não a reproduz com segurança.

Para testar a leitura com cobertura útil, separe arquivos de **uma nota por documento**, com os valores corretos conhecidos para comparação:

| Documento | O que verifica |
| --- | --- |
| NF-e XML original e DANFE PDF da mesma nota | Campos, chave de 44 dígitos e consistência entre formatos |
| NFS-e XML original e PDF com texto selecionável da mesma nota | Número, prestador/tomador, bruto, líquido, ISS e data |
| DANFE e NFS-e digitalizados em PDF, sem texto selecionável | OCR em página escaneada |
| Fotos JPG e PNG de NF-e e NFS-e, inteiras, legíveis, de frente | OCR e envio opcional de imagem ao Gemini |
| Fotos inclinadas, com sombra/dobra e com rotação EXIF | Robustez do pré-processamento e limites de leitura |
| NFS-e de municípios ou provedores diferentes | Adaptação a layouts distintos |
| Nota com campo essencial ausente ou ilegível | Disparo da IA, evidência, preservação dos demais campos e conclusão quando a avaliação final estiver completa e válida |
| Arquivo repetido e PDF/imagem inválido | Reprocessamento independente, tratamento de erro e ausência de dados inventados |

Confira especialmente número, CNPJ/CPF, data de emissão, chave NF-e, valor bruto, líquido, ISS, vencimentos e o documento mostrado na prévia. Documentos de teste com dados anonimizados precisam manter os dígitos verificadores válidos quando a validação desses campos fizer parte do teste.

As capturas em `docs/` são históricas e podem divergir da interface atual. Não foi realizada validação em celular físico.

## Limitações conhecidas

- Layouts municipais de NFS-e variam: o parser XML cobre o namespace ABRASF usado nos exemplos, o retorno municipal paulistano (`RetornoConsulta/NFe`, com ou sem namespace) e o de NF-e o namespace do Portal Fiscal. Padrões nacionais/municipais diferentes podem precisar de novos adaptadores.
- PDFs com texto são lidos preservando as colunas. Cabeçalhos e linhas de valores são associados por coluna, e a seção de totais tem prioridade sobre itens individuais. RPS não substitui número da NFS-e. O formato municipal denominado `NFe` é classificado como NFS-e por sua estrutura.
- PDF/imagem depende de rótulos e contexto textual reconhecíveis. Tabelas com ordem de leitura ambígua, fotos inclinadas, baixa nitidez e texto manuscrito podem gerar campos ausentes. OCR não garante recuperação de imagens ruins. Uma foto reconhecida com chave ausente permanece para revisão, preservando os demais campos extraídos.
- O leitor considera texto útil a partir de 20 caracteres por página; cabeçalhos em páginas com corpo escaneado podem impedir OCR automático. O OCR corrige orientação EXIF, amplia imagens pequenas e relê regiões de total/chave e das células de emitente/destinatário/data do DANFE localizadas pelo cabeçalho. Em capturas compactas de NF-e, se o OCR ler "N F-e" e perder "DANFE", o leitor relê o cabeçalho e combina uma segunda segmentação antes de classificar o documento. Para NFS-e com cabeçalho no canto superior, relê o número e a data; tabelas de nove montantes com rótulos reconhecidos são mapeadas por coluna. Identificadores só são aceitos na releitura do DANFE se passarem pela validação matemática; valores conflitantes não são aceitos e não há correção automática de dígitos da chave. No lote local, a versão 8 do extrator reavalia notas anteriores em erro/revisão quando reenviadas; se a chave recuperada apontar para uma nota já cadastrada, o erro antigo é consolidado com ela.
- Uma nota por documento. Não há separação de arquivos com várias notas nem suporte a XML compactado/ZIP, assinatura digital ou consulta à SEFAZ/prefeituras.
- Somente CPF/CNPJ numéricos. Identificadores alfanuméricos e regimes tributários específicos não são tratados.
- ISS, base, alíquota e retenção são extraídos quando o layout expõe rótulos suportados. Não há cálculo/reconciliação tributária completa.
- No lote local, cópias em formatos diferentes podem não ser reconhecidas como duplicadas sem chave confiável. A interface pública não faz deduplicação nem permite editar/aprovar manualmente os campos.
- A API é síncrona. Seu limite de upload e de requisições não substitui limites de infraestrutura para exposição pública. Não há autenticação, histórico no servidor ou recuperação dos dados da aba após recarregar. Downloads JSON/CSV ficam no dispositivo do usuário e passam a ser responsabilidade dele.
- O limite de 12 mil caracteres pode deixar evidências de IA de fora. A integração externa foi testada com mocks, não com chamada paga real.

## Organização para GitHub

`.gitignore` exclui ambientes, caches, credenciais, banco local e documentos operacionais. Exemplos e fixtures publicados no estado atual são fictícios. Arquivos operacionais e caches anteriormente rastreados foram removidos apenas do índice do Git, preservando os arquivos locais. **O histórico anterior pode conter dados:** a limpeza do estado atual não reescreve commits passados; revise o histórico antes de tornar o repositório público. Não houve push nem publicação automática.

Veja [o relatório de implementação](docs/RELATORIO.md) para a análise inicial, fases, validação e commits.
