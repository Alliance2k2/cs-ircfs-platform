import { describe, expect, it } from "vitest";
import { rainfallMillimetres } from "./observations";

describe("mapped rainfall evidence", () => {
  it("keeps dry measured readings distinct from missing or malformed data", () => {
    expect(rainfallMillimetres("0 mm")).toBe(0);
    expect(rainfallMillimetres("12.5 mm")).toBe(12.5);
    for (const value of [null, "", "unknown", "12 bogus", "-2 mm", "Infinity mm"]) {
      expect(rainfallMillimetres(value)).toBeNull();
    }
  });
});
