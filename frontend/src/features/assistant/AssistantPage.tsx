import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowUp, Bot, Copy, FileText, History, MessageSquare, Paperclip, Plus, Settings2, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { apiGet, apiSend } from "@/services/api/client";
import { useSession } from "@/app/providers/SessionProvider";
import { DocumentWorkspace } from "./DocumentWorkspace";
import { useI18n } from "@/i18n";

const schema = z.object({ answer: z.string(), mode: z.string(), notice: z.string().optional(), sources: z.array(z.object({ id: z.string(), title: z.string(), text: z.string(), reference: z.string(), revision: z.string(), page: z.number().optional(), heading: z.string().optional(), classification: z.string().optional(), language: z.string().optional() })) });
type Answer = z.infer<typeof schema>;
type Exchange = { id: string; question: string; result: Answer };
const configSchema = z.object({ generation_enabled: z.boolean(), retrieval_mode: z.string(), generation_ready: z.boolean().default(false), generation_status: z.string().default("disabled"), local_provider: z.boolean().default(false), uploads_enabled: z.boolean().default(false) });

function AnswerActions({ answer }: { answer: string }) {
  const { t } = useI18n();
  const [status, setStatus] = useState("");
  const [voted, setVoted] = useState(false);
  const [sending, setSending] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(answer); setStatus(t("assistant.copied")); }
    catch { setStatus(t("assistant.copyFailed")); }
  }
  async function feedback(vote: "helpful" | "unhelpful") {
    setSending(true);
    try { await apiSend("POST", "assistant/feedback", { vote }); setVoted(true); setStatus(t("assistant.feedbackSaved")); }
    catch { setStatus(t("assistant.feedbackFailed")); }
    finally { setSending(false); }
  }
  const action = "rounded-lg p-2 text-muted hover:bg-canvas hover:text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-40";
  return <div className="mt-2"><div className="flex gap-1">
    <button aria-label={t("assistant.copy")} title={t("assistant.copy")} type="button" onClick={() => void copy()} className={action}><Copy aria-hidden className="h-4 w-4" /></button>
    <button aria-label={t("assistant.helpful")} title={t("assistant.helpful")} type="button" disabled={voted || sending} onClick={() => void feedback("helpful")} className={action}><ThumbsUp aria-hidden className="h-4 w-4" /></button>
    <button aria-label={t("assistant.unhelpful")} title={t("assistant.unhelpful")} type="button" disabled={voted || sending} onClick={() => void feedback("unhelpful")} className={action}><ThumbsDown aria-hidden className="h-4 w-4" /></button>
  </div>{status && <p role="status" className="text-xs text-muted">{status}</p>}</div>;
}

export function AssistantPage() {
  const { t } = useI18n();
  const { role } = useSession();
  const config = useQuery({ queryKey: ["assistant", "config"], queryFn: ({ signal }) => apiGet("assistant/config", configSchema, signal), staleTime: 15_000, refetchInterval: 15_000, retry: false });
  const [documentsOpen, setDocumentsOpen] = useState(false);
  const [selectedReferences, setSelectedReferences] = useState<string[]>([]);
  const documentDialog = useRef<HTMLDialogElement>(null);
  function openDocuments() { setDocumentsOpen(true); documentDialog.current?.showModal(); }
  function closeDocuments() { documentDialog.current?.close(); setDocumentsOpen(false); }
  const [language, setLanguage] = useState("auto");
  const [useHistory, setUseHistory] = useState(true);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Exchange[]>([]);
  const [chats, setChats] = useState<{ id: string; messages: Exchange[]; references: string[] }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState("");
  const conversation = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const wasBusy = useRef(false);
  useEffect(() => {
    if (wasBusy.current && !busy) input.current?.focus({ preventScroll: true });
    wasBusy.current = busy;
  }, [busy]);
  useEffect(() => {
    const panel = conversation.current;
    if (panel) panel.scrollTop = messages.length || busy ? panel.scrollHeight : 0;
  }, [messages, busy]);
  function clear() {
    if (messages.length) setChats((previous) => [{ id: crypto.randomUUID(), messages, references: selectedReferences }, ...previous].slice(0, 5));
    setMessages([]); setSelectedReferences([]); setError(""); setQuestion(""); input.current?.focus();
  }
  function restore(id: string) {
    const chat = chats.find((item) => item.id === id);
    if (!chat) return;
    setChats((previous) => [...(messages.length ? [{ id: crypto.randomUUID(), messages, references: selectedReferences }] : []), ...previous.filter((item) => item.id !== id)].slice(0, 5));
    setMessages(chat.messages); setSelectedReferences(chat.references); setError(""); setQuestion(""); input.current?.focus();
  }
  async function ask(event: FormEvent) {
    event.preventDefault();
    if (busy || !config.data || question.trim().length < 3) return;
    setBusy(true); setError(""); setPending(question.trim());
    const submitted = question.trim();
    try {
      const result = await apiSend("POST", "assistant/ask", { question: submitted, language, history: useHistory ? messages.slice(-3).map((message) => message.question) : [], ...(selectedReferences.length ? { selected_references: selectedReferences } : {}) }, schema);
      setMessages((previous) => [...previous.slice(-9), { id: crypto.randomUUID(), question: submitted, result }]);
      setQuestion("");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "The assistant could not be reached."); }
    finally { setBusy(false); setPending(""); }
  }
  return <div className="mx-auto grid max-w-6xl overflow-hidden rounded-3xl border border-line bg-surface shadow-card lg:grid-cols-[14rem_minmax(0,1fr)]">
    <aside aria-label="Assistant workspace" className="hidden flex-col border-r border-line bg-canvas p-5 lg:flex">
      <p className="mb-5 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-primary"><Sparkles aria-hidden className="h-4 w-4" />Workspace</p>
      <button type="button" disabled={busy} onClick={clear} className="flex items-center gap-2 rounded-xl bg-forest px-3 py-3 text-sm font-semibold text-white"><Plus aria-hidden className="h-4 w-4" />{t("assistant.new")}</button>
      <button type="button" onClick={openDocuments} className="mt-2 flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-3 text-sm font-semibold"><FileText aria-hidden className="h-4 w-4 text-primary" />{t("assistant.documents")}</button>
      <p className="mb-3 mt-7 text-2xs font-bold uppercase tracking-widest text-muted">{t("assistant.recent")}</p>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">{chats.length ? chats.map((chat) => <button key={chat.id} type="button" disabled={busy} aria-label={`Restore chat: ${chat.messages[0]?.question ?? "Conversation"}`} onClick={() => restore(chat.id)} className="block w-full truncate rounded-lg px-2 py-2 text-left text-xs text-muted hover:bg-surface">{chat.messages[0]?.question}</button>) : <p className="text-xs leading-relaxed text-muted">{t("assistant.emptyHistory")}</p>}</div>
      <div className="mt-6 rounded-xl border border-line bg-surface p-3"><p className="text-xs font-semibold">{config.data?.generation_ready ? "AI connected" : "AI not connected"}</p><p className="mt-1 text-2xs leading-relaxed text-muted">{config.data?.local_provider ? "Runs on this laptop. No paid API." : "Source-based replies. Check the cited evidence."}</p></div>
    </aside>
    <section aria-label="Assistant chat" className="flex h-[calc(100dvh-9rem)] min-h-[540px] max-h-[1000px] min-w-0 flex-col overflow-hidden bg-surface">
      <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line px-4 py-4 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-2xl bg-forest text-lime"><Bot aria-hidden className="h-6 w-6" /></span>
          <div><h1 className="font-heading text-lg font-extrabold">CS Assistant</h1><p className="mt-0.5 flex items-center gap-1.5 text-xs text-muted"><span aria-hidden className={`h-1.5 w-1.5 rounded-full ${config.data?.generation_ready ? "bg-fresh" : "bg-amber"}`} />{config.data ? config.data.generation_ready ? config.data.local_provider ? "Local AI · On this laptop" : "AI · Source-grounded" : config.data.generation_enabled ? "AI unavailable · Document fallback" : "Documents only · AI not connected" : config.isError ? "Mode unavailable" : "Checking connection…"}</p></div>
        </div>
        <div className="flex items-center gap-2">
          <details className="relative"><summary aria-label="Conversation history" title="Conversation history" className="flex cursor-pointer list-none items-center rounded-xl border border-line p-2.5 text-muted"><History aria-hidden className="h-4 w-4" /></summary>
            <div className="absolute right-0 top-11 z-20 w-64 rounded-xl border border-line bg-surface p-3 shadow-raised"><p className="mb-2 text-xs font-semibold">Recent chats on this page</p>{chats.length ? chats.map((chat) => <button key={chat.id} type="button" disabled={busy} onClick={(event) => { restore(chat.id); event.currentTarget.closest("details")?.removeAttribute("open"); }} className="mb-1 block w-full truncate rounded-lg p-2 text-left text-xs hover:bg-canvas">{chat.messages[0]?.question}</button>) : <p className="text-xs text-muted">Start a new chat to save this conversation here.</p>}<p className="mt-2 text-2xs text-muted">Up to 5 chats. Cleared when you leave this page.</p></div>
          </details>
          <button type="button" aria-label="New chat" title="New conversation" disabled={busy} onClick={clear} className="flex items-center gap-2 rounded-xl border border-line px-3 py-2 text-xs font-semibold hover:bg-canvas disabled:opacity-40"><Plus aria-hidden className="h-4 w-4" /><span className="hidden sm:inline">New chat</span></button>
        </div>
      </header>
      <div ref={conversation} role="region" aria-label="Chat messages" aria-busy={busy} tabIndex={0} className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-6 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary sm:px-6">
        {!messages.length && !busy && <div className="mx-auto flex max-w-xl flex-col items-center py-2 text-center sm:py-6">
          <span className="mb-4 grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-forest to-primary text-lime shadow-card"><MessageSquare aria-hidden className="h-7 w-7" /></span>
          <h2 className="font-heading text-2xl font-extrabold tracking-tight sm:text-3xl">{t("assistant.welcome")}</h2>
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted">{t("assistant.intro")}</p>
          <button type="button" onClick={openDocuments} className="mt-5 flex items-center gap-2 rounded-full border border-primary/20 bg-mint px-4 py-2.5 text-sm font-semibold text-primary"><Paperclip aria-hidden className="h-4 w-4" />{t("assistant.choose")}</button>
          <div className="mt-5 grid w-full gap-2 sm:grid-cols-3">{([
            [t("assistant.ussdLabel"), t("assistant.ussdQuestion")],
            [t("assistant.rainLabel"), t("assistant.rainQuestion")],
            [t("assistant.smsLabel"), t("assistant.smsQuestion")],
          ] as const).map(([label, example]) => <button key={example} aria-label={example} type="button" onClick={() => { setQuestion(example); input.current?.focus(); }} className="rounded-xl border border-line bg-canvas px-3 py-3 text-left text-xs transition hover:border-primary hover:bg-mint"><span className="font-bold text-primary">{label}</span><span className="mt-1 block leading-relaxed text-muted">{example}</span></button>)}</div>
          <p className="mt-4 text-xs text-muted">{config.data?.generation_ready ? t("assistant.validated") : t("assistant.offline")}</p>
        </div>}
        <ol aria-label="Conversation" className="space-y-6">{messages.map(({ id, question: prompt, result }) => <li key={id} className="space-y-4">
          <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-forest px-4 py-3 text-sm leading-relaxed text-white"><span className="sr-only">You: </span>{prompt}</div>
          <div className="flex items-start gap-2 sm:gap-3">
            <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-mint text-primary"><Bot aria-hidden className="h-5 w-5" /></span>
            <div className="min-w-0 max-w-[90%] flex-1">
              <p className="mb-2 text-xs font-bold text-primary">CS Assistant</p>
              <div className="rounded-2xl rounded-tl-sm bg-canvas px-4 py-3">
                <p className="whitespace-pre-wrap break-words text-sm leading-7">{result.answer}</p>
                <p className="mt-3 text-2xs text-muted">{result.mode === "generated" ? t("assistant.generatedMode") : result.mode === "documents" ? t("assistant.documentsMode") : result.mode === "privacy_refusal" ? t("assistant.privacyMode") : result.mode === "conversation" ? t("assistant.guidanceMode") : t("assistant.noEvidence")}</p>
                {result.notice && <p className="mt-2 text-xs text-muted">{result.notice}</p>}
              </div>
              {result.sources.length > 0 && <details className="mt-3 text-xs">
                <summary className="cursor-pointer font-semibold text-primary">{t("assistant.sources")} ({result.sources.length})</summary>
                <div className="mt-2 space-y-2">{result.sources.map((source) => <details key={source.id} className="rounded-xl border border-line p-3">
                  <summary className="cursor-pointer font-semibold">[{source.id}] {source.title}</summary>
                  <p className="mt-2 whitespace-pre-wrap leading-relaxed">{source.text}</p>
                  <p className="mt-2 break-words text-2xs text-muted">Reference: {source.reference} · Revision: {source.revision}{source.page ? ` · Page/section: ${source.page}` : ""}{source.heading ? ` · ${source.heading}` : ""} · {source.classification ?? "engineering"}{source.language ? ` · ${source.language}` : ""}</p>
                </details>)}</div>
              </details>}
              <AnswerActions answer={result.answer} />
            </div>
          </div>
        </li>)}</ol>
        {busy && <div className="mt-6 space-y-4">
          <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-forest px-4 py-3 text-sm text-white">{pending}</div>
          <p role="status" className="flex items-center gap-2 text-sm text-muted"><Bot aria-hidden className="h-5 w-5 text-primary" /><span className="motion-safe:animate-pulse">{t("assistant.searching")}</span></p>
        </div>}
      </div>
      <div className="shrink-0 border-t border-line bg-surface px-4 pb-3 pt-3 sm:px-6">
        {config.data?.generation_enabled && !config.data.local_provider && <p className="mb-2 text-xs text-muted">AI mode sends your question and retrieved excerpts to the configured AI provider. Check its source quotations.</p>}
        {selectedReferences.length > 0 && <button type="button" onClick={openDocuments} className="mb-2 flex items-center gap-2 rounded-full bg-mint px-3 py-1 text-xs font-semibold text-primary"><FileText aria-hidden className="h-3 w-3" />{selectedReferences.length} document{selectedReferences.length > 1 ? "s" : ""} selected · Change</button>}
        {config.isError && <p role="alert" className="mb-2 text-xs text-critical">Could not load assistant settings. <button type="button" onClick={() => void config.refetch()} className="underline">Retry settings</button></p>}
        {error && <p role="alert" className="mb-2 text-sm text-critical">{error}</p>}
        <p role="status" aria-live="polite" className="sr-only">{busy ? "Searching platform guidance" : messages.length ? "Answer ready" : "Ready for your question"}</p>
        <form onSubmit={ask}>
          <div className="flex items-end gap-2 rounded-2xl border border-line bg-canvas p-2 focus-within:border-primary focus-within:ring-1 focus-within:ring-primary">
            <button type="button" aria-label="Attach or choose documents" title="Documents" disabled={busy} onClick={openDocuments} className="mb-1 rounded-xl p-2 text-muted hover:bg-mint hover:text-primary"><Paperclip aria-hidden className="h-5 w-5" /></button>
            <label htmlFor="assistant-question" className="sr-only">{t("assistant.question")}</label>
            <textarea ref={input} id="assistant-question" placeholder={t("assistant.placeholder")} value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} required minLength={3} maxLength={1200} disabled={busy} rows={2} className="max-h-32 min-h-12 w-full resize-none border-0 bg-transparent px-2 py-2 text-sm focus:outline-none focus:ring-0" />
            <button type="submit" aria-label={t("assistant.send")} title="Send message" disabled={busy || !config.data || question.trim().length < 3} className="mb-1 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-white transition hover:bg-primary-strong disabled:opacity-40"><ArrowUp aria-hidden className="h-5 w-5" /></button>
          </div>
        </form>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-2xs text-muted">
          <span>{t("assistant.safety")}</span>
          <details className="relative"><summary className="flex cursor-pointer list-none items-center gap-1 rounded px-1 py-1 hover:text-primary"><Settings2 aria-hidden className="h-3 w-3" />{t("assistant.options")}</summary>
            <div className="absolute bottom-8 right-0 z-10 w-72 space-y-3 rounded-xl border border-line bg-surface p-4 text-xs shadow-raised">
              <label className="block">{t("assistant.language")}<select aria-label={t("assistant.language")} value={language} disabled={busy} onChange={(event) => setLanguage(event.target.value)} className="mt-1 w-full rounded-lg border border-line p-2"><option value="auto">{t("assistant.autoLanguage")}</option><option value="en">English</option><option value="rw">Kinyarwanda · pending native review</option></select></label>
              <label className="flex items-start gap-2"><input type="checkbox" checked={useHistory} disabled={busy} onChange={(event) => setUseHistory(event.target.checked)} />{t("assistant.followups")}</label>
              <p>{t("assistant.memory")}</p>
              <p>{t("assistant.provider")}</p>
            </div>
          </details>
        </div>
      </div>
    </section>
    <dialog ref={documentDialog} aria-label="Document workspace" onClose={() => setDocumentsOpen(false)} className="max-h-[85dvh] w-[92vw] max-w-3xl overflow-y-auto rounded-2xl border border-line bg-surface p-0 text-ink shadow-raised backdrop:bg-forest/50">
      {documentsOpen && <DocumentWorkspace selected={selectedReferences} onChange={setSelectedReferences} isAdmin={role === "administrator"} uploadsEnabled={config.data?.uploads_enabled ?? false} onClose={closeDocuments} onSummarize={() => { closeDocuments(); setQuestion("Summarize the selected document."); input.current?.focus(); }} />}
    </dialog>
  </div>;
}
