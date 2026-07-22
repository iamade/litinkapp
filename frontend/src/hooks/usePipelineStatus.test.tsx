/**
 * @vitest-environment jsdom
 */
import { cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { usePipelineStatus } from "./usePipelineStatus";

vi.mock("../services/aiService", () => ({
  aiService: {
    getPipelineStatus: vi.fn(),
    retryVideoGeneration: vi.fn(),
  },
}));

vi.mock("../utils/videoGenerationErrors", () => ({
  handlePipelineStatusError: vi.fn(),
}));

vi.mock("react-hot-toast", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

describe("usePipelineStatus", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("mounts without referencing polling callbacks before initialization", () => {
    expect(() => {
      renderHook(() => usePipelineStatus("", { autoRefresh: false }));
    }).not.toThrow();
  });
});
