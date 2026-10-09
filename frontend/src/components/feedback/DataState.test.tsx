import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { DataState } from "./DataState";

describe("DataState", () => {
  it("announces errors and offers a retry", async () => {
    const retry = vi.fn();
    renderWithProviders(<DataState kind="error" message="Database operation failed" onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Database operation failed");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("explains an unreachable platform", () => {
    renderWithProviders(<DataState kind="unreachable" />);
    expect(screen.getByRole("alert")).toHaveTextContent("not reachable");
  });

  it("shows empty states as status, without a retry", () => {
    renderWithProviders(<DataState kind="empty" message="Nothing needs action right now." />);
    expect(screen.getByRole("status")).toHaveTextContent("Nothing needs action right now.");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
