/**
 * Lightweight global active-generation counter.
 *
 * Long-running generation jobs (image/audio/video pipelines) emit
 * CREDITS_POLLING_START_EVENT / CREDITS_POLLING_END_EVENT. Consumers such as
 * useCreditBalance subscribe to these events and suspend their own background
 * polling while jobs are active, avoiding the "~1/sec /credits/balance poll
 * storm" during long jobs (KAN-436).
 */

export const CREDITS_POLLING_START_EVENT = "credits:polling:start";
export const CREDITS_POLLING_END_EVENT = "credits:polling:end";

let activeGenerationCount = 0;

function emit(eventName: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(eventName));
}

export function startCreditsPolling() {
  activeGenerationCount += 1;
  if (activeGenerationCount === 1) {
    emit(CREDITS_POLLING_START_EVENT);
  }
}

export function endCreditsPolling() {
  activeGenerationCount = Math.max(0, activeGenerationCount - 1);
  if (activeGenerationCount === 0) {
    emit(CREDITS_POLLING_END_EVENT);
  }
}

export function getActiveGenerationCount(): number {
  return activeGenerationCount;
}
