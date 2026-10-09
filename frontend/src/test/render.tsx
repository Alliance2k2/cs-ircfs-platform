import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { ROUTER_FUTURE } from "@/app/routing/future";
import { I18nProvider, type Language } from "@/i18n";

/** Render inside the app's providers, with a fresh query cache and no retries. */
export function renderWithProviders(ui: ReactElement, { lang = "en", route = "/" }: { lang?: Language; route?: string } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: false } } });
  return render(
    <QueryClientProvider client={client}>
      <I18nProvider initial={lang}>
        <MemoryRouter initialEntries={[route]} future={ROUTER_FUTURE}>
          {ui}
        </MemoryRouter>
      </I18nProvider>
    </QueryClientProvider>,
  );
}

/** A fetch stub answering JSON per path prefix (the part after /api/v1/). */
export function stubApi(routes: Record<string, unknown>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input).replace(/^.*\/api\/v1\//, "");
    const match = Object.keys(routes).find((prefix) => path.startsWith(prefix));
    if (match === undefined) return new Response(JSON.stringify({ detail: "Not found" }), { status: 404 });
    return new Response(JSON.stringify(routes[match]), { status: 200, headers: { "Content-Type": "application/json" } });
  });
}
