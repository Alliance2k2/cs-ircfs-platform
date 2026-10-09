import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { SessionContext, type Session } from "@/app/providers/SessionProvider";
import { ROUTER_FUTURE } from "@/app/routing/future";
import { I18nProvider, type Language } from "@/i18n";

/** Render inside the app's providers, with a fresh query cache and no retries. */
const PLANNER: Session = { account: null, role: "district_planner", development: false };

export function renderWithProviders(
  ui: ReactElement,
  { lang = "en", route = "/", session = PLANNER }: { lang?: Language; route?: string; session?: Session } = {},
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchInterval: false } } });
  return render(
    <QueryClientProvider client={client}>
      <I18nProvider initial={lang}>
        <SessionContext.Provider value={session}>
          <MemoryRouter initialEntries={[route]} future={ROUTER_FUTURE}>
            {ui}
          </MemoryRouter>
        </SessionContext.Provider>
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
