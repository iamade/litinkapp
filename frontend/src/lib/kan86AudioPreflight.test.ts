import { describe, expect, it } from 'vitest';
import { buildKan86AudioPreflight, isKan86UsableSceneAudio } from './kan86AudioPreflight';

describe('KAN-86 audio preflight', () => {
  it('blocks scenes without usable scene-scoped audio', () => {
    const result = buildKan86AudioPreflight(
      [{ id: 'scene-1', sceneNumber: 1, shotIndex: 0 }],
      () => [{ id: 'pending', url: 'https://cdn/audio.mp3', status: 'pending', duration: 8, sceneNumber: 1, shotIndex: 0 }]
    );

    expect(result.ok).toBe(false);
    expect(result.missingScenes).toHaveLength(1);
  });

  it('does not accept wrong-scene selected audio for a target scene', () => {
    const result = buildKan86AudioPreflight(
      [{ id: 'scene-1', sceneNumber: 1, shotIndex: 0 }],
      () => [{ id: 'wrong-scene', url: 'https://cdn/audio-2.mp3', status: 'completed', duration: 8, sceneNumber: 2, shotIndex: 0 }],
      new Set(['wrong-scene'])
    );

    expect(result.ok).toBe(false);
    expect(result.selectedAudioIds).toEqual([]);
  });

  it('returns selected usable scene audio and diagnostics', () => {
    const result = buildKan86AudioPreflight(
      [{ id: 'scene-1', sceneNumber: 1, shotIndex: 0 }],
      () => [{ id: 'audio-1', url: 'https://cdn/audio-1.mp3', status: 'completed', duration: 8, sceneNumber: 1, shotIndex: 0 }],
      new Set(['audio-1'])
    );

    expect(result.ok).toBe(true);
    expect(result.selectedAudioIds).toEqual(['audio-1']);
    expect(result.diagnostics[0]).toMatchObject({ sceneNumber: 1, audioId: 'audio-1', status: 'completed' });
  });

  it('treats missing urls and short durations as unusable', () => {
    expect(isKan86UsableSceneAudio({ id: 'no-url', status: 'completed', duration: 8 })).toBe(false);
    expect(isKan86UsableSceneAudio({ id: 'short', url: 'https://cdn/a.mp3', status: 'completed', duration: 3 })).toBe(false);
  });
});
