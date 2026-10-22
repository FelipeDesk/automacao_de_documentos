import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Dados = {
  tipo: "nfe" | "nfse";
  numero_nota: string | null;
  chave_acesso: string | null;
  emitente: { cnpj: string | null; razao_social: string | null };
  destinatario: { cnpj_cpf: string | null; razao_social: string | null };
  data_emissao: string | null;
  data_vencimento: string | null;
  valor_total: number | null;
  valor_liquido: number | null;
  valor_iss: number | null;
  avaliacao: {
    completude: number;
    validade: number | null;
    campos_ausentes: string[];
    inconsistencias: string[];
  };
  metadados: {
    metodo: string;
    ocr_utilizado: boolean;
    ia: { utilizada: boolean; erro: string | null; chamadas: number; provedor?: string; modelo?: string; modelos_tentados?: string[]; imagem_enviada?: boolean; campos_aceitos?: string[] };
  };
};
type Nota = {
  id: string;
  origem: string;
  status: "sucesso" | "erro" | "revisao_necessaria";
  dados: Dados | null;
  erro: string | null;
  processado_em: string;
};
type NotaSessao = Nota & { arquivo: File };
const statusNome = {
  sucesso: "Concluída",
  erro: "Erro",
  revisao_necessaria: "Revisão necessária",
};
const campoNome: Record<string, string> = {
  chave_acesso: "Chave de acesso", numero_nota: "Número da nota", valor_total: "Valor bruto",
  data_emissao: "Data de emissão", "emitente.cnpj": "CNPJ do emitente",
  "destinatario.cnpj_cpf": "CPF/CNPJ do destinatário",
};
const tipoNome = { nfe: "NF-e", nfse: "NFS-e" };
const explicarErroIA = (erro: string) => {
  if (erro.startsWith("HTTP 503") || erro.includes("UNAVAILABLE"))
    return "O Gemini está temporariamente indisponível. Tente novamente mais tarde; a extração local foi mantida.";
  if (erro.includes("RESOURCE_EXHAUSTED") || erro.startsWith("HTTP 429"))
    return "A cota do Gemini foi atingida. Confira os limites da sua conta no Google AI Studio.";
  if (erro.startsWith("HTTP 404"))
    return "O modelo configurado não está disponível para esta chave. Confira o acesso ao Gemini 3.6 Flash no Google AI Studio.";
  if (erro.startsWith("HTTP 401"))
    return "A chave da API foi recusada. Confira GEMINI_API_KEY no .env do backend.";
  if (erro.startsWith("HTTP 403"))
    return "O Gemini recusou o acesso. Confira a chave, o projeto e a disponibilidade do modelo no Google AI Studio.";
  return `A API retornou ${erro}. Confira as configurações e os limites da conta.`;
};
const moeda = (valor: number | null | undefined) =>
  valor == null
    ? "Não informado"
    : valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

async function requisitar<T>(url: string, opcoes?: RequestInit): Promise<T> {
  const resposta = await fetch(url, opcoes);
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new Error(
      typeof corpo.detail === "string"
        ? corpo.detail
        : `Não foi possível concluir a operação (${resposta.status}).`,
    );
  }
  return resposta.json();
}

function baixar(conteudo: string, tipo: string, nome: string) {
  const url = URL.createObjectURL(new Blob([conteudo], { type: tipo }));
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csvSeguro(valor: unknown): string {
  let texto = valor == null ? "" : String(valor);
  if (/^[\s\u0000-\u001f]*[=+\-@]/.test(texto)) texto = `'${texto}`;
  return `"${texto.replace(/"/g, '""')}"`;
}

function exportar(notas: NotaSessao[], formato: "json" | "csv") {
  const registros: Nota[] = notas.map(({ arquivo: _arquivo, ...nota }) => nota);
  if (formato === "json") {
    baixar(JSON.stringify(registros, null, 2), "application/json;charset=utf-8", "notas-sessao.json");
    return;
  }
  const campos = ["id", "origem", "tipo", "numero_nota", "cnpj_emitente", "documento_destinatario",
    "data_emissao", "data_vencimento", "valor_total", "valor_liquido", "valor_iss", "status", "metodo", "ia_utilizada"];
  const linhas = registros.map((n) => {
    const d = n.dados;
    const valores = [n.id, n.origem, d?.tipo, d?.numero_nota, d?.emitente.cnpj,
      d?.destinatario.cnpj_cpf, d?.data_emissao, d?.data_vencimento, d?.valor_total,
      d?.valor_liquido, d?.valor_iss, n.status, d?.metadados.metodo, d?.metadados.ia.utilizada];
    return valores.map(csvSeguro).join(";");
  });
  baixar(`\uFEFF${campos.join(";")}\r\n${linhas.join("\r\n")}`, "text/csv;charset=utf-8", "notas-sessao.csv");
}

type Previa = { estado: "carregando" | "pronta" | "erro"; tipo?: "imagem" | "pdf" | "xml"; url?: string; texto?: string };

function PreviaDocumento({ arquivo }: { arquivo: File }) {
  const [previa, setPrevia] = useState<Previa>({ estado: "carregando" });
  useEffect(() => {
    let ativo = true;
    let endereco: string | undefined;
    setPrevia({ estado: "carregando" });
    async function carregarArquivo() {
      try {
        const extensao = arquivo.name.split(".").pop()?.toLowerCase();
        if (extensao === "xml") {
          const texto = await arquivo.text();
          if (ativo) setPrevia({ estado: "pronta", tipo: "xml", texto });
        } else if (["jpg", "jpeg", "png", "pdf"].includes(extensao || "")) {
          if (!ativo) return;
          endereco = URL.createObjectURL(arquivo);
          setPrevia({ estado: "pronta", tipo: extensao === "pdf" ? "pdf" : "imagem", url: endereco });
        } else {
          throw new Error("formato não disponível");
        }
      } catch {
        if (ativo) setPrevia({ estado: "erro" });
      }
    }
    void carregarArquivo();
    return () => { ativo = false; if (endereco) URL.revokeObjectURL(endereco); };
  }, [arquivo]);

  return (
    <section className="document-preview" aria-label="Documento original">
      <div className="preview-heading">
        <div><span className="eyebrow">ARQUIVO ORIGINAL</span><strong title={arquivo.name}>{arquivo.name}</strong></div>
        {previa.estado === "pronta" && previa.url &&
          <a href={previa.url} target="_blank" rel="noopener noreferrer">Abrir ↗</a>}
      </div>
      <div className="preview-stage">
        {previa.estado === "carregando" && <p role="status">Carregando documento…</p>}
        {previa.estado === "erro" && <p role="alert">O arquivo original não está disponível para visualização.</p>}
        {previa.tipo === "imagem" && previa.url && <img src={previa.url} alt={`Documento ${arquivo.name}`} />}
        {previa.tipo === "pdf" && previa.url && <iframe src={previa.url} title={`Documento ${arquivo.name}`} />}
        {previa.tipo === "xml" && <pre>{previa.texto}</pre>}
      </div>
    </section>
  );
}

function App() {
  const [notas, setNotas] = useState<NotaSessao[]>([]);
  const [busca, setBusca] = useState("");
  const [tipo, setTipo] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [selecionada, setSelecionada] = useState<NotaSessao | null>(null);
  const [excluir, setExcluir] = useState<NotaSessao | null>(null);
  const confirmacao = useRef<HTMLDialogElement>(null);
  const [ordem, setOrdem] = useState("recentes");
  const [enviando, setEnviando] = useState(false);
  const [arrastando, setArrastando] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (selecionada) dialog.current?.showModal();
  }, [selecionada]);

  useEffect(() => {
    if (excluir) confirmacao.current?.showModal();
  }, [excluir]);

  function confirmarExclusao() {
    if (!excluir) return;
    setNotas((lista) => lista.filter((n) => n.id !== excluir.id));
    setMensagem("Nota removida desta sessão.");
    setErro("");
    confirmacao.current?.close();
    setExcluir(null);
  }

  async function enviar(arquivos: FileList | File[]) {
    if (enviando || !arquivos.length) return;
    setEnviando(true);
    setErro("");
    setMensagem("");
    const falhas: string[] = [];
    let processados = 0;
    for (const arquivo of Array.from(arquivos)) {
      setMensagem(`Processando ${arquivo.name}…`);
      if (
        !/\.(xml|pdf|jpe?g|png)$/i.test(arquivo.name) ||
        arquivo.size > 20 * 1024 * 1024
      ) {
        falhas.push(`${arquivo.name}: use XML, PDF, JPG ou PNG de até 20 MB.`);
        continue;
      }
      try {
        const form = new FormData();
        form.append("arquivo", arquivo);
        const nota = await requisitar<Nota>("/api/upload", {
          method: "POST",
          body: form,
        });
        setNotas((lista) => [{ ...nota, arquivo }, ...lista]);
        processados++;
      } catch (e) {
        falhas.push(
          `${arquivo.name}: ${e instanceof Error ? e.message : "Falha no envio."}`,
        );
      }
    }
    setMensagem(`${processados} documento(s) processado(s). Confira o status na lista.`);
    if (falhas.length) setErro(falhas.join(" "));
    setEnviando(false);
    if (input.current) input.current.value = "";
  }

  const pesquisa = busca.trim().toLowerCase();
  const visiveis = notas.filter(
    (n) =>
      (!tipo || n.dados?.tipo === tipo) &&
      (!filtroStatus || n.status === filtroStatus || (filtroStatus === "atencao" && n.status !== "sucesso")) &&
      (!pesquisa ||
        [
          n.dados?.numero_nota,
          n.dados?.emitente.razao_social,
          n.dados?.emitente.cnpj,
          n.dados?.emitente.cnpj?.replace(/\D/g, ""),
          n.origem,
        ].some(
          (v) =>
            v?.toLowerCase().includes(pesquisa.replace(/[./-]/g, "")) ||
            v?.toLowerCase().includes(pesquisa),
        )),
  );
  visiveis.sort((a, b) => ordem === "valor"
    ? (b.dados?.valor_total ?? -1) - (a.dados?.valor_total ?? -1)
    : ordem === "emitente"
      ? (a.dados?.emitente.razao_social || a.origem).localeCompare(b.dados?.emitente.razao_social || b.origem, "pt-BR")
      : b.processado_em.localeCompare(a.processado_em));
  const concluidas = notas.filter((n) => n.status === "sucesso");
  const totalBruto = concluidas.reduce((soma, n) => soma + (n.dados?.valor_total ?? 0), 0);
  const detalhes = selecionada?.dados;
  return (
    <div className="app">
      <main id="inicio">
        <div className="heading">
          <h1>Extrator de dados de Nf-e e NFS-e</h1>
          <div className="export-actions">
            <button className="secondary" disabled={!notas.length || enviando} onClick={() => exportar(notas, "json")}>Exportar JSON</button>
            <button className="secondary" disabled={!notas.length || enviando} onClick={() => exportar(notas, "csv")}>Exportar CSV</button>
          </div>
        </div>
        <section className="stats" aria-label="Resumo dos documentos">
          <div>
            <span>Documentos recebidos</span>
            <strong>{notas.length.toString().padStart(2, "0")}</strong>
            <small>Todos os arquivos</small>
          </div>
          <div>
            <span>Concluídos</span>
            <strong className="green">
              {notas
                .filter((n) => n.status === "sucesso")
                .length.toString()
                .padStart(2, "0")}
            </strong>
            <small>Sem pendências detectadas</small>
          </div>
          <div>
            <span>Precisam de atenção</span>
            <strong className="amber">
              {notas
                .filter((n) => n.status !== "sucesso")
                .length.toString()
                .padStart(2, "0")}
            </strong>
            <small>Revisões e erros</small>
          </div>
          <div className="total-card">
            <span>Valor bruto concluído</span>
            <strong>{moeda(totalBruto)}</strong>
            <small>Soma das {concluidas.length} notas concluídas</small>
          </div>
        </section>
        <section
          className={`upload ${arrastando ? "dragging" : ""}`}
          aria-label="Enviar documentos"
          onDragOver={(e) => {
            e.preventDefault();
            if (!enviando) setArrastando(true);
          }}
          onDragLeave={() => setArrastando(false)}
          onDrop={(e) => {
            e.preventDefault();
            setArrastando(false);
            void enviar(e.dataTransfer.files);
          }}
        >
          <div className="upload-icon" aria-hidden="true">
            ↥
          </div>
          <div className="upload-copy">
            <h2>
              {enviando
                ? "Lendo seus documentos…"
                : "Arraste suas notas para cá"}
            </h2>
            <p>XML, PDF e fotos JPG ou PNG · Até 20 MB por arquivo</p>
          </div>
          <input
            ref={input}
            type="file"
            multiple
            accept=".xml,.pdf,.jpg,.jpeg,.png"
            hidden
            onChange={(e) => {
              if (e.target.files) void enviar(e.target.files);
            }}
          />
          <button
            className="primary"
            disabled={enviando}
            onClick={() => input.current?.click()}
          >
            {enviando ? "Processando…" : "+ Selecionar arquivos"}
          </button>
        </section>
        <div className="feedback" aria-live="polite">
          {mensagem}
        </div>
        {erro && (
          <p className="error" role="alert">
            {erro}
          </p>
        )}
        <section className="documents">
          <div className="list-heading">
            <div>
              <h2>
                {filtroStatus === "revisao_necessaria" ? "Documentos para revisar" : filtroStatus === "erro" ? "Documentos com erro" : "Seus documentos"}
              </h2>
              <span>{visiveis.length} resultado(s)</span>
            </div>
            <div className="filters">
              <label className="search">
                <span aria-hidden="true">⌕</span>
                <input
                  aria-label="Pesquisar emitente, CNPJ, número ou arquivo"
                  placeholder="Emitente, CNPJ ou número…"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                />
              </label>
              <select
                aria-label="Filtrar tipo de nota"
                value={tipo}
                onChange={(e) => setTipo(e.target.value)}
              >
                <option value="">Todos os tipos</option>
                <option value="nfe">NF-e</option>
                <option value="nfse">NFS-e</option>
              </select>
            </div>
          </div>
          <div className="list-tools">
            <div className="status-tabs" aria-label="Filtrar status">
              {[["", "Todos"], ["sucesso", "Concluídas"], ["revisao_necessaria", "Para revisar"], ["erro", "Com erro"]].map(([valor, nome]) => (
                <button key={valor} className={filtroStatus === valor ? "active" : ""}
                  aria-pressed={filtroStatus === valor} onClick={() => setFiltroStatus(valor)}>
                  {nome} <span>{notas.filter((n) => !valor || n.status === valor).length}</span>
                </button>
              ))}
            </div>
            <select aria-label="Ordenar documentos" value={ordem} onChange={(e) => setOrdem(e.target.value)}>
              <option value="recentes">Mais recentes</option>
              <option value="valor">Maior valor bruto</option>
              <option value="emitente">Emitente A–Z</option>
            </select>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Documento / emitente</th>
                  <th>Tipo</th>
                  <th>Emissão</th>
                  <th>Valor bruto</th>
                  <th>Status</th>
                  <th>
                    <span className="sr-only">Ações</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visiveis.map((n) => (
                  <tr key={n.id}>
                    <td>
                      <div className="document-name">
                        <span className="file-icon">▤</span>
                        <div>
                          <strong>
                            {n.dados?.numero_nota
                              ? `Nota ${n.dados.numero_nota}`
                              : n.origem}
                          </strong>
                          <small>
                            {n.dados?.emitente.razao_social ||
                              n.dados?.emitente.cnpj ||
                              "Emitente não identificado"}
                          </small>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="type">
                        {n.dados ? tipoNome[n.dados.tipo] : "—"}
                      </span>
                    </td>
                    <td>{n.dados?.data_emissao || "—"}</td>
                    <td className="money">{moeda(n.dados?.valor_total)}</td>
                    <td>
                      <span className={`status ${n.status}`}>
                        <i />
                        {statusNome[n.status]}
                      </span>
                      {n.dados?.metadados.ia.utilizada && (
                        <span className="ai">IA</span>
                      )}
                    </td>
                    <td className="row-actions">
                      <button
                        className="details"
                        aria-label={`Ver detalhes de ${n.dados?.numero_nota || n.origem}`}
                        onClick={() => setSelecionada(n)}
                      >
                        Ver detalhes ↗
                      </button>
                      <button className="delete-button" disabled={enviando}
                        aria-label={`Excluir nota ${n.dados?.numero_nota || n.origem}`}
                        onClick={() => { setErro(""); setExcluir(n); }}>Excluir</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!visiveis.length && (
            <div className="empty">
              <span>▤</span>
              <h3>
                {notas.length
                    ? "Nenhum documento encontrado"
                    : "Sua organização começa aqui"}
              </h3>
              <p>
                {notas.length
                  ? "Experimente outro tipo, CNPJ ou número."
                  : "Envie sua primeira nota fiscal para visualizar os dados extraídos."}
              </p>
            </div>
          )}
          <footer>
            {visiveis.length} de {notas.length} documentos · Valor bruto visível: {moeda(visiveis.reduce((soma, n) => soma + (n.dados?.valor_total ?? 0), 0))}
            <span>Resultados só nesta aba</span>
          </footer>
        </section>
        <p className="page-note">
          A avaliação indica completude e validade por regras. Confira os dados
          antes de utilizá-los.
        </p>
      </main>
      <dialog ref={confirmacao} className="delete-dialog" aria-labelledby="delete-title"
        onClose={() => setExcluir(null)}>
        <span className="eyebrow">GERENCIAR DOCUMENTO</span>
        <h2 id="delete-title">Excluir esta nota?</h2>
        <p><b>{excluir?.dados?.numero_nota ? `Nota ${excluir.dados.numero_nota}` : excluir?.origem}</b></p>
        <p>A nota e sua prévia serão removidas desta aba e das exportações. Para recuperá-las, envie o arquivo novamente.</p>
        {erro && <p className="error" role="alert">{erro}</p>}
        <div className="dialog-actions">
          <button className="secondary" onClick={() => confirmacao.current?.close()}>Cancelar</button>
          <button className="danger" onClick={confirmarExclusao}>Excluir nota</button>
        </div>
      </dialog>
      <dialog
        className="document-dialog"
        ref={dialog}
        onClose={() => setSelecionada(null)}
        onClick={(e) => {
          if (e.target === dialog.current) dialog.current.close();
        }}
      >
        <div className="dialog-header">
          <div>
            <span className="eyebrow">DETALHES DO DOCUMENTO</span>
            <h2>
              {detalhes?.numero_nota
                ? `Nota ${detalhes.numero_nota}`
                : selecionada?.origem}
            </h2>
          </div>
          <button
            className="secondary"
            aria-label="Fechar detalhes"
            onClick={() => dialog.current?.close()}
          >
            ✕
          </button>
        </div>
        {selecionada && (
          <>
            <span className={`status ${selecionada.status}`}>
              <i />
              {statusNome[selecionada.status]}
            </span>
            <p className="origin">
              Arquivo: {selecionada.origem}
              <br />
              Processado em{" "}
              {new Date(selecionada.processado_em).toLocaleString("pt-BR")}
            </p>
          </>
        )}
        {selecionada?.erro && <p className="error">{selecionada.erro}</p>}
        <div className="detail-layout">
          <div className="detail-content">
        {detalhes && (
          <>
            <dl>
              {Object.entries({
                Tipo: tipoNome[detalhes.tipo],
                Emissão: detalhes.data_emissao,
                "Prestador / emitente": detalhes.emitente.razao_social,
                "CNPJ do emitente": detalhes.emitente.cnpj,
                "Tomador / destinatário": detalhes.destinatario.razao_social,
                "CPF/CNPJ do destinatário": detalhes.destinatario.cnpj_cpf,
                "Valor bruto": moeda(detalhes.valor_total),
                "Valor líquido": moeda(detalhes.valor_liquido),
                ISS: moeda(detalhes.valor_iss),
                Vencimento: detalhes.data_vencimento,
                "Chave fiscal": detalhes.chave_acesso,
                Método: detalhes.metadados.metodo,
                "OCR utilizado": detalhes.metadados.ocr_utilizado
                  ? "Sim"
                  : "Não",
                "IA acionada": detalhes.metadados.ia.utilizada ? "Sim" : "Não",
                "Provedor IA": detalhes.metadados.ia.provedor || "Não configurado",
                "Modelo IA": detalhes.metadados.ia.modelo || "Não informado",
                "Modelos tentados": detalhes.metadados.ia.modelos_tentados?.join(", ") || "Nenhum",
                "Tentativas de IA": String(detalhes.metadados.ia.chamadas),
                "Imagem enviada à IA": detalhes.metadados.ia.imagem_enviada ? "Sim" : "Não",
                "Campos preenchidos pela IA": detalhes.metadados.ia.campos_aceitos?.join(", ") || "Nenhum",
              }).map(([nome, valor]) => (
                <div key={nome}>
                  <dt>{nome}</dt>
                  <dd>{valor ?? "Não informado"}</dd>
                </div>
              ))}
            </dl>
            <section className="quality">
              <h3>Avaliação da extração</h3>
              <p>
                Completude: {detalhes.avaliacao.completude}% · Validade dos
                identificadores:{" "}
                {detalhes.avaliacao.validade == null
                  ? "Não avaliada"
                  : `${detalhes.avaliacao.validade}%`}
              </p>
              {!!detalhes.avaliacao.campos_ausentes.length && (
                <p>
                  <b>Campos ausentes:</b>{" "}
                  {detalhes.avaliacao.campos_ausentes.map((campo) => campoNome[campo] || campo).join(", ")}
                </p>
              )}
              {!!detalhes.avaliacao.inconsistencias.length && (
                <p>
                  <b>Conferir:</b>{" "}
                  {detalhes.avaliacao.inconsistencias.join(", ")}
                </p>
              )}
              {detalhes.metadados.ia.erro && (
                <p className="error">
                  Falha no auxílio de IA: {explicarErroIA(detalhes.metadados.ia.erro)}
                  {" "}Extração local preservada.
                </p>
              )}
            </section>
            <details className="raw">
              <summary>Todos os campos extraídos (JSON)</summary>
              <pre>{JSON.stringify(detalhes, null, 2)}</pre>
            </details>
          </>
        )}
          </div>
          {selecionada && <PreviaDocumento arquivo={selecionada.arquivo} />}
        </div>
      </dialog>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
