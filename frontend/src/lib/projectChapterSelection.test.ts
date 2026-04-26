import { describe, expect, it } from 'vitest';
import { getActualChapterId, getScriptSceneImageUrls } from './projectChapterSelection';

describe('KAN-142 project chapter selection helpers', () => {
  it('uses actual Chapter table id when artifact id differs', () => {
    expect(getActualChapterId({
      id: 'artifact-chapter-id',
      content: { chapter_id: 'actual-chapter-table-id' },
    })).toBe('actual-chapter-table-id');
  });

  it('falls back to artifact/project id for prompt-only virtual chapters', () => {
    expect(getActualChapterId({ id: 'virtual-project-id', content: {} })).toBe('virtual-project-id');
  });

  it('returns saved scene image URLs for the selected script only', () => {
    const urls = getScriptSceneImageUrls({
      2: [{ sceneNumber: 2, imageUrl: 'scene-2-url', script_id: 'script-A' }],
      1: [
        { sceneNumber: 1, imageUrl: 'scene-1-url', scriptId: 'script-A' },
        { sceneNumber: 1, imageUrl: 'other-script-url', script_id: 'script-B' },
      ],
    }, 'script-A');

    expect(urls).toEqual(['scene-1-url', 'scene-2-url']);
  });
});
