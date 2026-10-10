import { CheckCircle2, AlertTriangle, X } from "lucide-react";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { cx } from "@/lib/cx";

type Kind = "success" | "error";
interface Toast {
  id: number;
  kind: Kind;
  message: string;
}
interface ToastApi {
  success: (message: string) => void;
  error: (message: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

/** Short confirmations ("Case assigned") and errors, announced to screen readers. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const remove = useCallback((id: number) => setToasts((items) => items.filter((item) => item.id !== id)), []);
  const push = useCallback(
    (kind: Kind, message: string) => {
      const id = Date.now() + Math.random();
      setToasts((items) => [...items.slice(-3), { id, kind, message }]);
      window.setTimeout(() => remove(id), kind === "error" ? 8000 : 4500);
    },
    [remove],
  );
  const api = useMemo<ToastApi>(() => ({ success: (m) => push("success", m), error: (m) => push("error", m) }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.kind === "error" ? "alert" : "status"}
            className={cx(
              "pointer-events-auto flex items-start gap-2.5 rounded-control border px-4 py-3 text-sm font-semibold shadow-raised",
              toast.kind === "success" ? "border-fresh/40 bg-mint text-primary-strong" : "border-critical/30 bg-critical-soft text-critical",
            )}
          >
            {toast.kind === "success" ? <CheckCircle2 aria-hidden className="mt-0.5 h-4 w-4 shrink-0" /> : <AlertTriangle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />}
            <span className="flex-1">{toast.message}</span>
            <button type="button" onClick={() => remove(toast.id)} className="-m-1 rounded p-1 opacity-70 hover:opacity-100">
              <X aria-hidden className="h-4 w-4" />
              <span className="sr-only">Dismiss</span>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used inside <ToastProvider>");
  return value;
}
