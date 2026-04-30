import React from 'react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import CharacterDropdown from './CharacterDropdown';

afterEach(() => {
  cleanup();
});

describe('KAN-265 CharacterDropdown entityType creation path', () => {
  it('emits object entityType when creating a new object pill', () => {
    const onCreateNew = vi.fn();

    render(
      <CharacterDropdown
        value="Ancient Amulet"
        plotCharacters={[]}
        onSelect={vi.fn()}
        onCreateNew={onCreateNew}
        onCancel={vi.fn()}
        autoFocus={false}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /object/i }));

    expect(onCreateNew).toHaveBeenCalledWith('Ancient Amulet', 'object');
  });

  it('emits location entityType when creating a new location pill', () => {
    const onCreateNew = vi.fn();

    render(
      <CharacterDropdown
        value="Hidden Library"
        plotCharacters={[]}
        onSelect={vi.fn()}
        onCreateNew={onCreateNew}
        onCancel={vi.fn()}
        autoFocus={false}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /location/i }));

    expect(onCreateNew).toHaveBeenCalledWith('Hidden Library', 'location');
  });

  it('keeps BookViewForEntertainment wired to pass entityType into createPlotCharacter', () => {
    const bookViewSource = readFileSync(
      resolve(process.cwd(), 'src/pages/BookViewForEntertainment.tsx'),
      'utf8'
    );

    expect(bookViewSource).toContain(
      "onCreatePlotCharacter={async (name: string, entityType: 'character' | 'object' | 'location' = 'character')"
    );
    expect(bookViewSource).toContain('userService.createPlotCharacter(id, name, entityType)');
  });
});
