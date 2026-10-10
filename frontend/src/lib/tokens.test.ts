import { tokenColor } from "./tokens";

describe("tokenColor", () => {
  it("returns comma-separated colours that Mapbox GL and Recharts both accept", () => {
    expect(tokenColor("forest")).toBe("rgb(6, 78, 59)");
    expect(tokenColor("amber", 0.5)).toBe("rgba(146, 94, 8, 0.5)");
  });
});
