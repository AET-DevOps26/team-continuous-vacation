import { describe, it, expect, vi, beforeEach } from "vitest";
import { dataProvider } from "./data-provider";

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
const mockPost = vi.mocked(apiClient.POST);
const mockDelete = vi.mocked(apiClient.DELETE);
const mockPatch = vi.mocked(apiClient.PATCH);

beforeEach(() => vi.clearAllMocks());

describe("dataProvider", () => {
  describe("getList", () => {
    it("fetches trips", async () => {
      const trips = [
        { id: "1", destination: "Munich", startDate: "2026-05-15", endDate: "2026-05-18" },
      ];
      mockGet.mockResolvedValueOnce({ data: trips, error: undefined, response: new Response() });

      const result = await dataProvider.getList({ resource: "trips" });
      expect(result.data).toEqual(trips);
      expect(result.total).toBe(1);
    });

    it("throws on unknown resource", async () => {
      await expect(dataProvider.getList({ resource: "unknown" })).rejects.toThrow("Unknown resource");
    });
  });

  describe("getOne", () => {
    it("fetches single trip", async () => {
      const trip = {
        id: "1",
        destination: "Munich",
        startDate: "2026-05-15",
        endDate: "2026-05-18",
        vibe: "Sporty",
        schedule: { days: [] },
      };
      mockGet.mockResolvedValueOnce({ data: trip, error: undefined, response: new Response() });

      const result = await dataProvider.getOne!({ resource: "trips", id: "1" });
      expect(result.data).toEqual(trip);
    });

    it("throws on error", async () => {
      mockGet.mockResolvedValueOnce({
        data: undefined,
        error: { type: "NOT_FOUND", title: "Trip Not Found", status: 404 },
        response: new Response(),
      });

      await expect(dataProvider.getOne!({ resource: "trips", id: "bad" })).rejects.toThrow("Trip Not Found");
    });
  });

  describe("create", () => {
    it("generates trip", async () => {
      const trip = { id: "new-id", destination: "Tokyo", startDate: "2026-06-01", endDate: "2026-06-05", vibe: "Foodie", schedule: { days: [] } };
      mockPost.mockResolvedValueOnce({ data: trip, error: undefined, response: new Response() });

      const result = await dataProvider.create!({
        resource: "trips",
        variables: { destination: "Tokyo", startDate: "2026-06-01", endDate: "2026-06-05", vibe: "Foodie" },
      });
      expect(result.data).toEqual(trip);
    });
  });

  describe("deleteOne", () => {
    it("deletes trip", async () => {
      mockDelete.mockResolvedValueOnce({ data: undefined, error: undefined, response: new Response() });

      const result = await dataProvider.deleteOne!({ resource: "trips", id: "trip-1" });
      expect(result.data).toEqual({ id: "trip-1" });
    });

    it("deletes activity", async () => {
      mockDelete.mockResolvedValueOnce({ data: undefined, error: undefined, response: new Response() });

      const result = await dataProvider.deleteOne!({
        resource: "activities",
        id: "act-1",
        meta: { tripId: "trip-1", dayId: "day-1" },
      });
      expect(result.data).toEqual({ id: "act-1" });
    });
  });

  describe("update", () => {
    it("regenerates activity", async () => {
      const newActivity = { id: "act-1", dayId: "day-1", timeBlock: "MORNING", title: "Indoor Museum", description: "Visit museum", durationMinutes: 90 };
      mockPatch.mockResolvedValueOnce({ data: newActivity, error: undefined, response: new Response() });

      const result = await dataProvider.update!({
        resource: "activities",
        id: "act-1",
        variables: { instruction: "Make this indoor" },
        meta: { tripId: "trip-1", dayId: "day-1" },
      });
      expect(result.data).toEqual(newActivity);
    });
  });
});
