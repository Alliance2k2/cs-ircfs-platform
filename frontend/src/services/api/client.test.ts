import { z } from "zod";
import { ApiError, apiGet, query } from "./client";

const schema = z.object({ count: z.number() });

describe("apiGet", () => {
  it("returns data that matches the schema, sending the session cookie", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ count: 3 }), { status: 200 }));
    await expect(apiGet("things", schema)).resolves.toEqual({ count: 3 });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/things", expect.objectContaining({ credentials: "same-origin" }));
  });

  it("rejects data in an unexpected shape instead of rendering it", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ count: "three" }), { status: 200 }));
    await expect(apiGet("things", schema)).rejects.toThrow("unexpected format");
  });

  it("carries the message and status from the server", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Your role cannot use this feature" }), { status: 403 }));
    const error = await apiGet("things", schema).catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
    expect((error as ApiError).message).toBe("Your role cannot use this feature");
  });

  it("reports an unreachable platform as status 0", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const error = (await apiGet("things", schema).catch((reason: unknown) => reason)) as ApiError;
    expect(error.unreachable).toBe(true);
  });
});

describe("query", () => {
  it("keeps only defined values", () => {
    expect(query({ days: 30, scheme_id: null, sector_id: undefined, q: "" })).toBe("?days=30");
    expect(query({})).toBe("");
  });
});
