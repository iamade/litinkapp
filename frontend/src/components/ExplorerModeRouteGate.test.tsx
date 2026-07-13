import { cleanup, render, screen } from "@testing-library/react";
import * as matchers from "@testing-library/jest-dom/matchers";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ExplorerModeRouteGate } from "./ExplorerModeRouteGate";
import { getPostAuthRedirect } from "../lib/explorerMode";

expect.extend(matchers);

function renderExplorerRoute(path: "/dashboard" | "/explore" | "/learn") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path={path}
          element={
            <ExplorerModeRouteGate>
              <div>explorer content</div>
            </ExplorerModeRouteGate>
          }
        />
        <Route path="/creator" element={<div>creator home</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ExplorerModeRouteGate", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllEnvs();
  });

  it.each(["/dashboard", "/explore", "/learn"] as const)(
    "redirects %s to creator when explorer mode is unset",
    (path) => {
      vi.stubEnv("VITE_FEATURE_EXPLORER_MODE", undefined);

      renderExplorerRoute(path);

      expect(screen.getByText("creator home")).toBeInTheDocument();
      expect(screen.queryByText("explorer content")).not.toBeInTheDocument();
    }
  );

  it("renders explorer routes when explorer mode is enabled", () => {
    vi.stubEnv("VITE_FEATURE_EXPLORER_MODE", "true");

    renderExplorerRoute("/dashboard");

    expect(screen.getByText("explorer content")).toBeInTheDocument();
    expect(screen.queryByText("creator home")).not.toBeInTheDocument();
  });

  it("uses creator as the post-auth destination while explorer mode is disabled", () => {
    vi.stubEnv("VITE_FEATURE_EXPLORER_MODE", "false");

    expect(getPostAuthRedirect({ roles: ["explorer"], preferred_mode: "explorer" })).toBe("/creator");
    expect(getPostAuthRedirect({ roles: ["creator", "explorer"], preferred_mode: "explorer" })).toBe("/creator");
  });
});
