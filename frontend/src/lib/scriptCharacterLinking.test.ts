import { describe, expect, it } from 'vitest';
import { autoLinkCharacterIds } from './scriptCharacterLinking';

const plotCharacters = [
  { id: 'id-ishmael', name: 'Ishmael' },
  { id: 'id-ahab', name: 'Captain Ahab' },
  { id: 'id-queequeg', name: 'Queequeg' },
];

describe('autoLinkCharacterIds (KAN-331)', () => {
  it('auto-links exact-name matches so pills turn green', () => {
    const { characterIds, changed } = autoLinkCharacterIds(
      ['Ishmael', 'Captain Ahab'],
      ['', ''],
      plotCharacters
    );

    expect(changed).toBe(true);
    expect(characterIds).toEqual(['id-ishmael', 'id-ahab']);
  });

  it('preserves manual links (resolved ids are never overwritten)', () => {
    const { characterIds, changed } = autoLinkCharacterIds(
      ['Ishmael', 'Captain Ahab'],
      ['id-queequeg', 'id-ahab'],
      plotCharacters
    );

    // 'Ishmael' pill was manually linked to Queequeg — must stay untouched
    expect(changed).toBe(false);
    expect(characterIds).toEqual(['id-queequeg', 'id-ahab']);
  });

  it('leaves unmatched script-only characters unlinked (warning state)', () => {
    const { characterIds, changed } = autoLinkCharacterIds(
      ['Ishmael', 'Elijah'],
      ['', ''],
      plotCharacters
    );

    expect(changed).toBe(true); // Ishmael got linked
    expect(characterIds).toEqual(['id-ishmael', '']); // Elijah stays warning
  });

  it('repairs stale ids that no longer resolve to current plot characters', () => {
    // Regenerated plot overview orphaned the old uuid; name still matches
    const { characterIds, changed } = autoLinkCharacterIds(
      ['Ishmael'],
      ['old-orphaned-uuid'],
      plotCharacters
    );

    expect(changed).toBe(true);
    expect(characterIds).toEqual(['id-ishmael']);
  });

  it('leaves unresolvable stale ids untouched when no name match exists', () => {
    const { characterIds, changed } = autoLinkCharacterIds(
      ['Elijah'],
      ['old-orphaned-uuid'],
      plotCharacters
    );

    expect(changed).toBe(false);
    expect(characterIds).toEqual(['old-orphaned-uuid']);
  });

  it('pads short character_ids arrays to the characters length', () => {
    const { characterIds } = autoLinkCharacterIds(
      ['Ishmael', 'Elijah', 'Peleg'],
      ['id-ishmael'],
      plotCharacters
    );

    expect(characterIds).toEqual(['id-ishmael', '', '']);
  });

  it('matches case-insensitively and trims whitespace', () => {
    const { characterIds, changed } = autoLinkCharacterIds(
      ['  ishmael ', 'CAPTAIN AHAB'],
      ['', ''],
      plotCharacters
    );

    expect(changed).toBe(true);
    expect(characterIds).toEqual(['id-ishmael', 'id-ahab']);
  });

  it('handles undefined character_ids', () => {
    const { characterIds, changed } = autoLinkCharacterIds(
      ['Queequeg'],
      undefined,
      plotCharacters
    );

    expect(changed).toBe(true);
    expect(characterIds).toEqual(['id-queequeg']);
  });
});
