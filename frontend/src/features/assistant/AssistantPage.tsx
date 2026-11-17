import { useState, type FormEvent } from "react";
import { z } from "zod";
import { apiSend } from "@/services/api/client";

const schema = z.object({ answer: z.string(), mode: z.string(), notice: z.string().optional(), sources: z.array(z.object({ id: z.string(), title: z.string(), text: z.string(), reference: z.string(), revision: z.string() })) });
type Answer = z.infer<typeof schema>;

export function AssistantPage() {
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
      const result = await apiSend("POST", "assistant/ask", { question: submitted }, schema);
      setMessages((previous) => [...previous.slice(-9), { question: submitted, result }]);
      setQuestion("");
    } catch (failure) { setError(failure instanceof Error ? failure.message : "The assistant could not be reached."); }
    finally { setBusy(false); }
  }
  return <div className="mx-auto max-w-3xl space-y-5">
    <header><h1 className="text-2xl font-extrabold">Document assistant</h1>
      <p className="mt-2 text-sm text-muted">Ask about platform procedures. Answers use engineering-reviewed excerpts, not live participant records.</p>
      <p className="mt-2 text-sm text-muted">English pilot. Do not enter personal information or credentials. Check sources before acting. Each question is answered independently.</p></header>
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
        <p className="mt-2 text-sm">{source.text}</p><p className="mt-2 break-words text-xs text-muted">Reference: {source.reference} · Excerpt revision: {source.revision}</p>
      </details>)}
    </li>)}</ol>
    {error && <p role="alert" className="text-sm text-critical">{error}</p>}
    <form onSubmit={ask} className="space-y-3">
      <label htmlFor="assistant-question" className="block font-semibold">Your question</label>
      <textarea id="assistant-question" value={question} onChange={(event) => setQuestion(event.target.value)} required minLength={3} maxLength={1200} disabled={busy} rows={3} className="w-full rounded-control border border-line bg-surface p-3" />
      <div className="flex items-center gap-3"><button type="submit" disabled={busy || question.trim().length < 3} className="rounded-control bg-primary px-4 py-2 font-semibold text-white disabled:opacity-50">{busy ? "Searching…" : "Ask assistant"}</button>
        <button type="button" disabled={busy} onClick={() => { setMessages([]); setError(""); setQuestion(""); }} className="rounded-control border border-line px-4 py-2">Clear conversation</button></div>
      <p role="status" className="text-sm text-muted">{busy ? "Searching platform documents…" : messages.length ? "Answer ready." : "Conversation clears when you leave this page."}</p>
    </form>
  </div>;
}
