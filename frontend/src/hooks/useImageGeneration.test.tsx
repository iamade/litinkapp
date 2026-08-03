/**
 * @vitest-environment jsdom
 */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useImageGeneration } from "./useImageGeneration";
import {
  __resetActiveGenerationStateForTests,
  getActiveGenerationCount,
} from "../lib/activeGeneration";
import { userService } from "../services/userService";

vi.mock("react-hot-toast", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

vi.mock("../lib/credits", () => ({
  dispatchCreditsRefresh: vi.fn(),
}));

vi.mock("../services/userService", () => ({
  userService: {
    getChapterImages: vi.fn(),
    generateSceneImage: vi.fn(),
    generateCharacterImage: vi.fn(),
    getImageGenerationStatus: vi.fn(),
  },
}));

const imageOptions = {
  style: "realistic" as const,
  quality: "standard" as const,
  aspectRatio: "16:9" as const,
  useCharacterReferences: false,
  includeBackground: true,
  lightingMood: "",
};

describe("useImageGeneration polling cleanup", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(userService.getChapterImages).mockResolvedValue({ images: [] });
    vi.mocked(userService.generateSceneImage).mockResolvedValue({ record_id: "scene-record" });
    vi.mocked(userService.generateCharacterImage).mockResolvedValue({ record_id: "character-record" });
    vi.mocked(userService.getImageGenerationStatus).mockResolvedValue({ status: "processing" });
    __resetActiveGenerationStateForTests();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    __resetActiveGenerationStateForTests();
  });

  it("stops scene and character credit polling sessions on unmount", async () => {
    const { result, unmount } = renderHook(() => useImageGeneration("chapter-id", "script-id"));

    await act(async () => {
      await result.current.generateSceneImage(1, "Scene description", imageOptions);
      await result.current.generateCharacterImage("Ari", "Character description", imageOptions);
    });

    expect(getActiveGenerationCount()).toBe(2);

    unmount();

    expect(getActiveGenerationCount()).toBe(0);

    await act(async () => {
      vi.advanceTimersByTime(300000);
    });

    expect(userService.getImageGenerationStatus).not.toHaveBeenCalled();
  });
});
