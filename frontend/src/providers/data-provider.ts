import type {
  DataProvider,
  GetListParams,
  GetOneParams,
  CreateParams,
  DeleteOneParams,
  UpdateParams,
} from "@refinedev/core";
import { apiClient } from "@/lib/api-client";
import type { components } from "@/lib/api-types";

// Refine's DataProvider interface uses higher-kinded generics on each method
// (`<TData extends BaseRecord>`) which are structurally unsatisfiable with
// concrete return types. The official packages (@refinedev/simple-rest etc.)
// solve this with `as DataProvider`. We follow the same pattern here.
// Runtime type safety comes from the openapi-fetch client which validates
// against the generated schema types.

export type TripSummary = components["schemas"]["TripSummary"];
export type Trip = components["schemas"]["Trip"];
export type Activity = components["schemas"]["Activity"];
export type GenerationPreferences = components["schemas"]["GenerationPreferences"];
export type RegenerationInstruction = components["schemas"]["RegenerationInstruction"];

interface ActivityMeta {
  tripId: string;
  dayId: string;
}

function extractActivityMeta(meta: unknown): ActivityMeta {
  if (
    meta != null &&
    typeof meta === "object" &&
    "tripId" in meta &&
    "dayId" in meta &&
    typeof (meta as ActivityMeta).tripId === "string" &&
    typeof (meta as ActivityMeta).dayId === "string"
  ) {
    return meta as ActivityMeta;
  }
  throw new Error("Missing required meta: { tripId, dayId }");
}

export const dataProvider = {
  getList: async ({ resource }: GetListParams) => {
    if (resource === "trips") {
      const { data, error } = await apiClient.GET("/trips");
      if (error) throw new Error("Failed to fetch trips");
      const trips = data ?? [];
      return { data: trips, total: trips.length };
    }
    throw new Error(`Unknown resource: ${resource}`);
  },

  getOne: async ({ resource, id }: GetOneParams) => {
    if (resource === "trips") {
      const { data, error } = await apiClient.GET("/trips/{tripId}", {
        params: { path: { tripId: String(id) } },
      });
      if (error) throw new Error(error.title ?? "Failed to fetch trip");
      return { data };
    }
    throw new Error(`Unknown resource: ${resource}`);
  },

  create: async ({ resource, variables }: CreateParams) => {
    if (resource === "trips") {
      const { data, error } = await apiClient.POST("/trips", {
        body: variables as GenerationPreferences,
      });
      if (error) throw new Error(error.title ?? "Failed to generate trip");
      return { data };
    }
    throw new Error(`Unknown resource: ${resource}`);
  },

  deleteOne: async ({ resource, id, meta }: DeleteOneParams) => {
    if (resource === "trips") {
      const { error } = await apiClient.DELETE("/trips/{tripId}", {
        params: { path: { tripId: String(id) } },
      });
      if (error) throw new Error(error.title ?? "Failed to delete trip");
      return { data: { id: String(id) } };
    }
    if (resource === "activities") {
      const { tripId, dayId } = extractActivityMeta(meta);
      const { error } = await apiClient.DELETE(
        "/trips/{tripId}/days/{dayId}/activities/{activityId}",
        { params: { path: { tripId, dayId, activityId: String(id) } } }
      );
      if (error) throw new Error(error.title ?? "Failed to delete activity");
      return { data: { id: String(id) } };
    }
    throw new Error(`Unknown resource: ${resource}`);
  },

  update: async ({ resource, id, variables, meta }: UpdateParams) => {
    if (resource === "activities") {
      const { tripId, dayId } = extractActivityMeta(meta);
      const { data, error } = await apiClient.PATCH(
        "/trips/{tripId}/days/{dayId}/activities/{activityId}",
        {
          params: { path: { tripId, dayId, activityId: String(id) } },
          body: variables as RegenerationInstruction,
        }
      );
      if (error) throw new Error(error.title ?? "Failed to regenerate activity");
      return { data };
    }
    throw new Error(`Unknown resource: ${resource}`);
  },

  getApiUrl: () => import.meta.env.VITE_API_URL ?? "/api",
} as unknown as DataProvider;
