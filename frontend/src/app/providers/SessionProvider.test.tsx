import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { SessionProvider, useSession } from "./SessionProvider";
import { I18nProvider } from "@/i18n";

function Identity() {
  const session = useSession();
  return <p>{session.development ? "Local demo administrator" : session.role}</p>;
}

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><I18nProvider><SessionProvider><Identity /></SessionProvider></I18nProvider></QueryClientProvider>);
}

it("honors explicit local demo access even when an old browser session would be refused", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const config = String(url).endsWith("/auth/config");
    return new Response(JSON.stringify(config ? { development_bypass: true, google_client_id: null } : { detail: "This account is suspended" }), { status: config ? 200 : 403 });
  });
  try {
    const view = mount();
    expect(await screen.findByText("Local demo administrator")).toBeVisible();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/auth/me"))).toBe(false);
    view.unmount();
  } finally { fetchMock.mockRestore(); }
});

it("refuses a suspended session when local demo access is disabled", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const config = String(url).endsWith("/auth/config");
    return new Response(JSON.stringify(config ? { development_bypass: false, google_client_id: null } : { detail: "This account is suspended" }), { status: config ? 200 : 403 });
  });
  try {
    const view = mount();
    expect(await screen.findByText("This account is suspended")).toBeVisible();
    expect(screen.queryByText("Local demo administrator")).not.toBeInTheDocument();
    view.unmount();
  } finally { fetchMock.mockRestore(); }
});
