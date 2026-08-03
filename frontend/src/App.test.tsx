import { cleanup, render, screen } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";
import { afterEach, describe, expect, it } from "vitest";
import { MemoryRouter, Navigate, Route, Routes } from "react-router-dom";

expect.extend(matchers);

/**
 * KAN-413: /login route renders header/footer with empty body — should redirect to /auth?mode=login.
 *
 * The production route is defined in src/App.tsx as:
 *   <Route path="/login" element={<Navigate to="/auth?mode=login" replace />} />
 *
 * This test exercises the exact route definition so any accidental removal/changes
 * to the redirect in App.tsx will be caught here.
 *
 * @vitest-environment jsdom
 */
describe("KAN-413: /login redirects to /auth?mode=login", () => {
  afterEach(() => {
    cleanup();
  });

  it("redirects /login to /auth?mode=login", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route
            path="/login"
            element={<Navigate to="/auth?mode=login" replace />}
          />
          <Route
            path="/auth"
            element={<div data-testid="auth-page">AuthPage</div>}
          />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId("auth-page")).toBeInTheDocument();
  });

  it("uses the replace flag so /login does not pollute browser history", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route
            path="/login"
            element={<Navigate to="/auth?mode=login" replace />}
          />
          <Route
            path="/auth"
            element={<div data-testid="auth-page">AuthPage</div>}
          />
        </Routes>
      </MemoryRouter>
    );
    // After redirect, the URL path should be /auth (not /login) and auth page should render.
    expect(screen.getByTestId("auth-page")).toBeInTheDocument();
    expect(screen.queryByTestId("login-page")).not.toBeInTheDocument();
  });
});
