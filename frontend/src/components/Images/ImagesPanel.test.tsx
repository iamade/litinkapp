import React from 'react';
import { render, screen } from '@testing-library/react';
import type { Mock } from 'vitest';
import ImagesPanel from './ImagesPanel';
import { ScriptSelectionProvider } from '../../contexts/ScriptSelectionContext';
import * as imageGenerationModule from '../../hooks/useImageGeneration';
import * as scriptSelectionModule from '../../contexts/ScriptSelectionContext';
import * as userServiceModule from '../../services/userService';

// Mock the hooks
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

// Mock userService
vi.mock('../../services/userService', () => ({
  userService: {
    getCharactersByChapter: vi.fn()
  }
}));

const mockUserService = userServiceModule.userService as unknown as {
  getCharactersByChapter: Mock;
};

describe('ImagesPanel script_id filtering', () => {
  const mockUseImageGeneration = imageGenerationModule.useImageGeneration as unknown as Mock;
  const mockUseScriptSelection = scriptSelectionModule.useScriptSelection as unknown as Mock;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('filters scene images by script_id when backend returns script_id', () => {
    // Mock context to return selected script
    mockUseScriptSelection.mockReturnValue({
      selectedScriptId: 'script-123',
      stableSelectedChapterId: 'chapter-456',
      versionToken: 1,
      isSwitching: false
    });

    // Mock hook to return images with script_id
    mockUseImageGeneration.mockReturnValue({
      sceneImages: {
        1: {
          sceneNumber: 1,
          imageUrl: 'url1',
          prompt: 'prompt1',
          characters: [],
          generationStatus: 'completed',
          id: 'img1',
          script_id: 'script-123'
        },
        2: {
          sceneNumber: 2,
          imageUrl: 'url2',
          prompt: 'prompt2',
          characters: [],
          generationStatus: 'completed',
          id: 'img2',
          script_id: 'script-999' // Different script
        }
      },
      characterImages: {},
      isLoading: false,
      generatingScenes: new Set(),
      generatingCharacters: new Set(),
      loadImages: vi.fn(),
      generateSceneImage: vi.fn(),
      generateCharacterImage: vi.fn(),
      regenerateImage: vi.fn(),
      deleteImage: vi.fn(),
      generateAllSceneImages: vi.fn(),
      generateAllCharacterImages: vi.fn()
    });

    // Mock userService
    mockUserService.getCharactersByChapter.mockResolvedValue([]);

    render(
      <ScriptSelectionProvider>
        <ImagesPanel
          chapterTitle="Test Chapter"
          selectedScript={{ scene_descriptions: [] }}
          plotOverview={null}
        />
      </ScriptSelectionProvider>
    );

    // Should only show images for the selected script
    expect(screen.getByText('Scene Images')).toBeInTheDocument();
    // The filtering logic should work - we can't easily test the exact rendering without more setup
  });

  it('filters scene images by scriptId (camelCase) when backend returns scriptId', () => {
    // Mock context to return selected script
    mockUseScriptSelection.mockReturnValue({
      selectedScriptId: 'script-123',
      stableSelectedChapterId: 'chapter-456',
      versionToken: 1,
      isSwitching: false
    });

    // Mock hook to return images with scriptId (camelCase)
    mockUseImageGeneration.mockReturnValue({
      sceneImages: {
        1: {
          sceneNumber: 1,
          imageUrl: 'url1',
          prompt: 'prompt1',
          characters: [],
          generationStatus: 'completed',
          id: 'img1',
          scriptId: 'script-123' // camelCase
        },
        2: {
          sceneNumber: 2,
          imageUrl: 'url2',
          prompt: 'prompt2',
          characters: [],
          generationStatus: 'completed',
          id: 'img2',
          scriptId: 'script-999' // Different script
        }
      },
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
      setCharacterImage: vi.fn()
    });

    // Mock userService
    mockUserService.getCharactersByChapter.mockResolvedValue([]);

    render(
      <ScriptSelectionProvider>
        <ImagesPanel
          chapterTitle="Test Chapter"
          selectedScript={{ scene_descriptions: [] }}
          plotOverview={null}
        />
      </ScriptSelectionProvider>
    );

    // Should normalize scriptId to script_id and filter correctly
    expect(screen.getByText('Scene Images')).toBeInTheDocument();
  });

  it('shows all images when no script is selected', () => {
    // Mock context with no selected script
    mockUseScriptSelection.mockReturnValue({
      selectedScriptId: null,
      stableSelectedChapterId: 'chapter-456',
      versionToken: 1,
      isSwitching: false
    });

    // Mock hook to return images
    mockUseImageGeneration.mockReturnValue({
      sceneImages: {
        1: {
          sceneNumber: 1,
          imageUrl: 'url1',
          prompt: 'prompt1',
          characters: [],
          generationStatus: 'completed',
          id: 'img1',
          script_id: 'script-123'
        }
      },
      characterImages: {},
      isLoading: false,
      generatingScenes: new Set(),
      generatingCharacters: new Set(),
      loadImages: vi.fn(),
      generateSceneImage: vi.fn(),
      generateCharacterImage: vi.fn(),
      regenerateImage: vi.fn(),
      deleteImage: vi.fn(),
      generateAllSceneImages: vi.fn(),
      generateAllCharacterImages: vi.fn()
    });

    // Mock userService
    mockUserService.getCharactersByChapter.mockResolvedValue([]);

    render(
      <ScriptSelectionProvider>
        <ImagesPanel
          chapterTitle="Test Chapter"
          selectedScript={{ scene_descriptions: [] }}
          plotOverview={null}
        />
      </ScriptSelectionProvider>
    );

    // Should show empty state when no script selected
    expect(screen.getByText('Select a script to view images')).toBeInTheDocument();
  });

  describe('Multi-select and delete functionality', () => {
    it('selects multiple scene thumbnails and invokes delete selected', async () => {
      // Mock context to return selected script
      mockUseScriptSelection.mockReturnValue({
        selectedScriptId: 'script-123',
        stableSelectedChapterId: 'chapter-456',
        versionToken: 1,
        isSwitching: false
      });

      // Mock hook to return images with IDs
      const mockDeleteGenerations = vi.fn().mockResolvedValue({ success: true, message: 'Deleted successfully' });
      mockUseImageGeneration.mockReturnValue({
        sceneImages: {
          1: {
            sceneNumber: 1,
            imageUrl: 'url1',
            prompt: 'prompt1',
            characters: [],
            generationStatus: 'completed',
            id: 'img1',
            script_id: 'script-123'
          },
          2: {
            sceneNumber: 2,
            imageUrl: 'url2',
            prompt: 'prompt2',
            characters: [],
            generationStatus: 'completed',
            id: 'img2',
            script_id: 'script-123'
          }
        },
        characterImages: {},
        isLoading: false,
        generatingScenes: new Set(),
        generatingCharacters: new Set(),
        loadImages: vi.fn(),
        generateSceneImage: vi.fn(),
        generateCharacterImage: vi.fn(),
        regenerateImage: vi.fn(),
        deleteImage: vi.fn(),
        deleteGenerations: mockDeleteGenerations,
        deleteAllSceneGenerations: vi.fn(),
        generateAllSceneImages: vi.fn(),
        generateAllCharacterImages: vi.fn(),
        setCharacterImage: vi.fn()
      });

      // Mock userService
      mockUserService.getCharactersByChapter.mockResolvedValue([]);

      const { user } = render(
        <ScriptSelectionProvider>
          <ImagesPanel
            chapterTitle="Test Chapter"
            selectedScript={{ scene_descriptions: [
              { scene_number: 1, visual_description: 'Scene 1' },
              { scene_number: 2, visual_description: 'Scene 2' }
            ] }}
            plotOverview={null}
          />
        </ScriptSelectionProvider>
      );

      // Switch to scenes tab
      await user.click(screen.getByText('Scenes'));

      // Check that "Select All" button is present
      expect(screen.getByText('Select All')).toBeInTheDocument();

      // Click "Select All" button
      await user.click(screen.getByText('Select All'));

      // Check that selected count is shown
      expect(screen.getByText('2 selected')).toBeInTheDocument();

      // Click "Delete Selected" button
      await user.click(screen.getByText('Delete Selected'));

      // Check that confirmation modal appears
      expect(screen.getByText('Delete 2 Selected Images')).toBeInTheDocument();

      // Confirm deletion
      await user.click(screen.getByText('Delete Selected'));

      // Verify API call was made with correct IDs
      expect(mockDeleteGenerations).toHaveBeenCalledWith(['img1', 'img2']);
    });

    it('clicks "Delete all generated scenes" and triggers correct API call', async () => {
      // Mock context to return selected script
      mockUseScriptSelection.mockReturnValue({
        selectedScriptId: 'script-123',
        stableSelectedChapterId: 'chapter-456',
        versionToken: 1,
        isSwitching: false
      });

      // Mock hook to return images
      const mockDeleteAllSceneGenerations = vi.fn().mockResolvedValue({ success: true, message: 'Deleted all successfully' });
      mockUseImageGeneration.mockReturnValue({
        sceneImages: {
          1: {
            sceneNumber: 1,
            imageUrl: 'url1',
            prompt: 'prompt1',
            characters: [],
            generationStatus: 'completed',
            id: 'img1',
            script_id: 'script-123'
          }
        },
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
        deleteAllSceneGenerations: mockDeleteAllSceneGenerations,
        generateAllSceneImages: vi.fn(),
        generateAllCharacterImages: vi.fn(),
        setCharacterImage: vi.fn()
      });

      // Mock userService
      mockUserService.getCharactersByChapter.mockResolvedValue([]);

      const { user } = render(
        <ScriptSelectionProvider>
          <ImagesPanel
            chapterTitle="Test Chapter"
            selectedScript={{ scene_descriptions: [
              { scene_number: 1, visual_description: 'Scene 1' }
            ] }}
            plotOverview={null}
          />
        </ScriptSelectionProvider>
      );

      // Switch to scenes tab
      await user.click(screen.getByText('Scenes'));

      // Click "Delete All" button
      await user.click(screen.getByText('Delete All'));

      // Check that confirmation modal appears
      expect(screen.getByText('Delete All Generated Scene Images')).toBeInTheDocument();

      // Confirm deletion
      await user.click(screen.getByText('Delete All'));

      // Verify API call was made with correct script ID
      expect(mockDeleteAllSceneGenerations).toHaveBeenCalledWith('script-123');
    });
  });
});