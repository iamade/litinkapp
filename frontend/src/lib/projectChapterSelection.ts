export type ChapterLike = {
  id: string;
  content?: {
    chapter_id?: string | null;
  } | null;
} | null;

// KAN-142: Project artifacts can have an artifact id that differs from the
// real Chapter table id used by storyboard/images/audio/video APIs.
export const getActualChapterId = (chapter: ChapterLike): string => {
  if (!chapter) return '';
  return chapter.content?.chapter_id || chapter.id;
};

export const getScriptSceneImageUrls = (
  sceneImages: Record<string | number, any>,
  selectedScriptId?: string | null
): string[] => {
  return Object.values(sceneImages)
    .flat()
    .filter((img: any) => {
      const normalizedScriptId = img.script_id || img.scriptId;
      return img.imageUrl && (!selectedScriptId || normalizedScriptId === selectedScriptId);
    })
    .sort((a: any, b: any) => a.sceneNumber - b.sceneNumber)
    .map((img: any) => img.imageUrl);
};
