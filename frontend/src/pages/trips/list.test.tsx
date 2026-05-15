import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "@/test/test-utils";
import { TripList } from "./list";

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

beforeEach(() => {
  vi.clearAllMocks();
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

  it("shows loading state initially", () => {
    mockGet.mockReturnValue(new Promise(() => {}));

    renderWithProviders(<TripList />);

    expect(screen.getByText("Loading trips...")).toBeInTheDocument();
  });
});
