// KAN-186: shared mapping of AI-generated character details onto character form state.

/** Values offered by the Role <select> in the character forms (placeholder excluded). */
export const CHARACTER_ROLE_OPTIONS = [
  'protagonist',
  'antagonist',
  'supporting',
  'mentor',
  'sidekick',
] as const;

/** Values offered by the Accent <select> in the character forms. */
export const CHARACTER_ACCENT_OPTIONS = [
  'neutral',
  'nigerian',
  'british',
  'american',
  'indian',
  'australian',
  'jamaican',
  'french',
  'german',
] as const;

/** Voice gender values AI Assist may prefill ('auto' stays a user-only default). */
export const CHARACTER_VOICE_GENDER_OPTIONS = ['male', 'female'] as const;

/** Character form fields populated by AI Assist (optional so Partial edit drafts fit too). */
export interface CharacterDetailFields {
  physical_description?: string;
  personality?: string;
  character_arc?: string;
  want?: string;
  need?: string;
  lie?: string;
  ghost?: string;
  role?: string;
  accent?: string;
  voice_gender?: string;
  voice_characteristics?: string;
}

function pickValidRole(value: string | undefined, prev: string | undefined): string | undefined {
  return value && (CHARACTER_ROLE_OPTIONS as readonly string[]).includes(value) ? value : prev;
}

function pickValidAccent(value: string | undefined, prev: string | undefined): string | undefined {
  const normalized = value?.trim().toLowerCase();
  return normalized && (CHARACTER_ACCENT_OPTIONS as readonly string[]).includes(normalized)
    ? normalized
    : prev;
}

function pickValidVoiceGender(
  value: string | undefined,
  prev: string | undefined
): string | undefined {
  return value && (CHARACTER_VOICE_GENDER_OPTIONS as readonly string[]).includes(value)
    ? value
    : prev;
}

/**
 * Merge AI-generated character details into existing character form state.
 *
 * Free-text fields only overwrite when the response provides a non-empty value;
 * constrained selects (role/accent/voice_gender) only accept values the UI offers,
 * so unexpected AI output never leaves the selects in an invalid state.
 * Accent is matched case-insensitively (normalized to the lowercase option value).
 */
export function applyGeneratedCharacterDetails<T extends CharacterDetailFields>(
  prev: T,
  details: Partial<CharacterDetailFields>
): T {
  return {
    ...prev,
    physical_description: details.physical_description || prev.physical_description,
    personality: details.personality || prev.personality,
    character_arc: details.character_arc || prev.character_arc,
    want: details.want || prev.want,
    need: details.need || prev.need,
    lie: details.lie || prev.lie,
    ghost: details.ghost || prev.ghost,
    role: pickValidRole(details.role, prev.role),
    accent: pickValidAccent(details.accent, prev.accent),
    voice_gender: pickValidVoiceGender(details.voice_gender, prev.voice_gender),
    voice_characteristics: details.voice_characteristics || prev.voice_characteristics,
  } as T;
}
