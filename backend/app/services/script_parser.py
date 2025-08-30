import re
from typing import Dict, List, Tuple, Any
import json

class ScriptParser:
    def __init__(self):
        pass

    def parse_script_for_audio(self, script: str, characters: List[str], scene_descriptions: List[str]) -> Dict[str, Any]:
        """Parse script to extract different audio components"""
        
        audio_components = {
            "narrator_segments": [],
            "character_dialogues": [],
            "sound_effects": [],
            "background_music": []
        }
        
        # Split script into lines for processing
        lines = script.split('\n')
        current_scene = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Detect scene changes
            if line.startswith('SCENE') or line.startswith('INT.') or line.startswith('EXT.'):
                current_scene += 1
                
                # Extract environmental sounds from scene description
                scene_sounds = self._extract_scene_sounds(line)
                if scene_sounds:
                    audio_components["sound_effects"].extend(scene_sounds)
                continue
            
            # Detect character dialogue
            character_match = self._detect_character_dialogue(line, characters)
            if character_match:
                character_name, dialogue = character_match
                audio_components["character_dialogues"].append({
                    "character": character_name,
                    "text": dialogue,
                    "scene": current_scene,
                    "line_number": i + 1
                })
                continue
            
            # Detect narrator text (descriptive text that's not dialogue)
            if self._is_narrator_text(line, characters):
                audio_components["narrator_segments"].append({
                    "text": line,
                    "scene": current_scene,
                    "line_number": i + 1
                })
                continue
            
            # Detect sound effects in parentheses or brackets
            sound_effects = self._extract_sound_effects(line)
            if sound_effects:
                for effect in sound_effects:
                    audio_components["sound_effects"].append({
                        "description": effect,
                        "scene": current_scene,
                        "line_number": i + 1
                    })
        
        # Add scene-based background music
        audio_components["background_music"] = self._generate_background_music_cues(scene_descriptions)
        
        return audio_components

    def _detect_character_dialogue(self, line: str, characters: List[str]) -> Tuple[str, str] | None:
        """Detect if a line contains character dialogue"""
        
        # Pattern 1: CHARACTER: dialogue
        colon_pattern = r'^([A-Z][A-Z\s]+):\s*(.+)$'
        match = re.match(colon_pattern, line)
        if match:
            character_name = match.group(1).strip()
            dialogue = match.group(2).strip()
            
            # Check if it's a known character or close match
            if character_name in characters or any(char.upper() == character_name for char in characters):
                return (character_name, dialogue)
        
        # Pattern 2: "dialogue" - CHARACTER
        quote_pattern = r'^"(.+)"\s*-\s*([A-Z][A-Za-z\s]+)$'
        match = re.match(quote_pattern, line)
        if match:
            dialogue = match.group(1).strip()
            character_name = match.group(2).strip().upper()
            
            if character_name in [char.upper() for char in characters]:
                return (character_name, dialogue)
        
        return None

    def _is_narrator_text(self, line: str, characters: List[str]) -> bool:
        """Check if line is narrator text (not dialogue or stage directions)"""
        
        # Skip if it's character dialogue
        if self._detect_character_dialogue(line, characters):
            return False
        
        # Skip if it's scene headers
        if line.startswith(('SCENE', 'INT.', 'EXT.', 'FADE', 'CUT TO')):
            return False
            
        # Skip if it's stage directions (usually in parentheses)
        if line.startswith('(') and line.endswith(')'):
            return False
        
        # If it's descriptive text, it's likely narrator content
        if len(line.split()) > 3:  # At least 4 words
            return True
            
        return False

    def _extract_sound_effects(self, line: str) -> List[str]:
        """Extract sound effects from stage directions"""
        sound_effects = []
        
        # Pattern for sound effects in parentheses: (SOUND EFFECT)
        parentheses_pattern = r'\(([^)]+)\)'
        matches = re.findall(parentheses_pattern, line)
        
        for match in matches:
            if any(keyword in match.upper() for keyword in ['SOUND', 'NOISE', 'MUSIC', 'AUDIO', 'SFX']):
                sound_effects.append(match)
        
        # Pattern for sound effects in brackets: [SOUND EFFECT]
        bracket_pattern = r'\[([^\]]+)\]'
        matches = re.findall(bracket_pattern, line)
        
        for match in matches:
            if any(keyword in match.upper() for keyword in ['SOUND', 'NOISE', 'MUSIC', 'AUDIO', 'SFX']):
                sound_effects.append(match)
        
        return sound_effects

    def _extract_scene_sounds(self, scene_line: str) -> List[Dict[str, Any]]:
        """Extract environmental sounds from scene descriptions"""
        scene_sounds = []
        scene_lower = scene_line.lower()
        
        # Environmental sound mappings
        sound_mappings = {
            'forest': 'birds chirping, leaves rustling, wind through trees',
            'ocean': 'waves crashing, seagulls, ocean breeze',
            'city': 'traffic, car horns, urban ambiance',
            'night': 'crickets, owl hoots, night ambiance',
            'rain': 'rainfall, thunder, storm sounds',
            'fire': 'crackling fire, wood burning',
            'castle': 'medieval ambiance, stone echoes',
            'tavern': 'crowd chatter, clinking glasses',
            'battle': 'sword clashing, armor clanking, battle cries'
        }
        
        for environment, sounds in sound_mappings.items():
            if environment in scene_lower:
                scene_sounds.append({
                    "description": sounds,
                    "type": "environmental",
                    "environment": environment
                })
        
        return scene_sounds

    def _generate_background_music_cues(self, scene_descriptions: List[str]) -> List[Dict[str, Any]]:
        """Generate background music cues based on scene descriptions"""
        music_cues = []
        
        for i, scene in enumerate(scene_descriptions):
            scene_lower = scene.lower()
            
            # Determine music mood based on scene content
            if any(word in scene_lower for word in ['battle', 'fight', 'war', 'action']):
                music_type = "epic battle music, orchestral"
            elif any(word in scene_lower for word in ['sad', 'death', 'tragic', 'sorrow']):
                music_type = "melancholic music, slow piano"
            elif any(word in scene_lower for word in ['happy', 'celebration', 'joy', 'party']):
                music_type = "uplifting music, cheerful melody"
            elif any(word in scene_lower for word in ['mysterious', 'dark', 'secret', 'hidden']):
                music_type = "mysterious ambient music, suspenseful"
            elif any(word in scene_lower for word in ['romance', 'love', 'kiss', 'romantic']):
                music_type = "romantic music, soft strings"
            else:
                music_type = "cinematic background music, orchestral"
            
            music_cues.append({
                "scene": i + 1,
                "description": music_type,
                "type": "background_music"
            })
        
        return music_cues

    def estimate_audio_duration(self, text: str, words_per_minute: int = 150) -> float:
        """Estimate audio duration based on text length"""
        words = len(text.split())
        duration_minutes = words / words_per_minute
        return duration_minutes * 60  # Return seconds