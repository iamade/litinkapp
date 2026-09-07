import { cleanup, render, screen } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { toast } from "react-hot-toast";
import AuthPage from "./AuthPage";

expect.extend(matchers);

vi.mock("../contexts/AuthContext", () => ({
  useAuth: () => ({
    login: vi.fn(),
    register: vi.fn(),
    resendVerificationEmail: vi.fn(),
  }),
}));

vi.mock("react-hot-toast", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

/**
 * @vitest-environment jsdom
 */
function renderAuthPage(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("AuthPage OAuth errors", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("renders a session-expired message for invalid OAuth state", () => {
    renderAuthPage("/auth?oauth_error=invalid_state");

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Your sign-in session expired. Please try signing in with Google again."
    );
  });

  it("opens register mode, prefills email, and explains account-unavailable Google redirects", () => {
    const email = "writer+google@example.com";

    renderAuthPage(
      `/auth?mode=register&oauth_error=account_unavailable&email=${encodeURIComponent(email)}`
    );

    expect(screen.getByText("Start Creating AI Videos")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Enter email")).toHaveValue(email);
    expect(screen.getByRole("button", { name: "Register" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Register to use that Google email with LitInkAI."
    );
    expect(screen.getByRole("alert")).toHaveTextContent(email);
    expect(toast.error).toHaveBeenCalledWith(
      "We couldn't sign in with that Google account. Please choose an active account or use email and password.",
      { id: "oauth-account-unavailable" }
    );
  });
});
