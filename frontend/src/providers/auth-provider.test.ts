import { describe, it, expect, beforeEach, vi } from "vitest";
import { authProvider, ensureDemoSession } from "./auth-provider";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    POST: vi.fn(),
  },
}));

import { apiClient } from "@/lib/api-client";
const mockPost = vi.mocked(apiClient.POST);

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("authProvider", () => {
  describe("check", () => {
    it("returns authenticated when token exists", async () => {
      localStorage.setItem("access_token", "test-token");
      const result = await authProvider.check!();
      expect(result.authenticated).toBe(true);
    });

    it("returns unauthenticated when no token", async () => {
      const result = await authProvider.check!();
      expect(result.authenticated).toBe(false);
    });
  });

  describe("login", () => {
    it("stores token on success", async () => {
      mockPost.mockResolvedValueOnce({
        data: {
          travelerId: "uuid-1",
          isDemo: false,
          accessToken: "jwt-token",
          tokenType: "Bearer",
          expiresAt: "2026-06-14T10:30:00Z",
        },
        error: undefined,
        response: new Response(),
      });

      const result = await authProvider.login!({ email: "test@test.com", password: "password1" });
      expect(result.success).toBe(true);
      expect(localStorage.getItem("access_token")).toBe("jwt-token");
      expect(localStorage.getItem("traveler_id")).toBe("uuid-1");
    });

    it("returns error on failure", async () => {
      mockPost.mockResolvedValueOnce({
        data: undefined,
        error: { type: "AUTH_ERROR", title: "Invalid credentials", status: 401 },
        response: new Response(),
      });

      const result = await authProvider.login!({ email: "bad@test.com", password: "wrong" });
      expect(result.success).toBe(false);
    });
  });

  describe("logout", () => {
    it("clears localStorage", async () => {
      localStorage.setItem("access_token", "token");
      localStorage.setItem("traveler_id", "id");
      await authProvider.logout!();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("traveler_id")).toBeNull();
    });
  });

  describe("getIdentity", () => {
    it("returns demo identity", async () => {
      localStorage.setItem("traveler_id", "demo-uuid");
      localStorage.setItem("is_demo", "true");
      const identity = await authProvider.getIdentity!();
      expect(identity).toEqual({ id: "demo-uuid", name: "Demo Traveler" });
    });

    it("returns null when not authenticated", async () => {
      const identity = await authProvider.getIdentity!();
      expect(identity).toBeNull();
    });
  });
});

describe("ensureDemoSession", () => {
  it("creates demo session when no token exists", async () => {
    mockPost.mockResolvedValueOnce({
      data: {
        travelerId: "demo-uuid",
        isDemo: true,
        accessToken: "demo-jwt",
        tokenType: "Bearer",
        expiresAt: "2026-06-14T10:30:00Z",
      },
      error: undefined,
      response: new Response(),
    });

    await ensureDemoSession();
    expect(localStorage.getItem("access_token")).toBe("demo-jwt");
    expect(localStorage.getItem("is_demo")).toBe("true");
  });

  it("skips if token already exists", async () => {
    localStorage.setItem("access_token", "existing-token");
    await ensureDemoSession();
    expect(mockPost).not.toHaveBeenCalled();
  });
});
