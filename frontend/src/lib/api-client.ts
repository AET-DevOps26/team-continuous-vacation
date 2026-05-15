import createClient from "openapi-fetch";
import type { paths } from "./api-types";

// In dev mode, Vite proxy forwards /auth and /trips to localhost:8080,
// so we use relative URLs (empty baseUrl). In production (Docker), set
// VITE_API_URL to the backend's absolute URL if not behind same origin.
const API_BASE_URL: string = import.meta.env.VITE_API_URL ?? "";

export const apiClient = createClient<paths>({
  baseUrl: API_BASE_URL,
});

apiClient.use({
  onRequest({ request }): Request {
    const token = localStorage.getItem("access_token");
    if (token) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
});
