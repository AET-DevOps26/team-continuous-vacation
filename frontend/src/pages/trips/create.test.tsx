import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TripCreate } from "./create";

const mocks = vi.hoisted(() => ({
  createMutate: vi.fn(),
  show: vi.fn(),
  list: vi.fn(),
}));

vi.mock("@refinedev/core", () => ({
  useCreate: () => ({ mutate: mocks.createMutate }),
  useNavigation: () => ({ show: mocks.show, list: mocks.list }),
}));

vi.mock("@/components/ui/calendar", () => ({
  Calendar: ({ onSelect }: { onSelect: (date: Date) => void }) => (
    <button type="button" onClick={() => onSelect(new Date("2026-07-01T00:00:00"))}>
      Select July 1
    </button>
  ),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TripCreate", () => {
  it("submits trip preferences and navigates to the generated trip", async () => {
    const user = userEvent.setup();
    mocks.createMutate.mockImplementation((_params, options) => {
      options.onSuccess({ data: { id: "trip-1" } });
      options.onSettled();
    });

    render(<TripCreate />);

    await user.type(screen.getByPlaceholderText("e.g. Munich, Beach vacation, Tokyo"), "Munich");
    await user.click(screen.getByRole("button", { name: "Start Date" }));
    await user.click(await screen.findByRole("button", { name: "Select July 1" }));
    await user.click(screen.getByRole("button", { name: "End Date" }));
    await user.click(await screen.findByRole("button", { name: "Select July 1" }));
    await user.click(screen.getByRole("button", { name: "Sporty and active" }));
    await user.click(screen.getByRole("button", { name: "Generate Trip" }));

    await waitFor(() => {
      expect(mocks.createMutate).toHaveBeenCalledWith(
        {
          resource: "trips",
          values: {
            destination: "Munich",
            startDate: "2026-07-01",
            endDate: "2026-07-01",
            vibe: "Sporty and active",
          },
        },
        expect.any(Object)
      );
    });
    expect(mocks.show).toHaveBeenCalledWith("trips", "trip-1");
  });

  it("shows validation errors for an empty form", async () => {
    const user = userEvent.setup();
    render(<TripCreate />);

    await user.click(screen.getByRole("button", { name: "Generate Trip" }));

    expect(await screen.findByText("Destination is required")).toBeInTheDocument();
    expect(screen.getByText("Start date is required")).toBeInTheDocument();
    expect(screen.getByText("End date is required")).toBeInTheDocument();
    expect(screen.getByText("Vibe is required")).toBeInTheDocument();
    expect(mocks.createMutate).not.toHaveBeenCalled();
  });

  it("navigates back to the trip list", async () => {
    const user = userEvent.setup();
    render(<TripCreate />);

    await user.click(screen.getByRole("button", { name: "Back" }));

    expect(mocks.list).toHaveBeenCalledWith("trips");
  });
});
