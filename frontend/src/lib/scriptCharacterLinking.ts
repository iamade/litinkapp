/**
 * KAN-331: script character pill ↔ Plot Overview character resolution.
 *
 * A pill slot is "unresolved" when its id is empty OR the id does not exist in
 * the current Plot Overview character list (stale ids from a regenerated plot
 * overview). Unresolved slots are auto-linked on exact case-insensitive,
 * whitespace-trimmed name match. Resolved slots (e.g. manual links) are
 * preserved, and unmatched script-only characters keep their warning state.
 */

export interface LinkablePlotCharacter {
  id: string;
  name: string;
}

export interface AutoLinkResult {
  characterIds: string[];
  changed: boolean;
}

export function autoLinkCharacterIds(
  characters: string[],
  characterIds: (string | undefined)[] | undefined,
  plotCharacters: LinkablePlotCharacter[]
): AutoLinkResult {
  const ids = [...(characterIds ?? [])];
  // Pad character_ids to match characters length
  while (ids.length < characters.length) {
    ids.push('');
  }

  const knownIds = new Set(plotCharacters.map((pc) => pc.id));
  let changed = false;

  characters.forEach((name, idx) => {
    const currentId = ids[idx] ?? '';
    // Already linked to a current Plot Overview character (manual links land here)
    if (currentId && knownIds.has(currentId)) return;

    // Case-insensitive exact match against plot overview characters
    const match = plotCharacters.find(
      (pc) => pc.name.toLowerCase().trim() === String(name).toLowerCase().trim()
    );
    if (match) {
      ids[idx] = match.id;
      changed = true;
    }
  });

  return { characterIds: ids, changed };
}
