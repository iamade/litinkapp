import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import type { Mock } from 'vitest';
import ImagesPanel from './ImagesPanel';
import { ScriptSelectionProvider } from '../../contexts/ScriptSelectionContext';
import * as imageGenerationModule from '../../hooks/useImageGeneration';
import * as scriptSelectionModule from '../../contexts/ScriptSelectionContext';
import * as userServiceModule from '../../services/userService';

vi.mock('../../hooks/useImageGeneration', () => ({
  useImageGeneration: vi.fn()
}));

vi.mock('../../contexts/ScriptSelectionContext', async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    '../../contexts/ScriptSelectionContext'
  );
  return {
    ...actual,
    useScriptSelection: vi.fn()
  };
});

vi.mock('../../services/userService', () => ({
  userService: {
    getCharactersByChapter: vi.fn()
  }
}));

const mockUserService = userServiceModule.userService as unknown as {
  getCharactersByChapter: Mock;
};

const mockUseImageGeneration = imageGenerationModule.useImageGeneration as unknown as Mock;
const mockUseScriptSelection = scriptSelectionModule.useScriptSelection as unknown as Mock;

const sceneImage = (id: string, scriptIdField: 'script_id' | 'scriptId', scriptId: string, sceneNumber: number) => ({
  sceneNumber,
  imageUrl: 'https://example.test/' + id + '.png',
  prompt: id + ' prompt',
  characters: [],
  generationStatus: 'completed',
  id,
  [scriptIdField]: scriptId
});

const imageGenerationState = (sceneImages: Record<number, ReturnType<typeof sceneImage>[]>) => ({
  sceneImages,
  characterImages: {},
  isLoading: false,
  generatingScenes: new Set(),
  generatingCharacters: new Set(),
  loadImages: vi.fn(),
  generateSceneImage: vi.fn(),
  generateCharacterImage: vi.fn(),
  regenerateImage: vi.fn(),
  deleteImage: vi.fn(),
  deleteGenerations: vi.fn(),
  deleteAllSceneGenerations: vi.fn(),
  generateAllSceneImages: vi.fn(),
  generateAllCharacterImages: vi.fn(),
  setCharacterImage: vi.fn(),
  setSceneImages: vi.fn()
});

const scriptSelectionState = (selectedScriptId: string | null = 'script-123') => ({
  selectedScriptId,
  stableSelectedChapterId: 'chapter-456',
  versionToken: 1,
  isSwitching: false,
  selectedSceneImages: {},
  setSelectedSceneImage: vi.fn(),
  keySceneImages: {},
  deselectedImages: new Set(),
  storyboardDirty: false,
  imageOrderByScene: {},
  setKeySceneImage: vi.fn(),
  toggleDeselectedImage: vi.fn(),
  setImageOrder: vi.fn(),
  loadStoryboardConfig: vi.fn(),
  getStoryboardConfig: vi.fn(() => ({})),
  markStoryboardClean: vi.fn()
});

const renderImagesPanel = (sceneImages: Record<number, ReturnType<typeof sceneImage>[]>, selectedScriptId: string | null = 'script-123') => {
  mockUseScriptSelection.mockReturnValue(scriptSelectionState(selectedScriptId));
  mockUseImageGeneration.mockReturnValue(imageGenerationState(sceneImages));
  mockUserService.getCharactersByChapter.mockResolvedValue([]);

  return render(
    <MemoryRouter>
      <ScriptSelectionProvider>
        <ImagesPanel
          chapterId="chapter-456"
          chapterTitle="Test Chapter"
          selectedScript={{
            scene_descriptions: [
              { scene_number: 1, visual_description: 'Scene 1' },
              { scene_number: 2, visual_description: 'Scene 2' }
            ]
          }}
          plotOverview={null}
        />
      </ScriptSelectionProvider>
    </MemoryRouter>
  );
};

const confirmationModal = (title: string) => {
  const titleElement = screen.getByText(title);
  const modal = titleElement.closest('div.fixed');
  if (!modal) throw new Error('Confirmation modal root was not found');
  return within(modal);
};

describe('ImagesPanel script_id filtering', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('filters scene images by script_id when backend returns script_id', async () => {
    const user = userEvent.setup();
    renderImagesPanel({
      1: [sceneImage('matching-image', 'script_id', 'script-123', 1)],
      2: [sceneImage('nonmatching-image', 'script_id', 'script-999', 2)]
    });

    await user.click(screen.getByRole('button', { name: /^Scenes/ }));
    expect(screen.getByRole('heading', { level: 4, name: 'Scene Images' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Select All' }));
    expect(screen.getByText('1 selected')).toBeInTheDocument();
  });

  it('filters scene images by scriptId (camelCase) when backend returns scriptId', async () => {
    const user = userEvent.setup();
    renderImagesPanel({
      1: [sceneImage('matching-image', 'scriptId', 'script-123', 1)],
      2: [sceneImage('nonmatching-image', 'scriptId', 'script-999', 2)]
    });

    await user.click(screen.getByRole('button', { name: /^Scenes/ }));
    expect(screen.getByRole('heading', { level: 4, name: 'Scene Images' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Select All' }));
    expect(screen.getByText('1 selected')).toBeInTheDocument();
  });

  it('shows all images when no script is selected', () => {
    renderImagesPanel({
      1: [sceneImage('image-1', 'script_id', 'script-123', 1)]
    }, null);

    expect(screen.getByText('Select a script to view images')).toBeInTheDocument();
  });

  describe('Multi-select and delete functionality', () => {
    it('selects multiple scene thumbnails and invokes delete selected', async () => {
      const user = userEvent.setup();
      const mockDeleteGenerations = vi.fn().mockResolvedValue({ success: true, message: 'Deleted successfully' });
      mockUseScriptSelection.mockReturnValue(scriptSelectionState());
      mockUseImageGeneration.mockReturnValue({
        ...imageGenerationState({
          1: [sceneImage('img1', 'script_id', 'script-123', 1)],
          2: [sceneImage('img2', 'script_id', 'script-123', 2)]
        }),
        deleteGenerations: mockDeleteGenerations
      });
      mockUserService.getCharactersByChapter.mockResolvedValue([]);

      render(
        <MemoryRouter>
          <ScriptSelectionProvider>
            <ImagesPanel
              chapterId="chapter-456"
              chapterTitle="Test Chapter"
              selectedScript={{
                scene_descriptions: [
                  { scene_number: 1, visual_description: 'Scene 1' },
                  { scene_number: 2, visual_description: 'Scene 2' }
                ]
              }}
              plotOverview={null}
            />
          </ScriptSelectionProvider>
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: /^Scenes/ }));
      expect(screen.getByRole('button', { name: 'Select All' })).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Select All' }));
      expect(screen.getByText('2 selected')).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: 'Delete Selected' }));
      expect(screen.getByText('Delete 2 Selected Images')).toBeInTheDocument();
      await user.click(confirmationModal('Delete 2 Selected Images').getByRole('button', { name: 'Delete Selected' }));
      expect(mockDeleteGenerations).toHaveBeenCalledWith(['img1', 'img2']);
    });

    it('clicks "Delete all generated scenes" and triggers correct API call', async () => {
      const user = userEvent.setup();
      const mockDeleteAllSceneGenerations = vi.fn().mockResolvedValue({ success: true, message: 'Deleted all successfully' });
      mockUseScriptSelection.mockReturnValue(scriptSelectionState());
      mockUseImageGeneration.mockReturnValue({
        ...imageGenerationState({
          1: [sceneImage('img1', 'script_id', 'script-123', 1)]
        }),
        deleteAllSceneGenerations: mockDeleteAllSceneGenerations
      });
      mockUserService.getCharactersByChapter.mockResolvedValue([]);

      render(
        <MemoryRouter>
          <ScriptSelectionProvider>
            <ImagesPanel
              chapterId="chapter-456"
              chapterTitle="Test Chapter"
              selectedScript={{ scene_descriptions: [{ scene_number: 1, visual_description: 'Scene 1' }] }}
              plotOverview={null}
            />
          </ScriptSelectionProvider>
        </MemoryRouter>
      );

      await user.click(screen.getByRole('button', { name: /^Scenes/ }));
      await user.click(screen.getByRole('button', { name: 'Delete All' }));
      expect(screen.getByText('Delete All Generated Scene Images')).toBeInTheDocument();
      await user.click(confirmationModal('Delete All Generated Scene Images').getByRole('button', { name: 'Delete All' }));
      expect(mockDeleteAllSceneGenerations).toHaveBeenCalledWith('script-123');
    });
  });
});
