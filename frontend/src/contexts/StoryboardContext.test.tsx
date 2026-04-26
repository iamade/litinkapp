import { describe, expect, it } from 'vitest';
import { mapAudioFiles } from './StoryboardContext';

describe('KAN-142 storyboard audio hydration', () => {
  it('maps Script F chapter audio using metadata.scene_number before legacy/root scene fallbacks', () => {
    const mapped = mapAudioFiles([
      {
        id: 'script-f-scene-1',
        script_id: 'script-F',
        generation_status: 'completed',
        audio_url: 'https://cdn.example/audio/scene-1.mp3',
        audio_type: 'narrator',
        scene_id: 99,
        scene_number: 98,
        metadata: { scene_number: 1, scene: 97 },
      },
      {
        id: 'script-f-scene-2',
        script_id: 'script-F',
        status: 'completed',
        url: 'https://cdn.example/audio/scene-2.mp3',
        type: 'character',
        scene_id: 88,
        metadata: { scene_number: '2' },
      },
    ], 'script-F');

    expect(Object.keys(mapped).map(Number).sort()).toEqual([1, 2]);
    expect(mapped[1]).toHaveLength(1);
    expect(mapped[1][0]).toMatchObject({
      id: 'script-f-scene-1',
      type: 'narration',
      sceneNumber: 1,
      url: 'https://cdn.example/audio/scene-1.mp3',
    });
    expect(mapped[2][0]).toMatchObject({
      id: 'script-f-scene-2',
      type: 'dialogue',
      sceneNumber: 2,
      url: 'https://cdn.example/audio/scene-2.mp3',
    });
  });

  it('does not hydrate failed, no-url, null-script, bogus-scene, or cross-script rows', () => {
    const mapped = mapAudioFiles([
      {
        id: 'valid-script-f-scene-1',
        script_id: 'script-F',
        generation_status: 'completed',
        audio_url: 'https://cdn.example/audio/valid.mp3',
        metadata: { scene_number: 1 },
      },
      {
        id: 'failed-row',
        script_id: 'script-F',
        generation_status: 'failed',
        audio_url: 'https://cdn.example/audio/failed.mp3',
        metadata: { scene_number: 1 },
      },
      {
        id: 'no-url-row',
        script_id: 'script-F',
        generation_status: 'completed',
        metadata: { scene_number: 1 },
      },
      {
        id: 'null-script-row',
        script_id: null,
        generation_status: 'completed',
        audio_url: 'https://cdn.example/audio/null-script.mp3',
        metadata: { scene_number: 1 },
      },
      {
        id: 'bogus-scene-row',
        script_id: 'script-F',
        generation_status: 'completed',
        audio_url: 'https://cdn.example/audio/bogus.mp3',
        metadata: { scene_number: 'bogus' },
      },
      {
        id: 'cross-script-row',
        script_id: 'script-A',
        generation_status: 'completed',
        audio_url: 'https://cdn.example/audio/cross-script.mp3',
        metadata: { scene_number: 1 },
      },
    ], 'script-F');

    expect(mapped).toEqual({
      1: [expect.objectContaining({ id: 'valid-script-f-scene-1', sceneNumber: 1 })],
    });
  });
});
