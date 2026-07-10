/**
 * CharacterReferenceInjector — KAN-371
 *
 * Injects character visual references into image/video generation prompts.
 * Builds a structured reference block from character data (appearance, traits,
 * visual markers) and appends it to the generation prompt for consistent
 * character rendering across generated media.
 */

export interface CharacterReference {
  name: string;
  appearance?: string;
  gender?: string;
  age?: string;
  hair_color?: string;
  eye_color?: string;
  skin_tone?: string;
  build?: string;
  height?: string;
  distinctive_features?: string;
  clothing_style?: string;
  visual_markers?: string[];
  reference_image_url?: string;
}

export interface InjectedPrompt {
  original_prompt: string;
  enhanced_prompt: string;
  character_references: CharacterReference[];
  reference_block: string;
}

/**
 * Build a structured visual reference block from character data.
 * This block is appended to image/video generation prompts to ensure
 * consistent character appearance across generated media.
 */
export function buildCharacterReferenceBlock(
  characters: CharacterReference[]
): string {
  if (!characters || characters.length === 0) return "";

  const blocks = characters.map((char) => {
    const parts: string[] = [];

    parts.push(`[CHARACTER: ${char.name}]`);

    if (char.appearance) {
      parts.push(`Appearance: ${char.appearance}`);
    } else {
      // Build appearance from individual traits
      const traits: string[] = [];
      if (char.gender) traits.push(char.gender);
      if (char.age) traits.push(`${char.age} years old`);
      if (char.build) traits.push(char.build);
      if (char.height) traits.push(char.height);
      if (char.skin_tone) traits.push(`${char.skin_tone} skin`);
      if (traits.length > 0) parts.push(`Appearance: ${traits.join(", ")}`);
    }

    if (char.hair_color) parts.push(`Hair: ${char.hair_color}`);
    if (char.eye_color) parts.push(`Eyes: ${char.eye_color}`);
    if (char.clothing_style) parts.push(`Clothing: ${char.clothing_style}`);
    if (char.distinctive_features)
      parts.push(`Distinctive features: ${char.distinctive_features}`);

    if (char.visual_markers && char.visual_markers.length > 0) {
      parts.push(`Visual markers: ${char.visual_markers.join(", ")}`);
    }

    return parts.join("; ");
  });

  return `\n\n--- CHARACTER VISUAL REFERENCES ---\n${blocks.join("\n")}\n--- END REFERENCES ---`;
}

/**
 * Inject character visual references into a generation prompt.
 * Returns the enhanced prompt with character reference block appended.
 */
export function injectCharacterReferences(
  prompt: string,
  characters: CharacterReference[]
): InjectedPrompt {
  const referenceBlock = buildCharacterReferenceBlock(characters);

  return {
    original_prompt: prompt,
    enhanced_prompt: referenceBlock
      ? `${prompt}\n${referenceBlock}`
      : prompt,
    character_references: characters,
    reference_block: referenceBlock,
  };
}

/**
 * Extract character references from a LitInkAI character object.
 * Handles the various shapes character data can take across the app.
 */
export function extractCharacterReference(
  character: any
): CharacterReference | null {
  if (!character) return null;

  return {
    name: character.name || character.character_name || "Unknown",
    appearance: character.appearance || character.physical_description || undefined,
    gender: character.gender || character.voice_gender || undefined,
    age: character.age || undefined,
    hair_color: character.hair_color || undefined,
    eye_color: character.eye_color || undefined,
    skin_tone: character.skin_tone || undefined,
    build: character.build || character.body_type || undefined,
    height: character.height || undefined,
    distinctive_features:
      character.distinctive_features || character.unique_traits || undefined,
    clothing_style: character.clothing_style || character.attire || undefined,
    visual_markers: character.visual_markers || character.visual_tags || undefined,
    reference_image_url:
      character.reference_image_url ||
      character.avatar_url ||
      character.image_url ||
      undefined,
  };
}

/**
 * Build a batch reference block for multiple characters in a scene.
 */
export function buildSceneCharacterReferences(
  characters: any[],
  sceneDescription: string
): InjectedPrompt {
  const refs = characters
    .map(extractCharacterReference)
    .filter((r): r is CharacterReference => r !== null);

  return injectCharacterReferences(sceneDescription, refs);
}
