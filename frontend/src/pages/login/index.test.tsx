import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from ".";

const mocks = vi.hoisted(() => ({
  loginMutate: vi.fn(),
  registerMutate: vi.fn(),
  notify: vi.fn(),
  navigate: vi.fn(),
  ensureDemoSession: vi.fn(),
}));

vi.mock("@refinedev/core", () => ({
  useLogin: () => ({ mutate: mocks.loginMutate, status: "idle" }),
  useRegister: () => ({ mutate: mocks.registerMutate, status: "idle" }),
  useNotification: () => ({ open: mocks.notify }),
}));

vi.mock("@/providers/auth-provider", () => ({
  ensureDemoSession: mocks.ensureDemoSession,
}));

vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useNavigate: () => mocks.navigate,
  };
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe("LoginPage", () => {
  it("submits login credentials", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByPlaceholderText("you@example.com"), "ada@example.com");
    await user.type(screen.getByPlaceholderText("Min. 8 characters"), "password123");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(mocks.loginMutate).toHaveBeenCalledWith({
      email: "ada@example.com",
      password: "password123",
    });
    expect(mocks.registerMutate).not.toHaveBeenCalled();
  });

  it("switches to registration mode and submits registration credentials", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: "Register" }));
    await user.type(screen.getByPlaceholderText("you@example.com"), "grace@example.com");
    await user.type(screen.getByPlaceholderText("Min. 8 characters"), "password123");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(mocks.registerMutate).toHaveBeenCalledWith({
      email: "grace@example.com",
      password: "password123",
    });
    expect(mocks.loginMutate).not.toHaveBeenCalled();
  });

  it("shows a notification when demo session creation fails", async () => {
    const user = userEvent.setup();
    mocks.ensureDemoSession.mockRejectedValueOnce(new Error("demo unavailable"));

    render(<LoginPage />);
    await user.click(screen.getByRole("button", { name: "Try Demo (No Sign-up)" }));

    expect(mocks.notify).toHaveBeenCalledWith({
      type: "error",
      message: "Failed to create demo session. Please try again.",
    });
  });
});
