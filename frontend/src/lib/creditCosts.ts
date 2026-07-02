export const CREDIT_COSTS = {
  IMAGE: 1,
  AUDIO_PER_SECOND: 1,
  VIDEO_PER_SECOND: 5,
  SCRIPT: 2,
  UPSCALE: 1,
} as const;

export const DEFAULT_AUDIO_SECONDS_PER_SCENE = 5;
export const DEFAULT_VIDEO_SECONDS_PER_SHOT = 5;

const roundUp = (value: number) => Math.max(1, Math.ceil(value));

export function estimateImageCredits(count = 1): number {
  return Math.max(0, Math.ceil(count)) * CREDIT_COSTS.IMAGE;
}

export function estimateScriptCredits(): number {
  return CREDIT_COSTS.SCRIPT;
}

export function estimateUpscaleCredits(count = 1): number {
  return Math.max(0, Math.ceil(count)) * CREDIT_COSTS.UPSCALE;
}

export function estimateAudioCredits(seconds: number): number {
  return roundUp(seconds * CREDIT_COSTS.AUDIO_PER_SECOND);
}

export function estimateAudioCreditsFromScenes(
  sceneCount: number,
  averageSecondsPerScene = DEFAULT_AUDIO_SECONDS_PER_SCENE
): number {
  if (sceneCount <= 0) return 0;
  return estimateAudioCredits(sceneCount * averageSecondsPerScene);
}

export function estimateVideoCredits(seconds: number): number {
  return roundUp(seconds * CREDIT_COSTS.VIDEO_PER_SECOND);
}

export function estimateVideoCreditsFromShots(
  shotCount: number,
  averageSecondsPerShot = DEFAULT_VIDEO_SECONDS_PER_SHOT
): number {
  if (shotCount <= 0) return 0;
  return estimateVideoCredits(shotCount * averageSecondsPerShot);
}

export function getInsufficientCreditsTooltip(balance: number, required: number): string {
  return `Insufficient credits (${balance} available, ${required} required)`;
}
