import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TripShow } from "./show";

const mocks = vi.hoisted(() => ({
  trip: {
    id: "trip-1",
    destination: "Munich",
    startDate: "2026-07-01",
    endDate: "2026-07-01",
    vibe: "Sporty",
    schedule: {
      days: [
        {
          id: "day-1",
          dayNumber: 1,
          date: "2026-07-01",
          activities: [
            {
              id: "activity-1",
              dayId: "day-1",
              timeBlock: "MORNING",
              title: "English Garden run",
              description: "A scenic morning route.",
              durationMinutes: 90,
              isIndoor: false,
              tags: ["SPORTY", "OUTDOOR"],
            },
          ],
        },
      ],
    },
  },
  query: {
    isLoading: false,
    data: undefined as unknown,
    refetch: vi.fn(),
  },
  updateMutate: vi.fn(),
  deleteMutate: vi.fn(),
  list: vi.fn(),
}));

vi.mock("@refinedev/core", () => ({
  useShow: () => ({ query: mocks.query }),
  useUpdate: () => ({ mutate: mocks.updateMutate }),
  useDelete: () => ({ mutate: mocks.deleteMutate }),
  useNavigation: () => ({ list: mocks.list }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.query.isLoading = false;
  mocks.query.data = { data: mocks.trip };
});

describe("TripShow", () => {
  it("shows loading state", () => {
    mocks.query.isLoading = true;
    mocks.query.data = undefined;

    render(<TripShow />);

    expect(screen.getByText("Loading trip...")).toBeInTheDocument();
  });

  it("renders trip schedule details", () => {
    render(<TripShow />);

    expect(screen.getByText("Munich")).toBeInTheDocument();
    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.getByText("English Garden run")).toBeInTheDocument();
    expect(screen.getByText("sporty")).toBeInTheDocument();
  });

  it("regenerates an activity with the entered instruction", async () => {
    const user = userEvent.setup();
    mocks.updateMutate.mockImplementation((_params, options) => {
      options.onSuccess();
      options.onSettled();
    });

    render(<TripShow />);

    await user.click(screen.getByTitle("Regenerate activity"));
    await user.type(screen.getByPlaceholderText("e.g. Make this an indoor activity"), "Make this indoor");
    await user.click(screen.getByRole("button", { name: "Go" }));

    expect(mocks.updateMutate).toHaveBeenCalledWith(
      {
        resource: "activities",
        id: "activity-1",
        values: { instruction: "Make this indoor" },
        meta: { tripId: "trip-1", dayId: "day-1" },
        invalidates: [],
      },
      expect.any(Object)
    );
    expect(mocks.query.refetch).toHaveBeenCalled();
  });

  it("deletes an activity and refetches the trip", async () => {
    const user = userEvent.setup();
    mocks.deleteMutate.mockImplementation((_params, options) => {
      options.onSuccess();
    });

    render(<TripShow />);

    await user.click(screen.getByTitle("Delete activity"));

    expect(mocks.deleteMutate).toHaveBeenCalledWith(
      {
        resource: "activities",
        id: "activity-1",
        meta: { tripId: "trip-1", dayId: "day-1" },
        invalidates: [],
      },
      expect.objectContaining({ onSuccess: expect.any(Function) })
    );
    expect(mocks.query.refetch).toHaveBeenCalled();
  });

  it("navigates back to the trip list", async () => {
    const user = userEvent.setup();
    render(<TripShow />);

    await user.click(screen.getByRole("button", { name: "Back" }));

    expect(mocks.list).toHaveBeenCalledWith("trips");
  });
});
