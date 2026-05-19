import type { AuthProvider } from "@refinedev/core";
import { apiClient } from "@/lib/api-client";

export const authProvider: AuthProvider = {
  async login({ email, password }) {
    const { data, error } = await apiClient.POST("/auth/login", {
      body: { email, password },
    });
    if (error || !data) {
      return { success: false, error: { name: "Login Failed", message: error?.title ?? "Invalid credentials" } };
    }
    localStorage.setItem("access_token", data.accessToken);
    localStorage.setItem("traveler_id", data.travelerId);
    localStorage.setItem("is_demo", String(data.isDemo));
    return { success: true, redirectTo: "/" };
  },

  async register({ email, password }) {
    const { data, error } = await apiClient.POST("/auth/register", {
      body: { email, password },
    });
    if (error || !data) {
      return { success: false, error: { name: "Registration Failed", message: error?.title ?? "Could not register" } };
    }
    localStorage.setItem("access_token", data.accessToken);
    localStorage.setItem("traveler_id", data.travelerId);
    localStorage.setItem("is_demo", String(data.isDemo));
    return { success: true, redirectTo: "/" };
  },

  async logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("traveler_id");
    localStorage.removeItem("is_demo");
    return { success: true, redirectTo: "/login" };
  },

  async check() {
    const token = localStorage.getItem("access_token");
    if (token) {
      return { authenticated: true };
    }
    return { authenticated: false, redirectTo: "/login" };
  },

  async getIdentity() {
    const travelerId = localStorage.getItem("traveler_id");
    const isDemo = localStorage.getItem("is_demo") === "true";
    if (!travelerId) return null;
    return { id: travelerId, name: isDemo ? "Demo Traveler" : "Traveler" };
  },

  async onError(error) {
    if (error?.statusCode === 401) {
      return { logout: true };
    }
    return { error };
  },
};

export async function ensureDemoSession(): Promise<void> {
  const token = localStorage.getItem("access_token");
  if (token) return;

  const { data, error } = await apiClient.POST("/auth/demo");
  if (error || !data) {
    throw new Error("Failed to create demo session");
  }
  localStorage.setItem("access_token", data.accessToken);
  localStorage.setItem("traveler_id", data.travelerId);
  localStorage.setItem("is_demo", String(data.isDemo));
}
