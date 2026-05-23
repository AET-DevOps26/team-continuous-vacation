import createClient from "openapi-fetch";
import type { paths } from "./api-types";

const API_BASE_URL: string = import.meta.env.VITE_API_URL ?? "/api";

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
