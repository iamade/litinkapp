export const CREDIT_COSTS = {
  IMAGE: 1,
  AUDIO_PER_SECOND: 1,
  VIDEO_PER_SECOND: 5,
  SCRIPT: 2,
  UPSCALE: 1,
} as const;

export const DEFAULT_AUDIO_SECONDS_PER_SCENE = 5;
export const DEFAULT_VIDEO_SECONDS_PER_SHOT = 5;
export type BookPipelineCreditMode = 'draft' | 'cinematic';

export const BOOK_PIPELINE_CREDIT_RATES = {
  draft: {
    plot: 2,
    scriptPer1kTokens: 3,
    image: 12,
    audioPerSecond: 2,
    videoPerSecond: 35,
  },
  cinematic: {
    plot: 2,
    scriptPer1kTokens: {
      free: 3,
      basic: 8,
      pro: 10,
      standard: 10,
      premium: 12,
      professional: 15,
      enterprise: 15,
    },
    image: {
      free: 12,
      basic: 12,
      pro: 16,
      standard: 16,
      premium: 17,
      professional: 22,
      enterprise: 65,
    },
    audioPerSecond: 2,
    videoPerSecond: 49,
  },
} as const;

type Tier = keyof typeof BOOK_PIPELINE_CREDIT_RATES.cinematic.image;

export function normalizeBookPipelineMode(
  requestedMode: BookPipelineCreditMode | string | undefined,
  userTier = 'free'
): BookPipelineCreditMode {
  if (userTier.toLowerCase() === 'free') return 'draft';
  return requestedMode === 'cinematic' ? 'cinematic' : 'draft';
}

function tierRate(rate: number | Partial<Record<Tier, number>>, userTier = 'free'): number {
  if (typeof rate === 'number') return rate;
  const tier = userTier.toLowerCase() as Tier;
  return rate[tier] ?? rate.pro ?? rate.free ?? 1;
}

const roundUp = (value: number) => Math.max(1, Math.ceil(value));

export function estimateImageCredits(
  count = 1,
  mode: BookPipelineCreditMode = 'draft',
  userTier = 'free'
): number {
  const effectiveMode = normalizeBookPipelineMode(mode, userTier);
  const rate = tierRate(BOOK_PIPELINE_CREDIT_RATES[effectiveMode].image, userTier);
  return Math.max(0, Math.ceil(count)) * rate;
}

export function estimateScriptCredits(
  mode: BookPipelineCreditMode = 'draft',
  userTier = 'free',
  estimatedTokens = 1000
): number {
  const effectiveMode = normalizeBookPipelineMode(mode, userTier);
  const rate = tierRate(BOOK_PIPELINE_CREDIT_RATES[effectiveMode].scriptPer1kTokens, userTier);
  return Math.max(1, Math.ceil(estimatedTokens / 1000)) * rate;
}

export function estimateUpscaleCredits(count = 1): number {
  return Math.max(0, Math.ceil(count)) * CREDIT_COSTS.UPSCALE;
}

export function estimateAudioCredits(
  seconds: number,
  mode: BookPipelineCreditMode = 'draft',
  userTier = 'free'
): number {
  const effectiveMode = normalizeBookPipelineMode(mode, userTier);
  return roundUp(seconds * BOOK_PIPELINE_CREDIT_RATES[effectiveMode].audioPerSecond);
}

export function estimateAudioCreditsFromScenes(
  sceneCount: number,
  averageSecondsPerScene = DEFAULT_AUDIO_SECONDS_PER_SCENE,
  mode: BookPipelineCreditMode = 'draft',
  userTier = 'free'
): number {
  if (sceneCount <= 0) return 0;
  return estimateAudioCredits(sceneCount * averageSecondsPerScene, mode, userTier);
}

export function estimateVideoCredits(
  seconds: number,
  mode: BookPipelineCreditMode = 'draft',
  userTier = 'free'
): number {
  const effectiveMode = normalizeBookPipelineMode(mode, userTier);
  return roundUp(seconds * BOOK_PIPELINE_CREDIT_RATES[effectiveMode].videoPerSecond);
}

export function estimateVideoCreditsFromShots(
  shotCount: number,
  averageSecondsPerShot = DEFAULT_VIDEO_SECONDS_PER_SHOT,
  mode: BookPipelineCreditMode = 'draft',
  userTier = 'free'
): number {
  if (shotCount <= 0) return 0;
  return estimateVideoCredits(shotCount * averageSecondsPerShot, mode, userTier);
}

export function getInsufficientCreditsTooltip(balance: number, required: number): string {
  return `Insufficient credits (${balance} available, ${required} required)`;
}
