import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { metric } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  it("shows the value with its unit, period and source", () => {
    renderWithProviders(<MetricCard metric={metric()} />);
    expect(screen.getByText("126")).toBeInTheDocument();
    expect(screen.getByText("reports")).toBeInTheDocument();
    expect(screen.getByText("Last 30 days")).toBeInTheDocument();
    expect(screen.getByText("Citizen reports, unverified")).toBeInTheDocument();
  });

  it("puts the percent sign on the number", () => {
    renderWithProviders(<MetricCard metric={metric({ value: 50, unit: "%" })} />);
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("says when there is no data instead of showing zero", () => {
    renderWithProviders(<MetricCard metric={metric({ value: null, source: "missing", note: "No rain-gauge readings" })} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.getByText("Not enough data")).toBeInTheDocument();
    expect(screen.getByText("No rain-gauge readings")).toBeInTheDocument();
  });

  it("reveals the definition on request", async () => {
    renderWithProviders(<MetricCard metric={metric()} />);
    const definition = screen.getByText(/reports received/);
    expect(definition).not.toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /What this means/ }));
    expect(definition).toBeVisible();
  });
});
