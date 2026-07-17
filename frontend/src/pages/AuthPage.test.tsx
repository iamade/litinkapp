import { cleanup, render, screen } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
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
});
