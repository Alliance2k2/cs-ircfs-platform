import { useState, type FormEvent } from "react";
import { z } from "zod";
import { apiSend } from "@/services/api/client";
import { useSession } from "@/app/providers/SessionProvider";
import { KnowledgePanel } from "./KnowledgePanel";

const schema = z.object({ answer: z.string(), mode: z.string(), notice: z.string().optional(), sources: z.array(z.object({ id: z.string(), title: z.string(), text: z.string(), reference: z.string(), revision: z.string(), page: z.number().optional(), classification: z.string().optional(), language: z.string().optional() })) });
type Answer = z.infer<typeof schema>;

function AnswerActions({ answer }: { answer: string }) {
  const [status, setStatus] = useState("");
  const [voted, setVoted] = useState(false);
  const [sending, setSending] = useState(false);
  async function copy() {
    try { await navigator.clipboard.writeText(answer); setStatus("Answer copied."); }
    catch { setStatus("Clipboard unavailable. Select the answer text to copy it."); }
  }
  async function feedback(vote: "helpful" | "unhelpful") {
    setSending(true);
    try { await apiSend("POST", "assistant/feedback", { vote }); setVoted(true); setStatus("Feedback recorded without your question or answer."); }
    catch { setStatus("Feedback could not be recorded. Please try again."); }
    finally { setSending(false); }
  }
  return <div className="mt-3 space-y-2"><div className="flex flex-wrap gap-3 text-sm">
    <button type="button" onClick={() => void copy()} className="rounded-control border border-line p-2">Copy answer</button>
    <button type="button" disabled={voted || sending} onClick={() => void feedback("helpful")} className="rounded-control border border-line p-2">Helpful</button>
    <button type="button" disabled={voted || sending} onClick={() => void feedback("unhelpful")} className="rounded-control border border-line p-2">Not helpful</button>
  </div><p role="status" className="text-xs text-muted">{status}</p></div>;
}

export function AssistantPage() {
  const { role } = useSession();
  const [language, setLanguage] = useState("auto");
  const [useHistory, setUseHistory] = useState(true);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<{ question: string; result: Answer }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function ask(event: FormEvent) {
    event.preventDefault();
    if (busy || question.trim().length < 3) return;
    setBusy(true); setError("");
    const submitted = question.trim();
    try {
      const result = await apiSend("POST", "assistant/ask", { question: submitted, language, history: useHistory ? messages.slice(-3).map((message) => message.question) : [] }, schema);
      setMessages((previous) => [...previous.slice(-9), { question: submitted, result }]);
      setQuestion("");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "The assistant could not be reached."); }
    finally { setBusy(false); }
  }
  return <div className="mx-auto max-w-3xl space-y-5">
    <header><h1 className="text-2xl font-extrabold">Document assistant</h1>
      <p className="mt-2 text-sm text-muted">Ask about platform procedures. Answers use engineering-reviewed excerpts, not live participant records.</p>
      <p className="mt-2 text-sm text-muted">Do not enter personal information or credentials. Check sources before acting. Follow-ups may use the last three questions on this page. Kinyarwanda retrieval is experimental and requires native review; excerpts retain their source language.</p></header>
    <p className="text-sm text-muted">Local document lookup is the default. If an administrator enables AI generation, questions and retrieved excerpts are sent to an external AI provider.</p>
    <div className="flex flex-wrap gap-2">{["How do I change the USSD language?", "How are rainfall observations verified?", "What should I do with an unknown delivery?"].map((example) =>
      <button key={example} disabled={busy} type="button" onClick={() => setQuestion(example)} className="rounded-control border border-line bg-surface p-2 text-sm">{example}</button>)}</div>
    <ol aria-label="Conversation" className="space-y-4">{messages.map(({ question: prompt, result }, index) => <li key={index} className="rounded-card border border-line bg-surface p-5">
      <h2 className="font-bold">{prompt}</h2>
      <p className="my-2 text-xs text-muted">{result.mode === "generated" ? "AI-generated answer — verify sources" : "Document lookup — no AI-generated answer"}</p>
      <p className="whitespace-pre-wrap text-sm">{result.answer}</p>
      {result.notice && <p className="mt-2 text-sm text-muted">{result.notice}</p>}
      {result.sources.map((source) => <details key={source.id} className="mt-3 border-t border-line pt-2">
        <summary className="cursor-pointer text-sm font-semibold">[{source.id}] {source.title}</summary>
        <p className="mt-2 text-sm">{source.text}</p><p className="mt-2 break-words text-xs text-muted">Reference: {source.reference} · Excerpt revision: {source.revision}{source.page ? ` · Page/section: ${source.page}` : ""} · {source.classification ?? "engineering"}{source.language ? ` · ${source.language}` : ""}</p>
      </details>)}
      <AnswerActions answer={result.answer} />
    </li>)}</ol>
    {error && <p role="alert" className="text-sm text-critical">{error}</p>}
    <form onSubmit={ask} className="space-y-3">
      <label className="block text-sm">Question language<select aria-label="Question language" value={language} disabled={busy} onChange={(event) => setLanguage(event.target.value)} className="ml-2 rounded-control border border-line p-2"><option value="auto">Detect automatically (experimental)</option><option value="en">English</option><option value="rw">Kinyarwanda — pending native review</option></select></label>
      <label className="block text-sm"><input type="checkbox" checked={useHistory} disabled={busy} onChange={(event) => setUseHistory(event.target.checked)} className="mr-2" />Use recent questions for follow-ups</label>
      <label htmlFor="assistant-question" className="block font-semibold">Your question</label>
      <textarea id="assistant-question" value={question} onChange={(event) => setQuestion(event.target.value)} required minLength={3} maxLength={1200} disabled={busy} rows={3} className="w-full rounded-control border border-line bg-surface p-3" />
      <div className="flex items-center gap-3"><button type="submit" disabled={busy || question.trim().length < 3} className="rounded-control bg-primary px-4 py-2 font-semibold text-white disabled:opacity-50">{busy ? "Searching…" : "Ask assistant"}</button>
        <button type="button" disabled={busy} onClick={() => { setMessages([]); setError(""); setQuestion(""); }} className="rounded-control border border-line px-4 py-2">Clear conversation</button></div>
      <p role="status" className="text-sm text-muted">{busy ? "Searching platform documents…" : messages.length ? "Answer ready." : "Conversation clears when you leave this page."}</p>
    </form>
    {role === "administrator" && <KnowledgePanel />}
  </div>;
}
