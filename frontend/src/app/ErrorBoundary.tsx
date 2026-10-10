import { AlertTriangle, RefreshCw } from "lucide-react";
import { Component, type ReactNode } from "react";
import { translate, type Language } from "@/i18n";

interface State {
  error: Error | null;
}

/** One broken page must not blank the whole app: show a clear message and a reload button. */
export class ErrorBoundary extends Component<{ children: ReactNode; lang: Language; resetKey?: string }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidUpdate(previous: { resetKey?: string }) {
    if (previous.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }

  componentDidCatch(error: Error) {
    console.error("Page error", error);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    const t = (key: Parameters<typeof translate>[1]) => translate(this.props.lang, key);
    return (
      <div role="alert" className="mx-auto mt-16 flex max-w-md flex-col items-center gap-3 rounded-card border border-line bg-surface p-8 text-center shadow-card">
        <AlertTriangle aria-hidden className="h-8 w-8 text-critical" />
        <h2 className="text-lg font-extrabold">{t("shell.errorTitle")}</h2>
        <p className="text-sm text-muted">{t("shell.errorBody")}</p>
        <button type="button" onClick={() => window.location.reload()} className="inline-flex items-center gap-2 rounded-control bg-primary px-4 py-2 text-sm font-semibold text-white">
          <RefreshCw aria-hidden className="h-4 w-4" />
          {t("shell.reload")}
        </button>
      </div>
    );
  }
}
