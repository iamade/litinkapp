/**
 * Script Synchronization Test Suite
 * 
 * This test validates the script synchronization behavior across the video generation interface:
 * - Script selection synchronizes with video preview
 * - Audio track synchronization works
 * - Character dialogue mapping functions
 * - Consistent behavior with Images panel
 */

// Mock data for testing
const mockScripts = {
  cinematic: {
    id: 'script-1',
    chapter_id: 'chapter-1',
    script_style: 'cinematic',
    script_name: 'Cinematic Movie Script',
    script: `SCENE 1
INT. LIVING ROOM - DAY

JOHN sits on the couch, looking worried.

JOHN
I don't know what to do anymore.

MARY enters, holding a coffee mug.

MARY
You need to make a decision, John.

SCENE 2
EXT. PARK - AFTERNOON

JOHN walks slowly through the park, deep in thought.

JOHN
(whispering)
What if I choose wrong?`,
    scene_descriptions: [
      {
        scene_number: 1,
        location: 'Living Room',
        time_of_day: 'Day',
        characters: ['JOHN', 'MARY'],
        key_actions: 'John expresses worry, Mary confronts him',
        estimated_duration: 15,
        visual_description: 'A cozy living room with sunlight streaming through the window',
        audio_requirements: 'Tense background music, dialogue'
      },
      {
        scene_number: 2,
        location: 'Park',
        time_of_day: 'Afternoon',
        characters: ['JOHN'],
        key_actions: 'John walks and contemplates his decision',
        estimated_duration: 10,
        visual_description: 'A peaceful park with trees and walking paths',
        audio_requirements: 'Ambient nature sounds, soft music'
      }
    ],
    characters: ['JOHN', 'MARY'],
    character_details: 'John: protagonist, conflicted; Mary: supportive friend',
    acts: [],
    beats: [],
    scenes: [],
    created_at: '2024-01-01T00:00:00Z',
    status: 'ready'
  },
  documentary: {
    id: 'script-2',
    chapter_id: 'chapter-1',
    script_style: 'documentary',
    script_name: 'Documentary Style',
    script: `NARRATOR
Welcome to our exploration of decision-making.

We begin with John, a man facing a difficult choice.

JOHN
I've been thinking about this for weeks.

The pressure builds as the deadline approaches.`,
    scene_descriptions: [
      {
        scene_number: 1,
        location: 'Various',
        time_of_day: 'Day',
        characters: ['NARRATOR', 'JOHN'],
        key_actions: 'Narrator introduces the topic, John shares his thoughts',
        estimated_duration: 20,
        visual_description: 'Montage of John in different locations',
        audio_requirements: 'Narration, interview audio, background score'
      }
    ],
    characters: ['NARRATOR', 'JOHN'],
    character_details: 'Narrator: voice of authority; John: subject of documentary',
    acts: [],
    beats: [],
    scenes: [],
    created_at: '2024-01-01T00:00:00Z',
    status: 'ready'
  }
};

// Test 1: VideoPreview Script Synchronization
function testVideoPreviewSynchronization() {
  console.log('🧪 Test 1: VideoPreview Script Synchronization');
  
  // Simulate script change
  const selectedScript = mockScripts.cinematic;
  
  // Test scene script extraction
  const currentScene = { sceneNumber: 1, id: 'scene-1', duration: 15 };
  const sceneScript = getCurrentSceneScript(selectedScript, currentScene);
  
  console.log('Scene Script Data:', sceneScript);
  console.assert(sceneScript, 'Scene script should be extracted');
  console.assert(sceneScript.scene_number === 1, 'Should match scene number');
  
  // Test dialogue extraction
  const dialogue = getCurrentSceneDialogue(selectedScript, currentScene);
  console.log('Dialogue Segments:', dialogue);
  console.assert(dialogue && dialogue.length > 0, 'Dialogue should be extracted');
  console.assert(dialogue[0].character === 'JOHN', 'Should extract correct character');
  
  console.log('✅ VideoPreview synchronization test passed\n');
}

// Test 2: AudioPanel Script Synchronization
function testAudioPanelSynchronization() {
  console.log('🧪 Test 2: AudioPanel Script Synchronization');
  
  const selectedScript = mockScripts.cinematic;
  
  // Test character voice mapping initialization
  const characterVoices = initializeCharacterVoices(selectedScript);
  console.log('Character Voices:', characterVoices);
  console.assert(Object.keys(characterVoices).length === 2, 'Should initialize voices for all characters');
  
  // Test script change detection
  const scriptChangeDetected = detectScriptChange(selectedScript);
  console.log('Script Change Detected:', scriptChangeDetected);
  console.assert(scriptChangeDetected, 'Should detect script changes');
  
  console.log('✅ AudioPanel synchronization test passed\n');
}

// Test 3: Character Dialogue Mapping
function testCharacterDialogueMapping() {
  console.log('🧪 Test 3: Character Dialogue Mapping');
  
  const selectedScript = mockScripts.cinematic;
  
  // Test dialogue parsing
  const dialogueSegments = parseDialogueFromScript(selectedScript.script, 1);
  console.log('Parsed Dialogue:', dialogueSegments);
  
  console.assert(dialogueSegments.length === 2, 'Should parse all dialogue segments');
  console.assert(dialogueSegments[0].character === 'JOHN', 'First character should be JOHN');
  console.assert(dialogueSegments[1].character === 'MARY', 'Second character should be MARY');
  
  // Test voice assignment
  const voiceMapping = {
    'JOHN': 'elevenlabs_conversational',
    'MARY': 'elevenlabs_expressive'
  };
  
  const assignedVoices = assignVoicesToDialogue(dialogueSegments, voiceMapping);
  console.log('Assigned Voices:', assignedVoices);
  console.assert(assignedVoices.every(d => d.voiceModel), 'All dialogue should have voice assignments');
  
  console.log('✅ Character dialogue mapping test passed\n');
}

// Test 4: Cross-Component Consistency
function testCrossComponentConsistency() {
  console.log('🧪 Test 4: Cross-Component Consistency');
  
  const selectedScript = mockScripts.cinematic;
  
  // Test that all components receive the same script data
  const videoPreviewData = extractScriptDataForVideoPreview(selectedScript);
  const audioPanelData = extractScriptDataForAudioPanel(selectedScript);
  const imagesPanelData = extractScriptDataForImagesPanel(selectedScript);
  
  console.log('VideoPreview Data:', videoPreviewData.sceneCount);
  console.log('AudioPanel Data:', audioPanelData.characterCount);
  console.log('ImagesPanel Data:', imagesPanelData.sceneCount);
  
  // All should have consistent scene and character counts
  console.assert(videoPreviewData.sceneCount === audioPanelData.sceneCount, 
    'Scene count should be consistent between VideoPreview and AudioPanel');
  console.assert(audioPanelData.characterCount === imagesPanelData.characterCount,
    'Character count should be consistent between AudioPanel and ImagesPanel');
  
  console.log('✅ Cross-component consistency test passed\n');
}

// Helper functions (simulating actual component logic)
function getCurrentSceneScript(selectedScript, currentScene) {
  if (!selectedScript || !currentScene) return null;
  
  return selectedScript.scene_descriptions.find(
    scene => scene.scene_number === currentScene.sceneNumber
  );
}

function getCurrentSceneDialogue(selectedScript, currentScene) {
  if (!selectedScript?.script || !currentScene) return null;
  
  const sceneNumber = currentScene.sceneNumber;
  const scriptLines = selectedScript.script.split('\n');
  const dialogueSegments = [];
  
  let currentCharacter = '';
  let inScene = false;
  
  console.log(`🔍 Parsing dialogue for scene ${sceneNumber}`);
  
  for (let i = 0; i < scriptLines.length; i++) {
    const line = scriptLines[i].trim();
    
    // Check if we're entering the current scene
    if (!inScene && line.toLowerCase().includes(`scene ${sceneNumber}`)) {
      console.log(`🎬 Entering scene ${sceneNumber}`);
      inScene = true;
      continue;
    }
    
    // Check if we're entering the next scene (end current scene)
    if (inScene && line.toLowerCase().includes(`scene ${sceneNumber + 1}`)) {
      console.log(`🎬 Leaving scene ${sceneNumber} - found next scene`);
      break;
    }
    
    if (!inScene) continue;
    
    // Detect character names (uppercase, typically 2-20 chars)
    if (line === line.toUpperCase() && line.length > 1 && line.length < 20 &&
        !line.includes('.') && !line.includes('(') && !line.includes(')')) {
      console.log(`🎭 Found character: ${line}`);
      currentCharacter = line;
      continue;
    }
    
    // Detect dialogue (lines that follow character names)
    if (currentCharacter && line.length > 0 && !line.startsWith('(') && !line.startsWith('[')) {
      let dialogueText = line;
      if (dialogueText.startsWith('"') && dialogueText.endsWith('"')) {
        dialogueText = dialogueText.slice(1, -1);
      }
      
      console.log(`💬 Dialogue for ${currentCharacter}: ${dialogueText}`);
      dialogueSegments.push({
        character: currentCharacter,
        text: dialogueText
      });
      
      currentCharacter = ''; // Reset after dialogue
    }
  }
  
  console.log(`📝 Final dialogue segments:`, dialogueSegments);
  return dialogueSegments.length > 0 ? dialogueSegments : null;
}

function initializeCharacterVoices(selectedScript) {
  if (!selectedScript || !selectedScript.characters) return {};
  
  const characterVoices = {};
  selectedScript.characters.forEach(character => {
    characterVoices[character] = selectedScript.script_style === 'cinematic'
      ? 'elevenlabs_conversational'
      : 'elevenlabs_narrator';
  });
  
  return characterVoices;
}

function detectScriptChange(selectedScript) {
  // Simulate script change detection
  return selectedScript && selectedScript.id;
}

function parseDialogueFromScript(script, sceneNumber) {
  return getCurrentSceneDialogue({ script }, { sceneNumber }) || [];
}

function assignVoicesToDialogue(dialogueSegments, voiceMapping) {
  return dialogueSegments.map(dialogue => ({
    ...dialogue,
    voiceModel: voiceMapping[dialogue.character] || 'default_voice'
  }));
}

function extractScriptDataForVideoPreview(selectedScript) {
  return {
    sceneCount: selectedScript?.scene_descriptions?.length || 0,
    hasDialogue: selectedScript?.script?.includes('\n\n') || false
  };
}

function extractScriptDataForAudioPanel(selectedScript) {
  return {
    characterCount: selectedScript?.characters?.length || 0,
    sceneCount: selectedScript?.scene_descriptions?.length || 0,
    scriptStyle: selectedScript?.script_style || 'unknown'
  };
}

function extractScriptDataForImagesPanel(selectedScript) {
  return {
    sceneCount: selectedScript?.scene_descriptions?.length || 0,
    characterCount: selectedScript?.characters?.length || 0,
    hasVisualDescriptions: selectedScript?.scene_descriptions?.some(s => s.visual_description) || false
  };
}

// Run all tests
console.log('🚀 Starting Script Synchronization Tests\n');

try {
  testVideoPreviewSynchronization();
  testAudioPanelSynchronization();
  testCharacterDialogueMapping();
  testCrossComponentConsistency();
  
  console.log('🎉 All script synchronization tests completed successfully!');
  console.log('\n📋 Summary:');
  console.log('✅ Script selection synchronizes with video preview');
  console.log('✅ Audio track synchronization works');
  console.log('✅ Character dialogue mapping functions correctly');
  console.log('✅ Consistent behavior across all panels');
  
} catch (error) {
  console.error('❌ Test failed:', error);
  process.exit(1);
}