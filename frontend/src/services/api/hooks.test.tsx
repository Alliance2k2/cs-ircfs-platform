import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { z } from "zod";
import { useApi } from "./hooks";

it("keeps full scheme fields when a compact picker loads before an editing form", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([
    { id: 1, name: "Scheme", coverage_sector_ids: [2, 3], baseline_source: "Document A" },
  ]), { status: 200, headers: { "Content-Type": "application/json" } }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  try {
    const compact = renderHook(() => useApi("irrigation-schemes", z.array(z.object({ id: z.number(), name: z.string() }))), { wrapper });
    await waitFor(() => expect(compact.result.current.isSuccess).toBe(true));
    const detailed = renderHook(() => useApi("irrigation-schemes", z.array(z.object({
      id: z.number(), coverage_sector_ids: z.array(z.number()), baseline_source: z.string(),
    }))), { wrapper });
    await waitFor(() => expect(detailed.result.current.isSuccess).toBe(true));
    expect(detailed.result.current.data?.[0]).toMatchObject({ coverage_sector_ids: [2, 3], baseline_source: "Document A" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    compact.unmount();
    detailed.unmount();
  } finally {
    client.clear();
    fetchMock.mockRestore();
  }
});
