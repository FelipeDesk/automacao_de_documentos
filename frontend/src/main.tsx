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
    confianca_estimada: string;
    campos_ausentes: string[];
    inconsistencias: string[];
  };
  metadados: {
    metodo: string;
    ocr_utilizado: boolean;
    ia: { utilizada: boolean; erro: string | null; chamadas: number };
  };
};
type Nota = {
  id: string;
  origem: string;
  status: "sucesso" | "erro" | "revisao_necessaria";
  dados: Dados | null;
  erro: string | null;
  processado_em: string;
  duplicado: boolean;
};
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

function App() {
  const [notas, setNotas] = useState<Nota[]>([]);
  const [busca, setBusca] = useState("");
  const [tipo, setTipo] = useState("");
  const [filtroStatus, setFiltroStatus] = useState("");
  const [selecionada, setSelecionada] = useState<Nota | null>(null);
  const [excluir, setExcluir] = useState<Nota | null>(null);
  const [excluindo, setExcluindo] = useState(false);
  const confirmacao = useRef<HTMLDialogElement>(null);
  const [ordem, setOrdem] = useState("recentes");
  const [carregando, setCarregando] = useState(true);
  const [enviando, setEnviando] = useState(false);
  const [arrastando, setArrastando] = useState(false);
  const [erro, setErro] = useState("");
  const [mensagem, setMensagem] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  async function carregar() {
    setCarregando(true);
    try {
      const todos: Nota[] = [];
      for (let deslocamento = 0; ; deslocamento += 500) {
        const pagina = await requisitar<Nota[]>(
          `/api/notas?limite=500&deslocamento=${deslocamento}`,
        );
        todos.push(...pagina);
        if (pagina.length < 500) break;
      }
      setNotas(todos);
      setErro("");
    } catch {
      setErro(
        "Não foi possível conectar à API. Verifique se o servidor está em execução e tente atualizar.",
      );
    } finally {
      setCarregando(false);
    }
  }
  useEffect(() => {
    void carregar();
  }, []);
  useEffect(() => {
    if (selecionada) dialog.current?.showModal();
  }, [selecionada]);

  useEffect(() => {
    if (excluir) confirmacao.current?.showModal();
  }, [excluir]);

  async function confirmarExclusao() {
    if (!excluir || excluindo) return;
    setExcluindo(true);
    try {
      await requisitar(`/api/notas/${excluir.id}`, { method: "DELETE" });
      setNotas((lista) => lista.filter((n) => n.id !== excluir.id));
      setMensagem("Nota excluída da lista. Você pode enviar o arquivo novamente.");
      setErro("");
      confirmacao.current?.close();
      setExcluir(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Não foi possível excluir a nota.");
    } finally {
      setExcluindo(false);
    }
  }

  async function enviar(arquivos: FileList | File[]) {
    if (enviando || !arquivos.length) return;
    setEnviando(true);
    setErro("");
    setMensagem("");
    const falhas: string[] = [];
    let processados = 0,
      duplicados = 0;
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
        if (nota.duplicado) duplicados++;
        else processados++;
      } catch (e) {
        falhas.push(
          `${arquivo.name}: ${e instanceof Error ? e.message : "Falha no envio."}`,
        );
      }
    }
    await carregar();
    setMensagem(
      `${processados} documento(s) processado(s). ${duplicados} duplicado(s). Confira o status na lista.`,
    );
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
      <aside className="sidebar">
        <a className="brand" href="#inicio">
          <span className="brand-icon">n</span>notas
          <span className="brand-dot">.</span>
        </a>
        <span className="nav-label">ESPAÇO DE TRABALHO</span>
        <button
          className={`nav-item ${!filtroStatus ? "selected" : ""}`}
          onClick={() => setFiltroStatus("")}
        >
          <span>▤</span> Documentos{" "}
          <span className="nav-count">{notas.length}</span>
        </button>
        <button
          className={`nav-item ${filtroStatus === "revisao_necessaria" ? "selected" : ""}`}
          onClick={() => setFiltroStatus("revisao_necessaria")}
        >
          <span>◷</span> Para revisar{" "}
          <span className="nav-count">
            {notas.filter((n) => n.status === "revisao_necessaria").length}
          </span>
        </button>
        <div className="local-note">
          <span className="green-dot" /> Processamento local
          <p>Seus documentos organizados, com você no controle.</p>
        </div>
      </aside>
      <main id="inicio">
        <header>
          <div className="breadcrumb">
            Meu espaço <span>/</span> Documentos fiscais
          </div>
          <span className="local-chip">NF-e & NFS-e</span>
        </header>
        <div className="heading">
          <div>
            <span className="eyebrow">GESTÃO DE DOCUMENTOS</span>
            <h1>Notas fiscais</h1>
            <p>Do arquivo aos dados. Tudo em um só lugar.</p>
          </div>
          <button
            className="secondary"
            onClick={() => void carregar()}
            disabled={carregando || enviando}
          >
            ↻ Atualizar
          </button>
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
                      <button className="delete-button" disabled={enviando || excluindo}
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
                {carregando
                  ? "Carregando documentos…"
                  : notas.length
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
            <span>Extração local primeiro</span>
          </footer>
        </section>
        <p className="page-note">
          A avaliação indica completude e validade por regras. Confira os dados
          antes de utilizá-los.
        </p>
      </main>
      <dialog ref={confirmacao} className="delete-dialog" aria-labelledby="delete-title"
        onCancel={(e) => { if (excluindo) e.preventDefault(); }}
        onClose={() => setExcluir(null)}>
        <span className="eyebrow">GERENCIAR DOCUMENTO</span>
        <h2 id="delete-title">Excluir esta nota?</h2>
        <p><b>{excluir?.dados?.numero_nota ? `Nota ${excluir.dados.numero_nota}` : excluir?.origem}</b></p>
        <p>A nota será removida da lista e das exportações. Os arquivos originais serão preservados. Para recuperar o registro, envie o arquivo novamente.</p>
        {erro && <p className="error" role="alert">{erro}</p>}
        <div className="dialog-actions">
          <button className="secondary" disabled={excluindo} onClick={() => confirmacao.current?.close()}>Cancelar</button>
          <button className="danger" disabled={excluindo} onClick={() => void confirmarExclusao()}>{excluindo ? "Excluindo…" : "Excluir nota"}</button>
        </div>
      </dialog>
      <dialog
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
                "IA utilizada": detalhes.metadados.ia.utilizada
                  ? "Sim — conferir campos"
                  : "Não",
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
              <p>
                Confiança heurística: {detalhes.avaliacao.confianca_estimada}.
                Não representa probabilidade de acerto.
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
                  Falha no auxílio de IA: {detalhes.metadados.ia.erro}. Extração
                  local preservada.
                </p>
              )}
            </section>
            <details className="raw">
              <summary>Todos os campos extraídos (JSON)</summary>
              <pre>{JSON.stringify(detalhes, null, 2)}</pre>
            </details>
          </>
        )}
      </dialog>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
