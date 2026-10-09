import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { SessionProvider } from "@/app/providers/SessionProvider";
import { AppRoutes } from "@/app/routing/AppRoutes";
import { ROUTER_FUTURE } from "@/app/routing/future";
import { I18nProvider } from "@/i18n";
import { ApiError } from "@/services/api/client";
import "@/styles/index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: true,
      // Retry network hiccups, never "forbidden" or "not found".
      retry: (count, error) => count < 2 && (!(error instanceof ApiError) || error.status === 0 || error.status >= 500),
    },
  },
});

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root element");

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <BrowserRouter basename="/app" future={ROUTER_FUTURE}>
          <SessionProvider>
            <AppRoutes />
          </SessionProvider>
        </BrowserRouter>
      </I18nProvider>
    </QueryClientProvider>
  </StrictMode>,
);
