export interface Kan86VideoSceneRef {
  id: string;
  sceneNumber: number;
  shotIndex?: number;
}

export interface Kan86AudioRef {
  id?: string;
  url?: string;
  audio_url?: string;
  status?: string;
  duration?: number;
  duration_seconds?: number;
  sceneNumber?: number;
  scene_number?: number;
  scene?: number;
  shotIndex?: number;
}

export interface Kan86MissingAudioScene {
  sceneNumber: number;
  shotIndex?: number;
  reason: string;
}

export interface Kan86AudioDiagnostic {
  sceneNumber: number;
  shotIndex?: number;
  scriptId?: string;
  chapterId?: string;
  audioId?: string;
  url?: string;
  status?: string;
  duration?: number;
}

export interface Kan86AudioPreflightResult {
  ok: boolean;
  missingScenes: Kan86MissingAudioScene[];
  selectedAudioIds: string[];
  diagnostics: Kan86AudioDiagnostic[];
}

export const isKan86UsableSceneAudio = (audio: Kan86AudioRef | null | undefined): boolean => {
  const status = String(audio?.status || 'completed').toLowerCase();
  const duration = Number(audio?.duration ?? audio?.duration_seconds ?? 0);
  const url = audio?.url || audio?.audio_url;

  return Boolean(
    audio?.id &&
    url &&
    status !== 'failed' &&
    status !== 'error' &&
    status !== 'pending' &&
    (duration === 0 || duration >= 5)
  );
};

export const buildKan86AudioPreflight = (
  targetScenes: Kan86VideoSceneRef[],
  getAudioForShot: (sceneNumber: number, shotIndex?: number) => Kan86AudioRef[],
  selectedAudioIds: Set<string> = new Set<string>(),
  scope: { scriptId?: string; chapterId?: string } = {}
): Kan86AudioPreflightResult => {
  const missingScenes: Kan86MissingAudioScene[] = [];
  const selectedAudioIdsForGeneration: string[] = [];
  const diagnostics: Kan86AudioDiagnostic[] = [];

  targetScenes.forEach(scene => {
    const sceneAudio = getAudioForShot(scene.sceneNumber, scene.shotIndex) || [];
    const usableSceneAudio = sceneAudio.filter(audio => {
      const audioScene = audio.sceneNumber ?? audio.scene_number ?? audio.scene;
      const audioShot = audio.shotIndex;
      const sameScene = typeof audioScene === 'number' ? audioScene === scene.sceneNumber : true;
      const sameShot = typeof audioShot === 'number' && typeof scene.shotIndex === 'number'
        ? audioShot === scene.shotIndex
        : true;
      return sameScene && sameShot && isKan86UsableSceneAudio(audio);
    });
    const selectedForScene = usableSceneAudio.filter(audio => audio.id && selectedAudioIds.has(audio.id));
    const chosenAudio = selectedForScene[0] || usableSceneAudio[0];

    if (!chosenAudio?.id) {
      const hasAudio = sceneAudio.length > 0;
      missingScenes.push({
        sceneNumber: scene.sceneNumber,
        shotIndex: scene.shotIndex,
        reason: hasAudio ? 'Audio exists but is wrong-scene, missing URL, pending/failed, or shorter than 5s.' : 'No scene-scoped audio mapped.'
      });
      return;
    }

    if (!selectedAudioIdsForGeneration.includes(chosenAudio.id)) {
      selectedAudioIdsForGeneration.push(chosenAudio.id);
    }

    diagnostics.push({
      sceneNumber: scene.sceneNumber,
      shotIndex: scene.shotIndex,
      scriptId: scope.scriptId,
      chapterId: scope.chapterId,
      audioId: chosenAudio.id,
      url: chosenAudio.url || chosenAudio.audio_url,
      status: chosenAudio.status || 'completed',
      duration: Number(chosenAudio.duration ?? chosenAudio.duration_seconds ?? 0)
    });
  });

  return {
    ok: missingScenes.length === 0,
    missingScenes,
    selectedAudioIds: selectedAudioIdsForGeneration,
    diagnostics
  };
};
