# Relatório de implementação

Data: 13/10/2026. Branch preservada: `feature/finalizacao-automacao-fiscal`. Trabalho realizado no repositório existente, sem publicação/push.

## Análise inicial

A suíte inicial tinha 20 testes aprovados. `main.py` coordenava leitura, normalização, validação e JSON. `extratores/` continha NF-e/NFS-e XML e PDF; `processamento/` tinha leitor XML/PDF, classificador, normalizador, validadores, OCR inicial e um avaliador ainda não versionado.

Dependências já utilizadas: pypdf, PyMuPDF, Pillow, pytesseract e pytest. XML usava ElementTree; foi substituído pelo parser compatível defusedxml para documentos recebidos de fora.

Funcionalidades confirmadas e reaproveitadas: os quatro extratores, classificação, normalização de datas/valores/CPF/CNPJ, validação matemática de CPF/CNPJ/chave, exportação JSON e testes existentes. O OCR já renderizava páginas PDF, mas tinha caminho de Tesseract fixo, não integrava imagens ao processamento e não registrava seu uso. O avaliador registrava somente ausências de três campos. A NFS-e podia confundir líquido com bruto. Não existiam lote com movimentação, CSV, SQLite, fallback configurável, API ou frontend.

Havia alterações locais do usuário em `main.py` e `testes/test_integracao.py`, além de `avaliador.py` e seus testes não rastreados. Foram preservadas funcionalmente e incorporadas às fases relacionadas. Nenhum reset/checkout destrutivo foi executado. Caches compilados antigos e resultados locais estavam rastreados; foram retirados apenas do índice, com arquivos locais preservados.

## Fases concluídas

| Fase | Entrega | Verificação na fase | Commit |
| --- | --- | --- | --- |
| 6 | OCR configurável, pré-processamento condicional, PDF por página e imagens | 24 testes | `7acb257` — adiciona OCR para PDFs e imagens |
| 7 | Contexto/acentos em NFS-e, bruto separado de líquido, campos ISS | 26 testes | `076455b` — melhora extração de NFS-e |
| 8 | Obrigatórios por tipo, completude, validade, inconsistências e confiança heurística | 28 testes | `9fb2b89` — adiciona avaliação dos dados extraídos |
| 9 | Fallback de IA com autorização, esquema JSON, evidência, métricas e tratamento de falhas | 31 testes | `e940ee1` — integra IA para extrações incompletas |
| 10 | Pipeline compartilhado, lote resiliente, pastas, hashes, logs e CSV | 33 testes | `59cbb46` — automatiza processamento de arquivos |
| 11 | SQLite transacional, consultas e unicidade fiscal | 35 testes | `516fc09` — adiciona banco de dados SQLite |
| 12 | Upload e consultas FastAPI, validação e Swagger | 37 testes | `7893e78` — cria API com FastAPI |
| 13 | React/TypeScript/Vite, upload, filtros, detalhes e dashboard | 37 testes, build e navegador | `56d271d` — cria interface para notas fiscais |
| 14 | Regressões, fixtures sintéticas, OCR real, vencimentos, XML seguro e hashes alternativos | 57 testes com OCR real | `db8e16b` — amplia testes automatizados |
| 15 | Dependências, exemplos, documentação, screenshots e higiene do repositório | Verificação final descrita abaixo | `finaliza documentação do projeto` — consulte o hash com `git log -1 --oneline` |

O hash do commit que contém este relatório não pode ser escrito dentro do próprio commit sem alterá-lo. O relatório final no chat inclui o hash após a criação.

## Testes e verificações

- Suíte padrão: 54 aprovados e 3 testes opcionais de OCR ignorados.
- Com `TESTAR_OCR_REAL=1`: 57 aprovados. Tesseract executado de verdade com idioma português para PNG, JPG e PDF escaneado gerados durante os testes.
- XML/PDF NF-e e NFS-e, imagens, PDF misto, extração incompleta, arquivo corrompido, XML inválido/entidades, documento não fiscal e CNPJ inválido.
- Ausência de vencimento e preservação de múltiplos vencimentos; `data_vencimento` mantém o primeiro por compatibilidade.
- Lote completo com movimentação e JSON/CSV/SQLite; duplicidade por conteúdo/chave e associação de hashes alternativos.
- Fallback com autorização ausente, chamada desnecessária, evidência inválida, campos existentes, timeout e JSON inválido; nenhuma chamada paga.
- API: upload, listagem, detalhe, status, Swagger, validação, nome seguro e duplicatas.
- Build: TypeScript e Vite aprovados; dependências Python verificadas com `pip check`.
- Navegador: upload de XML fictício pela própria interface, status de revisão, modal de dados, pesquisa e filtro NF-e/NFS-e. Layouts 390 px e desktop inspecionados; excesso de largura corrigido.
- Aceitação do CLI com os nove exemplos: 8 revisões intencionais e 1 documento não fiscal; 8 linhas CSV, 9 registros SQLite e 9 JSON, com entrada esvaziada pela movimentação. Execução isolada com IA desativada.
- As capturas usam somente nomes e identificadores fictícios. Não houve teste em celular físico.

## Preservação e privacidade

Os documentos antigos de `testes/fixtures` foram preservados em `C:/Users/felip/AppData/Local/Temp/notas-fixtures-originais-20261013` antes de substituir as fixtures versionadas por arquivos integralmente sintéticos. O programa de geração está em `testes/dados_ficticios.py`; `gerar_demo.py` gera também imagens e PDF escaneado.

Os testes desabilitam IA e bloqueiam seu transporte externo automaticamente. Configuração de API, chave e preços são variáveis de ambiente; `.env.example` não contém segredos. Logs de extração mostram hash abreviado, método e status, não conteúdo fiscal nem credenciais.

Caches, resultados operacionais, configurações do editor, bancos e documentos recebidos não fazem parte do estado final versionado. O histórico Git anterior foi preservado e pode conter dados antigos: deve ser revisado antes de tornar o repositório público. Nenhum push ou publicação foi feito.

## Limitações e execução

O [README](../README.md) descreve instalação do Tesseract, variáveis, comandos de lote/API/frontend, arquitetura e limitações. A compatibilidade de XML/layouts é deliberadamente limitada aos padrões e rótulos implementados; OCR de baixa qualidade e dados ambíguos exigem revisão. CNPJ alfanumérico, assinatura/autorização fiscal, múltiplas notas por arquivo, autenticação, fila distribuída e aprovação manual pela interface não estão implementados.

Campos preenchidos pela IA sempre exigem revisão, mesmo quando têm evidência textual. A presença literal não comprova associação correta ao campo. A integração externa foi validada com mocks, não com chamada real. São necessárias `IA_HABILITADA=1`, `IA_ENVIO_AUTORIZADO=1`, chave e modelo configurados para qualquer envio.

Use apenas uma instância/processo por diretório de dados para manter JSON/CSV consistentes. Após corrigir uma configuração para reavaliar documentos já registrados, utilize cópias em um novo `DADOS_DIR`. A interface e o backend devem estar em execução para o fluxo de upload.
