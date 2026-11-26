/** Missing or malformed observations remain missing; zero is a measured value. */
export function rainfallMillimetres(status: string | null): number | null {
  if (status === null) return null;
  const match = /^\s*(\d+(?:\.\d+)?)\s*mm\s*$/i.exec(status);
  if (!match) return null;
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}
