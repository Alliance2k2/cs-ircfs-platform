import { screen } from "@testing-library/react";
import { overview } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";
import { ModuleGrid } from "./ModuleGrid";
import { OverviewHero } from "./OverviewHero";

describe("OverviewHero", () => {
  it("greets the planner and shows the headline numbers", () => {
    renderWithProviders(<OverviewHero data={overview()} />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/Good (morning|afternoon|evening), Planner/);
    expect(screen.getByText("126")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Act Now/ })).toHaveAttribute("href", "/actions");
  });

  it("hides the Act Now shortcut from monitors", () => {
    renderWithProviders(<OverviewHero data={overview()} />, { session: { account: null, role: "citizen_science_monitor", development: false } });
    expect(screen.queryByRole("link", { name: /Open Act Now/ })).not.toBeInTheDocument();
  });
});

describe("ModuleGrid", () => {
  it("links every workspace with its live count", () => {
    renderWithProviders(<ModuleGrid data={overview()} />);
    expect(screen.getByRole("link", { name: /Act now/ })).toHaveTextContent("11"); // 7 cases + 4 grievances
    expect(screen.getByRole("link", { name: /Map & observations/ })).toHaveTextContent("3 / 15");
  });
});
