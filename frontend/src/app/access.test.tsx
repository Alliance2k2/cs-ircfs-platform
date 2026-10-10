import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { Sidebar } from "@/components/navigation/Sidebar";
import { renderWithProviders } from "@/test/render";
import type { Role } from "@/services/api/schemas";
import { canAccess } from "./access";

const session = (role: Role) => ({ account: null, role, development: false });

describe("canAccess", () => {
  it("mirrors the backend role checks", () => {
    expect(canAccess("cooperative_leader", "field")).toBe(true);
    expect(canAccess("cooperative_leader", "analyst")).toBe(false);
    expect(canAccess("citizen_science_monitor", "analyst")).toBe(true);
    expect(canAccess("citizen_science_monitor", "staff")).toBe(false);
    expect(canAccess("district_officer", "planner")).toBe(false);
    expect(canAccess("district_planner", "planner")).toBe(true);
    expect(canAccess("district_planner", "admin")).toBe(false);
    expect(canAccess("farmer", "all")).toBe(true);
    expect(canAccess("farmer", "field")).toBe(false);
  });
});

describe("Sidebar", () => {
  it("shows a monitor only the pages they can use", () => {
    renderWithProviders(<Sidebar open={false} onClose={() => {}} collapsed={false} onToggleCollapsed={() => {}} />, { session: session("citizen_science_monitor") });
    expect(screen.getByRole("link", { name: /Field reports/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Priority actions/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Administration/ })).not.toBeInTheDocument();
  });

  it("shows administrators the administration page", () => {
    renderWithProviders(<Sidebar open={false} onClose={() => {}} collapsed={false} onToggleCollapsed={() => {}} />, { session: session("administrator") });
    expect(screen.getByRole("link", { name: /^Administration/ })).toBeInTheDocument();
  });
});

describe("RequireAccess", () => {
  it("explains who a page is for", async () => {
    const { RequireAccess } = await import("./access");
    renderWithProviders(
      <Routes><Route path="/" element={<RequireAccess access="admin"><p>secret</p></RequireAccess>} /></Routes>,
      { session: session("district_officer") },
    );
    expect(screen.getByRole("alert")).toHaveTextContent("This page is for administrators.");
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });
});
