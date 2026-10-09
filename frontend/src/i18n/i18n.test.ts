import { en } from "./en";
import { translate } from "./index";
import { rw } from "./rw";

describe("translate", () => {
  it("uses Kinyarwanda where available and falls back to English", () => {
    expect(translate("rw", "nav.overview")).toBe("Incamake");
    expect(translate("rw", "section.recentNote")).toBe(en["section.recentNote"]);
  });

  it("fills placeholders", () => {
    expect(translate("en", "filter.days", { n: 30 })).toBe("Last 30 days");
  });

  it("has no Kinyarwanda key without an English source", () => {
    for (const key of Object.keys(rw)) expect(en).toHaveProperty(key);
  });
});
