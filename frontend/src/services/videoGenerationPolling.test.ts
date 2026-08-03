/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  __resetActiveGenerationStateForTests,
  CREDITS_POLLING_END_EVENT,
  getActiveGenerationCount,
} from "../lib/activeGeneration";

const mocks = vi.hoisted(() => ({
  getEnhancedGenerationStatus: vi.fn(),
}));

vi.mock("../lib/videoGenerationApi", () => ({
  videoGenerationAPI: {
    getEnhancedGenerationStatus: mocks.getEnhancedGenerationStatus,
  },
  normalizeGenerationStatus: (status: string | null | undefined) => {
    if (status === "completed" || status === "failed") return status;
    return "generating_video";
  },
}));

vi.mock("../utils/videoGenerationErrors", () => ({
  handleVideoGenerationStatusError: vi.fn(),
  showVideoGenerationSuccess: vi.fn(),
}));

import pollingService, { startVideoGenerationPolling } from "./videoGenerationPolling";

type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
};

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

const processingStatus = {
  status: "processing",
  current_step: "video_generation",
  progress_percentage: 50,
  steps: {
    image_generation: { status: "completed", progress: 100 },
    audio_generation: { status: "completed", progress: 100 },
    video_generation: { status: "processing", progress: 50 },
    audio_video_merge: { status: "pending", progress: 0 },
  },
  error: null,
  video_url: null,
} as const;

describe("video generation polling cleanup", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mocks.getEnhancedGenerationStatus.mockReset();
    __resetActiveGenerationStateForTests();
  });

  afterEach(() => {
    pollingService.stopAllPolling();
    __resetActiveGenerationStateForTests();
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("does not let duplicate reactive stops emit extra end events", () => {
    const onEnd = vi.fn();
    window.addEventListener(CREDITS_POLLING_END_EVENT, onEnd);
    mocks.getEnhancedGenerationStatus.mockReturnValue(new Promise(() => {}));

    const stop = startVideoGenerationPolling({ scriptId: "script-1" });
    expect(getActiveGenerationCount()).toBe(1);

    stop();
    stop();

    expect(getActiveGenerationCount()).toBe(0);
    expect(onEnd).toHaveBeenCalledTimes(1);

    window.removeEventListener(CREDITS_POLLING_END_EVENT, onEnd);
  });

  it("does not schedule a reactive timeout after cleanup while a poll is in flight", async () => {
    const inFlight = deferred<typeof processingStatus>();
    const onUpdate = vi.fn();
    mocks.getEnhancedGenerationStatus.mockReturnValueOnce(inFlight.promise);

    const stop = startVideoGenerationPolling({ scriptId: "script-2", onUpdate });
    stop();

    inFlight.resolve(processingStatus);
    await Promise.resolve();
    await Promise.resolve();

    expect(onUpdate).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
    expect(getActiveGenerationCount()).toBe(0);
  });

  it("does not schedule a legacy timeout after stopPolling while a poll is in flight", async () => {
    const inFlight = deferred<typeof processingStatus>();
    const callbacks = {
      onUpdate: vi.fn(),
      onError: vi.fn(),
      onComplete: vi.fn(),
    };
    mocks.getEnhancedGenerationStatus.mockReturnValueOnce(inFlight.promise);

    pollingService.startPolling("video-1", callbacks);
    pollingService.stopPolling("video-1");

    inFlight.resolve(processingStatus);
    await Promise.resolve();
    await Promise.resolve();

    expect(callbacks.onUpdate).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
    expect(getActiveGenerationCount()).toBe(0);
  });
});
