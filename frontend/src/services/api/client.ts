import type { z } from "zod";

/** The FastAPI base path. The app is always served from the same origin as the API. */
export const API_BASE = "/api/v1";

/** A failed request, with the HTTP status (0 when the server could not be reached). */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  get unreachable(): boolean {
    return this.status === 0;
  }
}

function detailMessage(body: unknown, status: number): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item: { loc?: unknown[]; msg?: string }) => `${String(item.loc?.at(-1) ?? "")}: ${item.msg ?? ""}`).join("; ");
    }
  }
  return `Request failed (${status})`;
}

/**
 * GET a JSON resource and validate it against a Zod schema, so an unexpected API shape
 * fails loudly here instead of rendering wrong figures.
 */
export async function apiGet<T>(path: string, schema: z.ZodType<T, z.ZodTypeDef, unknown>, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/${path}`, { credentials: "same-origin", headers: { Accept: "application/json" }, signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError("The platform could not be reached.", 0);
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(detailMessage(body, response.status), response.status);
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    console.error(`Unexpected response from ${path}`, parsed.error.issues);
    throw new ApiError("The platform sent data in an unexpected format.", response.status);
  }
  return parsed.data;
}

/** Build a query string from defined values only. */
export function query(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
