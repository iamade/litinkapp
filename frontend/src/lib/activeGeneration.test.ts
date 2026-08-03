/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  __resetActiveGenerationStateForTests,
  CREDITS_POLLING_END_EVENT,
  CREDITS_POLLING_START_EVENT,
  getActiveGenerationCount,
  startCreditsPollingSession,
} from "./activeGeneration";

describe("active generation credit polling sessions", () => {
  beforeEach(() => {
    __resetActiveGenerationStateForTests();
  });

  afterEach(() => {
    __resetActiveGenerationStateForTests();
  });

  it("keeps overlapping jobs suspended when one job is stopped twice", () => {
    const onStart = vi.fn();
    const onEnd = vi.fn();
    window.addEventListener(CREDITS_POLLING_START_EVENT, onStart);
    window.addEventListener(CREDITS_POLLING_END_EVENT, onEnd);

    const first = startCreditsPollingSession();
    const second = startCreditsPollingSession();

    expect(getActiveGenerationCount()).toBe(2);
    expect(onStart).toHaveBeenCalledTimes(1);

    first.stop();
    first.stop();

    expect(getActiveGenerationCount()).toBe(1);
    expect(onEnd).not.toHaveBeenCalled();

    second.stop();
    second.stop();

    expect(getActiveGenerationCount()).toBe(0);
    expect(onEnd).toHaveBeenCalledTimes(1);

    window.removeEventListener(CREDITS_POLLING_START_EVENT, onStart);
    window.removeEventListener(CREDITS_POLLING_END_EVENT, onEnd);
  });
});
