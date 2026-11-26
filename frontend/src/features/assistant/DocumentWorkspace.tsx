import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText, RefreshCw, Upload, X } from "lucide-react";
import { z } from "zod";
import { apiGet } from "@/services/api/client";
import { KnowledgePanel } from "./KnowledgePanel";

const sourcesSchema = z.array(z.object({ reference: z.string(), title: z.string(), status: z.string(), language: z.string() }));

export function DocumentWorkspace({ selected, onChange, isAdmin, uploadsEnabled, onClose, onSummarize }: {
  selected: string[]; onChange: (values: string[]) => void; isAdmin: boolean; uploadsEnabled: boolean; onClose: () => void; onSummarize?: () => void;
}) {
  const [search, setSearch] = useState("");
  const [manage, setManage] = useState(false);
  const library = useQuery({ queryKey: ["assistant", "sources"], queryFn: ({ signal }) => apiGet("assistant/sources", sourcesSchema, signal), retry: false });
  const rows = library.data?.filter((row) => row.title.toLocaleLowerCase().includes(search.toLocaleLowerCase())) ?? [];
  useEffect(() => {
    if (!library.data) return;
    const allowed = new Set(library.data.map((row) => row.reference));
    const retained = selected.filter((reference) => allowed.has(reference));
    if (retained.length !== selected.length) onChange(retained);
  }, [library.data, selected, onChange]);
  return <section aria-label="Documents" className="space-y-5 p-5 sm:p-7">
    <header className="flex items-start justify-between gap-3"><div><p className="mb-1 text-xs font-semibold uppercase tracking-widest text-muted">Your source library</p><h2 className="text-2xl font-extrabold">Chat with documents</h2><p className="mt-2 text-sm text-muted">Choose reviewed sources to focus your next question.</p></div><button autoFocus type="button" aria-label="Close documents" onClick={onClose} className="rounded-xl border border-line p-2"><X aria-hidden className="h-5 w-5" /></button></header>
    <div className="flex flex-wrap gap-2"><button type="button" onClick={() => onChange([])} className="rounded-xl border border-line px-3 py-2 text-sm">Use all available sources</button><button type="button" aria-label="Refresh document library" onClick={() => void library.refetch()} className="rounded-xl border border-line p-2"><RefreshCw aria-hidden className="h-4 w-4" /></button>{isAdmin && <button type="button" onClick={() => setManage((value) => !value)} aria-expanded={manage} className="ml-auto flex items-center gap-2 rounded-xl bg-primary px-3 py-2 text-sm font-semibold text-white"><Upload aria-hidden className="h-4 w-4" />Upload &amp; review</button>}</div>
    <label className="block text-xs font-semibold text-muted">Find a document<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by title…" className="mt-2 w-full rounded-xl border border-line bg-canvas p-3 text-sm text-ink" /></label>
    {library.isPending && <p role="status" className="text-sm text-muted">Loading reviewed sources…</p>}
    {library.isError && <p role="alert" className="text-sm text-critical">Could not load documents. Use Refresh to try again.</p>}
    {library.isSuccess && !rows.length && <p className="rounded-xl bg-canvas p-4 text-sm text-muted">No reviewed documents match this search.</p>}
    <div className="grid max-h-72 gap-2 overflow-y-auto sm:grid-cols-2">{rows.map((row) => <label key={row.reference} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 ${selected.includes(row.reference) ? "border-primary bg-mint" : "border-line"}`}><input type="checkbox" className="mt-1" checked={selected.includes(row.reference)} disabled={!selected.includes(row.reference) && selected.length >= 20} onChange={(event) => onChange(event.target.checked ? [...selected, row.reference] : selected.filter((value) => value !== row.reference))} /><FileText aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><span className="text-sm font-semibold">{row.title}<span className="mt-1 block text-xs font-normal text-muted">{row.status === "packaged" ? "Platform guidance" : "Reviewed upload"} · {row.language.toUpperCase()}</span></span></label>)}</div>
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4"><p className="text-xs text-muted">{selected.length ? `${selected.length} selected` : "All authorized sources"}. Pending uploads are excluded.</p><div className="flex gap-2">{selected.length > 0 && onSummarize && <button type="button" onClick={onSummarize} className="rounded-xl border border-line px-3 py-2 text-sm font-semibold">Summarize selection</button>}<button type="button" onClick={onClose} className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-white">Use documents</button></div></div>
    {isAdmin && !uploadsEnabled && <p className="rounded-xl bg-amber-soft p-3 text-xs text-amber">Uploads await approval of the local extraction environment. Existing reviewed sources remain available.</p>}
    {!isAdmin && <p className="text-xs text-muted">An administrator can upload and approve additional documents.</p>}
    {manage && <div className="border-t border-line pt-4"><KnowledgePanel onSourcesChanged={() => { void library.refetch(); }} /></div>}
  </section>;
}
