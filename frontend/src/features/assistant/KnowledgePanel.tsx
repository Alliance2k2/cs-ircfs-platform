import { useState, type FormEvent } from "react";
import { z } from "zod";
import { apiGet, apiSend } from "@/services/api/client";

const documentSchema = z.object({ document_id: z.string(), version_id: z.string(), title: z.string(), language: z.string(), classification: z.string(), status: z.string(), revision: z.number(), roles: z.array(z.string()), sector_ids: z.array(z.number()) });
type Document = z.infer<typeof documentSchema>;
const previewSchema = z.array(z.object({ page: z.number(), heading: z.string(), text: z.string() }));
const uploadSchema = z.object({ status: z.string(), duplicate: z.boolean() });
const button = "rounded-control border border-line px-3 py-2 text-sm disabled:opacity-50";

export function KnowledgePanel() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selected, setSelected] = useState<Document | null>(null);
  const [preview, setPreview] = useState<z.infer<typeof previewSchema>>([]);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("en");
  const [classification, setClassification] = useState("engineering");
  const [roles, setRoles] = useState("administrator,district_officer,district_planner");
  const [sectors, setSectors] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);
  const [reference, setReference] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  async function refresh() { setDocuments(await apiGet("assistant/documents", z.array(documentSchema))); }
  async function run(action: () => Promise<void>) {
    setBusy(true); setError(""); setStatus("");
    try { await action(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Knowledge operation failed."); }
    finally { setBusy(false); }
  }
  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || busy) return;
    await run(async () => {
      if (file.size > 5 * 1024 * 1024) throw new Error("Choose a document of at most 5 MiB.");
      const params = new URLSearchParams({ filename: file.name, title, language, classification, roles, sectors });
      if (updating) params.set("document_id", updating);
      const response = await fetch(`/api/v1/assistant/documents?${params}`, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/octet-stream" }, body: file });
      const body: unknown = await response.json();
      if (!response.ok) throw new Error(z.object({ detail: z.string() }).safeParse(body).data?.detail ?? "Upload failed.");
      const uploaded = uploadSchema.parse(body);
      setStatus(uploaded.duplicate ? `This content already exists with status: ${uploaded.status}.` : "Document extracted and indexed locally; approval is required before retrieval.");
      await refresh();
    });
  }
  return <section aria-label="Knowledge management" className="space-y-4 rounded-card border border-line bg-surface p-5">
    <h2 className="text-lg font-bold">Manage knowledge sources</h2>
    <p className="text-sm text-muted">Administrator only. Upload approved-for-review institutional procedures, engineering summaries or demonstration material. Never upload participant records, grievances, personal documents or credentials. Uploads remain disabled until the extraction environment is approved.</p>
    <button type="button" disabled={busy} className={button} onClick={() => void run(refresh)}>Load knowledge sources</button>
    <ul className="space-y-3">{documents.map((doc) => <li key={doc.version_id} className="border-t border-line pt-3">
      <p>{doc.title} · revision {doc.revision} · {doc.classification} · {doc.status}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button className={button} disabled={busy} type="button" onClick={() => void run(async () => { const chunks = await apiGet(`assistant/documents/${doc.version_id}/preview`, previewSchema); setSelected(doc); setPreview(chunks); setReference(""); })}>Review {doc.title} revision {doc.revision}</button>
        <button className={button} disabled={busy} type="button" onClick={() => { setUpdating(doc.document_id); setTitle(doc.title); setLanguage(doc.language); setClassification(doc.classification); setRoles(doc.roles.join(",")); setSectors(doc.sector_ids.join(",")); }}>Prepare new version</button>
        <button className={button} disabled={busy} type="button" onClick={() => void run(async () => { await apiSend("DELETE", `assistant/documents/${doc.document_id}`); setSelected(null); setPreview([]); await refresh(); setStatus("Document removed from retrieval; chunks and vectors deleted."); })}>Remove {doc.title} from retrieval</button>
      </div>
    </li>)}</ul>
    {selected && <div className="space-y-3 border-t border-line pt-3">
      <h3 className="font-bold">Review: {selected.title}, revision {selected.revision}</h3>
      <p className="text-xs text-muted">Preview shows at most 100 chunks. Page numbers for non-PDF formats are logical sections, not printed pages. Approval requires independent content, privacy, permission and provenance review.</p>
      {preview.map((chunk, index) => <details key={index}><summary>Page/section {chunk.page} {chunk.heading}</summary><p className="whitespace-pre-wrap text-sm">{chunk.text}</p></details>)}
      <label className="block">Review/approval reference<input value={reference} maxLength={200} onChange={(event) => setReference(event.target.value)} className="ml-2 rounded-control border border-line p-2" /></label>
      <button className={button} disabled={busy || selected.status !== "pending" || !reference.trim()} type="button" onClick={() => void run(async () => { await apiSend("POST", `assistant/documents/${selected.version_id}/approve`, { reference }); setSelected(null); setPreview([]); await refresh(); setStatus("Reviewed version approved for authorized retrieval."); })}>Approve reviewed version</button>
    </div>}
    <form aria-label="Knowledge source upload" onSubmit={(event) => void upload(event)} className="space-y-3 border-t border-line pt-3">
      <h3 className="font-bold">{updating ? "Upload a new version" : "Upload a source for review"}</h3>
      <label className="block">Source title<input required value={title} maxLength={200} disabled={!!updating} onChange={(event) => setTitle(event.target.value)} className="ml-2 rounded-control border border-line p-2" /></label>
      <label className="block">Source language<select value={language} disabled={!!updating} onChange={(event) => setLanguage(event.target.value)} className="ml-2 border border-line p-2"><option value="en">English</option><option value="rw">Kinyarwanda — requires native review</option><option value="fr">French — retrieval only</option></select></label>
      <label className="block">Source classification<select value={classification} disabled={!!updating} onChange={(event) => setClassification(event.target.value)} className="ml-2 border border-line p-2"><option value="engineering">Engineering summary</option><option value="institutional">Institutional document — approval required</option><option value="demonstration">Demonstration material</option></select></label>
      <label className="block">Allowed staff roles (comma separated)<input value={roles} disabled={!!updating} onChange={(event) => setRoles(event.target.value)} className="block w-full border border-line p-2" /></label>
      <label className="block">Required sector IDs (comma separated; empty for general procedures)<input value={sectors} disabled={!!updating} onChange={(event) => setSectors(event.target.value)} className="block w-full border border-line p-2" /></label>
      <label className="block">Document file<input type="file" required accept=".pdf,.docx,.txt,.md,.csv,.json" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="ml-2" /></label>
      <button type="submit" disabled={busy || !file} className={button}>Upload and index for review</button>
      {updating && <button type="button" className={button} onClick={() => { setUpdating(null); setTitle(""); }}>Cancel version update</button>}
    </form>
    {error && <p role="alert" className="text-critical">{error}</p>}
    <p role="status" className="text-sm text-muted">{busy ? "Processing knowledge source…" : status}</p>
  </section>;
}
