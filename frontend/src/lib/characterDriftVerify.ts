/**
 * Character Drift Verification — KAN-371
 *
 * Detects when generated images drift from established character appearance.
 * Compares generated image metadata/prompts against stored character references
 * to flag potential visual inconsistencies.
 */

export interface DriftCheckResult {
  character_name: string;
  drift_detected: boolean;
  drift_score: number; // 0-1, higher = more drift
  mismatched_traits: string[];
  warnings: string[];
  recommendation?: string;
}

export interface CharacterTrait {
  key: string;
  expected: string;
  actual?: string;
}

const TRAIT_WEIGHTS: Record<string, number> = {
  hair_color: 0.15,
  eye_color: 0.10,
  skin_tone: 0.15,
  gender: 0.20,
  build: 0.10,
  height: 0.05,
  age: 0.10,
  clothing_style: 0.10,
  distinctive_features: 0.05,
};

/**
 * Check if a generated prompt contains character traits that match
 * the stored character reference. Returns a drift score and list of
 * mismatched traits.
 *
 * This is a heuristic check — it compares the prompt text against
 * expected character traits using keyword matching.
 */
export function verifyCharacterDrift(
  characterName: string,
  characterTraits: Record<string, string>,
  generatedPrompt: string
): DriftCheckResult {
  const promptLower = generatedPrompt.toLowerCase();
  const mismatched_traits: string[] = [];
  const warnings: string[] = [];
  let totalWeight = 0;
  let mismatchWeight = 0;

  for (const [trait, expectedValue] of Object.entries(characterTraits)) {
    if (!expectedValue || expectedValue === "unknown" || expectedValue === "auto") {
      continue;
    }

    const weight = TRAIT_WEIGHTS[trait] || 0.05;
    totalWeight += weight;

    const expectedLower = expectedValue.toLowerCase();
    const traitMentioned = promptLower.includes(expectedLower);

    if (!traitMentioned) {
      // Check for contradictory values
      const contradictory = findContradictoryTrait(trait, expectedLower, promptLower);
      if (contradictory) {
        mismatched_traits.push(`${trait}: expected "${expectedValue}", found "${contradictory}"`);
        mismatchWeight += weight;
        warnings.push(
          `Character "${characterName}" ${trait} may have drifted: expected "${expectedValue}" but prompt mentions "${contradictory}"`
        );
      }
    }
  }

  const driftScore = totalWeight > 0 ? mismatchWeight / totalWeight : 0;

  return {
    character_name: characterName,
    drift_detected: driftScore > 0.3,
    drift_score: Math.round(driftScore * 100) / 100,
    mismatched_traits,
    warnings,
    recommendation:
      driftScore > 0.5
        ? `High drift detected for "${characterName}". Consider regenerating with explicit character reference.`
        : driftScore > 0.3
          ? `Moderate drift for "${characterName}". Review generated image for consistency.`
          : undefined,
  };
}

/**
 * Check multiple characters against a generated prompt.
 */
export function verifySceneDrift(
  characters: Array<{ name: string; traits: Record<string, string> }>,
  generatedPrompt: string
): DriftCheckResult[] {
  return characters.map((char) =>
    verifyCharacterDrift(char.name, char.traits, generatedPrompt)
  );
}

/**
 * Simple contradictory trait detection.
 * Looks for known opposite values in the prompt.
 */
function findContradictoryTrait(
  trait: string,
  expected: string,
  prompt: string
): string | null {
  const contradictions: Record<string, Record<string, string[]>> = {
    hair_color: {
      black: ["blonde", "blond", "red hair", "ginger", "white hair", "gray hair", "grey hair"],
      blonde: ["black hair", "brunette", "dark hair", "red hair", "ginger"],
      brown: ["blonde", "blond", "red hair", "ginger", "white hair"],
      red: ["black hair", "blonde", "blond", "brown hair", "white hair"],
      white: ["black hair", "blonde", "blond", "brown hair", "red hair"],
    },
    eye_color: {
      blue: ["brown eyes", "green eyes", "dark eyes", "black eyes"],
      brown: ["blue eyes", "green eyes", "light eyes"],
      green: ["brown eyes", "blue eyes", "dark eyes"],
    },
    gender: {
      male: ["woman", "female", "girl", "lady", "feminine"],
      female: ["man", "male", "boy", "gentleman", "masculine"],
    },
    build: {
      slim: ["muscular", "heavy", "large", "bulky", "stocky", "overweight"],
      muscular: ["slim", "thin", "frail", "slender", "skinny"],
      heavy: ["slim", "thin", "slender", "athletic", "fit"],
    },
  };

  const traitContradictions = contradictions[trait];
  if (!traitContradictions) return null;

  const opposites = traitContradictions[expected];
  if (!opposites) return null;

  for (const opposite of opposites) {
    if (prompt.includes(opposite)) {
      return opposite;
    }
  }

  return null;
}
