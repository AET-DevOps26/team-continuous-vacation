import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "@/test/test-utils";
import { TripList } from "./list";

const navigationMocks = vi.hoisted(() => ({
  show: vi.fn(),
  create: vi.fn(),
}));

vi.mock("@refinedev/core", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@refinedev/core")>();
  return {
    ...actual,
    useNavigation: () => navigationMocks,
  };
});

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    GET: vi.fn(),
    POST: vi.fn(),
    DELETE: vi.fn(),
    PATCH: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";
const mockGet = vi.mocked(apiClient.GET);
const mockDelete = vi.mocked(apiClient.DELETE);

beforeEach(() => {
  vi.clearAllMocks();
  window.history.pushState({}, "", "/trips");
  localStorage.setItem("access_token", "test-token");
});

describe("TripList", () => {
  it("shows empty state when no trips", async () => {
    mockGet.mockResolvedValueOnce({ data: [], error: undefined, response: new Response() });

    renderWithProviders(<TripList />);

    await waitFor(() => {
      expect(screen.getByText("No trips yet")).toBeInTheDocument();
    });
  });

  it("renders trip cards", async () => {
    const trips = [
      { id: "1", destination: "Munich", startDate: "2026-05-15", endDate: "2026-05-18" },
      { id: "2", destination: "Tokyo", startDate: "2026-06-01", endDate: "2026-06-05" },
    ];
    mockGet.mockResolvedValueOnce({ data: trips, error: undefined, response: new Response() });

    renderWithProviders(<TripList />);

    await waitFor(() => {
      expect(screen.getByText("Munich")).toBeInTheDocument();
      expect(screen.getByText("Tokyo")).toBeInTheDocument();
    });
  });

  it("navigates to create from the header action", async () => {
    mockGet.mockResolvedValueOnce({ data: [], error: undefined, response: new Response() });
    const user = userEvent.setup();

    renderWithProviders(<TripList />);

    await user.click(await screen.findByRole("button", { name: /new trip/i }));

    expect(navigationMocks.create).toHaveBeenCalledWith("trips");
  });

  it("navigates to trip details when a trip card is clicked", async () => {
    mockGet.mockResolvedValueOnce({
      data: [{ id: "1", destination: "Munich", startDate: "2026-05-15", endDate: "2026-05-18" }],
      error: undefined,
      response: new Response(),
    });
    const user = userEvent.setup();

    renderWithProviders(<TripList />);

    await user.click(await screen.findByText("Munich"));

    expect(navigationMocks.show).toHaveBeenCalledWith("trips", "1");
  });

  it("deletes a trip without opening the trip card", async () => {
    mockGet.mockResolvedValueOnce({
      data: [{ id: "1", destination: "Munich", startDate: "2026-05-15", endDate: "2026-05-18" }],
      error: undefined,
      response: new Response(),
    });
    mockDelete.mockResolvedValueOnce({ data: undefined, error: undefined, response: new Response() });
    const user = userEvent.setup();

    renderWithProviders(<TripList />);

    await user.click(await screen.findByRole("button", { name: /delete munich/i }));

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith(
      "/trips/{tripId}",
      { params: { path: { tripId: "1" } } }
    ));
    expect(navigationMocks.show).not.toHaveBeenCalled();
  });

  it("shows loading state initially", () => {
    mockGet.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<TripList />);

    expect(screen.getByText("Loading trips...")).toBeInTheDocument();
  });
});
