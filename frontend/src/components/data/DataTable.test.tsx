import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/render";
import { DataTable, type Column } from "./DataTable";

type Row = { id: number; name: string; reports: number };
const rows: Row[] = Array.from({ length: 23 }, (_, index) => ({ id: index + 1, name: `Cooperative ${index + 1}`, reports: (index * 7) % 10 }));
const columns: Column<Row>[] = [
  { key: "name", header: "Name", primary: true, render: (row) => row.name, sortValue: (row) => row.name },
  { key: "reports", header: "Reports", render: (row) => row.reports, sortValue: (row) => row.reports },
];

const table = (props: Partial<Parameters<typeof DataTable<Row>>[0]> = {}) =>
  renderWithProviders(<DataTable rows={rows} columns={columns} rowKey={(row) => row.id} caption="Cooperatives" emptyMessage="None yet" searchText={(row) => row.name} pageSize={10} {...props} />);

describe("DataTable", () => {
  it("pages long lists", async () => {
    table();
    const body = screen.getByRole("table");
    expect(within(body).getAllByRole("row")).toHaveLength(11); // header + 10
    await userEvent.click(screen.getByRole("button", { name: "Next page" }));
    expect(within(body).getByText("Cooperative 11")).toBeInTheDocument();
  });

  it("searches", async () => {
    table();
    await userEvent.type(screen.getByRole("searchbox"), "Cooperative 23");
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(2);
  });

  it("sorts by a column and says so", async () => {
    table();
    await userEvent.click(screen.getByRole("button", { name: "Reports" }));
    const header = screen.getByRole("columnheader", { name: /Reports/ });
    expect(header).toHaveAttribute("aria-sort");
  });

  it("shows the empty message, not an empty grid", () => {
    table({ rows: [] });
    expect(screen.getByText("None yet")).toBeInTheDocument();
  });

  it("shows an error with a retry", async () => {
    const retry = vi.fn();
    table({ rows: undefined, error: "The platform could not be reached.", onRetry: retry });
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalled();
  });
});
