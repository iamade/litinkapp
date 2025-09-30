import re
from typing import Dict, List, Tuple, Any
import json

class ScriptParser:
    def __init__(self):
        pass

    def parse_script_for_audio(self, script: str, characters: List[str], scene_descriptions: List[str], script_style: str = "cinematic_movie") -> Dict[str, Any]:
        """Parse script to extract different audio components based on style"""
        
        print(f"[SCRIPT PARSER DEBUG] Input:")
        print(f"- Script length: {len(script)} characters")
        print(f"- Characters provided: {characters}")
        print(f"- Script style: {script_style}")
        print(f"- Script sample (first 300 chars): {script[:300]}")
        
        # ✅ FIX: Clean the characters list - remove malformed entries
        cleaned_characters = []
        invalid_keywords = [
            'HOGWARTS EXPRESS', 'FADE OUT', 'FADE IN', 'CUT TO', 'INT.', 'EXT.',
            'SCENE', 'CUPBOARD', 'BEDROOM', 'NIGHT', 'MORNING', 'DAY', 'LATER',
            'CONTINUOUS', 'MOMENTS LATER', 'MEANWHILE', 'ELSEWHERE'
        ]
        
        for char in characters:
            if char and len(char.strip()) > 0 and len(char.strip()) < 30:  # Reasonable character name length
                # Skip entries that look like scene headers or malformed
                if not any(keyword in char.upper() for keyword in invalid_keywords):
                    # Only keep if it looks like a proper character name
                    if char.strip().replace(' ', '').isalpha():  # Only letters and spaces
                        cleaned_characters.append(char.strip())
        
        print(f"[SCRIPT PARSER DEBUG] Cleaned characters: {cleaned_characters}")
        
        # Handle cinematic movie style differently
        if script_style == "cinematic_movie":
            return self._parse_cinematic_movie_script(script, cleaned_characters, scene_descriptions)
        else:
            return self._parse_narration_script(script, cleaned_characters, scene_descriptions) 
        
      
    def _generate_sound_effects(self, scene_descriptions: List) -> List[Dict[str, Any]]:
        """Generate sound effects based on scene descriptions, prioritizing audio_requirements from DeepSeek"""

        sound_effects = []

        for i, scene in enumerate(scene_descriptions):
            try:
                # ✅ Handle both object and string formats
                if isinstance(scene, dict):
                    scene_number = scene.get('scene_number', i + 1)
                    audio_requirements = scene.get('audio_requirements', '').strip()

                    if audio_requirements:
                        # 🎯 Use DeepSeek-provided audio requirements
                        print(f"[SFX PARSER] Scene {scene_number}: Using DeepSeek audio_requirements: '{audio_requirements}'")

                        # Parse the audio_requirements string for sound effects
                        effects_found = self._parse_audio_requirements_for_sfx(audio_requirements, scene_number)
                        if effects_found:
                            sound_effects.extend(effects_found)
                        else:
                            # Fallback if parsing fails
                            sound_effects.append({
                                "scene": scene_number,
                                "description": audio_requirements,
                                "duration": 10.0
                            })
                    else:
                        # Fallback to keyword-based generation from visual content
                        scene_text = scene.get('visual_description', '') or scene.get('key_actions', '') or str(scene)
                        effects_found = self._generate_sfx_from_keywords(scene_text, scene_number)
                        sound_effects.extend(effects_found)

                elif isinstance(scene, str):
                    # Legacy string format - use keyword analysis
                    scene_number = i + 1
                    effects_found = self._generate_sfx_from_keywords(scene, scene_number)
                    sound_effects.extend(effects_found)
                else:
                    # Fallback for unexpected types
                    scene_text = str(scene)
                    scene_number = i + 1
                    effects_found = self._generate_sfx_from_keywords(scene_text, scene_number)
                    sound_effects.extend(effects_found)

            except Exception as e:
                print(f"[SFX PARSER] Error processing scene {i}: {e}")
                sound_effects.append({
                    "scene": i + 1,
                    "description": "ambient room tone",
                    "duration": 10.0
                })

        return sound_effects

    def _parse_audio_requirements_for_sfx(self, audio_requirements: str, scene_number: int) -> List[Dict[str, Any]]:
        """Parse DeepSeek audio_requirements string for sound effects"""
        effects = []

        # Split by common delimiters
        requirements = audio_requirements.replace(';', ',').replace(' and ', ',').replace(' or ', ',')
        items = [item.strip() for item in requirements.split(',') if item.strip()]

        for item in items:
            item_lower = item.lower()

            # Skip dialogue and music mentions
            if any(skip_word in item_lower for skip_word in ['dialogue', 'music', 'narration', 'voice']):
                continue

            # Extract duration if mentioned
            duration = 10.0  # default
            if 'second' in item_lower:
                # Try to extract number before 'second'
                import re
                duration_match = re.search(r'(\d+)\s*second', item_lower)
                if duration_match:
                    duration = float(duration_match.group(1))

            effects.append({
                "scene": scene_number,
                "description": item.strip(),
                "duration": duration
            })

        return effects

    def _generate_sfx_from_keywords(self, scene_text: str, scene_number: int) -> List[Dict[str, Any]]:
        """Fallback: Generate sound effects from keyword analysis of scene text"""
        scene_lower = scene_text.lower()
        effects_found = []

        # Map keywords to sound effects
        effect_mapping = {
            "door": "door opening/closing",
            "footsteps": "footsteps",
            "wind": "wind blowing",
            "rain": "rain falling",
            "fire": "crackling fire",
            "water": "water flowing",
            "crowd": "crowd murmur",
            "explosion": "explosion",
            "thunder": "thunder",
            "car": "car engine",
            "phone": "phone ringing",
            "clock": "clock ticking",
            "owl": "owl hooting",
            "magic": "magical sound effects",
            "wand": "magic wand sounds"
        }

        for keyword, effect in effect_mapping.items():
            if keyword in scene_lower:
                effects_found.append({
                    "scene": scene_number,
                    "description": effect,
                    "duration": 5.0
                })

        # Add at least one ambient effect per scene if none found
        if not effects_found:
            effects_found.append({
                "scene": scene_number,
                "description": "ambient room tone",
                "duration": 10.0
            })

        return effects_found
    
    # Update your existing _parse_cinematic_movie_script method:
    def _parse_cinematic_movie_script(self, script: str, characters: List[str], scene_descriptions: List) -> Dict[str, Any]:
        """Parse cinematic movie script with character dialogues"""
        
        # ✅ Debug scene_descriptions format
        print(f"[SCRIPT PARSER] Scene descriptions type: {type(scene_descriptions)}")
        if scene_descriptions:
            print(f"[SCRIPT PARSER] First scene type: {type(scene_descriptions[0])}")
            if isinstance(scene_descriptions[0], dict):
                print(f"[SCRIPT PARSER] First scene keys: {list(scene_descriptions[0].keys())}")
        
        audio_components = {
            "narrator_segments": [],
            "character_dialogues": [],
            "sound_effects": [],
            "background_music": []
        }
        
        lines = script.split('\n')
        current_scene = 0
        current_character = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Detect scene changes
            if line.startswith('SCENE') or line.startswith('INT.') or line.startswith('EXT.'):
                current_scene += 1
                current_character = None  # Reset character context on scene change
                
                # Extract environmental sounds from scene description
                scene_sounds = self._extract_scene_sounds(line)
                if scene_sounds:
                    audio_components["sound_effects"].extend(scene_sounds)
                continue
            
            # Check if line is a character name (ALL CAPS at start of line, no colon)
            if (line.isupper() and ':' not in line and 
                not line.startswith('SFX:') and not line.startswith('MUSIC:') and
                not line.startswith(('SCENE', 'INT.', 'EXT.', 'FADE', 'CUT TO'))):
                
                # Verify it's a known character
                if any(char.upper() == line for char in characters):
                    current_character = line
                    continue
            
            # Check for dialogue using existing method first
            character_match = self._detect_character_dialogue(line, characters)
            if character_match:
                character_name, dialogue = character_match
                audio_components["character_dialogues"].append({
                    "character": character_name,
                    "text": dialogue,
                    "scene": current_scene,
                    "line_number": i + 1
                })
                current_character = None  # Reset after dialogue
                continue
            
            # Check for dialogue following character name (cinematic format)
            if current_character and (line.startswith('"') or line.startswith("'") or 
                                    (not line.startswith('(') and len(line.split()) > 1)):
                dialogue = line.strip('"').strip("'")
                audio_components["character_dialogues"].append({
                    "character": current_character,
                    "text": dialogue,
                    "scene": current_scene,
                    "line_number": i + 1
                })
                current_character = None  # Reset after dialogue
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
                continue
            
            # Check for explicit sound/music cues
            if line.startswith('SFX:') or 'SOUND:' in line.upper():
                effect = line.replace('SFX:', '').replace('SOUND:', '').strip()
                audio_components["sound_effects"].append({
                    "description": effect,
                    "scene": current_scene,
                    "line_number": i + 1
                })
                continue
                
            if line.startswith('MUSIC:') or 'BACKGROUND MUSIC:' in line.upper():
                music = line.replace('MUSIC:', '').replace('BACKGROUND MUSIC:', '').strip()
                audio_components["background_music"].append({
                    "description": music,
                    "scene": current_scene,
                    "line_number": i + 1
                })
                continue
            
            # Everything else is narration (if not character dialogue context)
            if not current_character and self._is_narrator_text(line, characters):
                audio_components["narrator_segments"].append({
                    "text": line,
                    "scene": current_scene,
                    "line_number": i + 1
                })
        
        # ✅ Add scene-based background music if none specified (with scene format handling)
        if not audio_components["background_music"]:
            audio_components["background_music"] = self._generate_background_music_cues(scene_descriptions)
        
        # ✅ Add generated sound effects from scene descriptions (NEW METHOD)
        generated_sound_effects = self._generate_sound_effects(scene_descriptions)
        audio_components["sound_effects"].extend(generated_sound_effects)
        
        # Add default sound effects if none found at all
        if not audio_components["sound_effects"]:
            audio_components["sound_effects"] = [{
                "description": "ambient background sounds",
                "scene": 1,
                "line_number": 0
            }]
        
        return audio_components
              
    def _parse_cinematic_movie_script(self, script: str, characters: List[str], scene_descriptions: List[str]) -> Dict[str, Any]:
            """Parse cinematic movie script with character dialogues"""
            
            # ✅ Debug scene_descriptions format
            print(f"[SCRIPT PARSER] Scene descriptions type: {type(scene_descriptions)}")
            if scene_descriptions:
                print(f"[SCRIPT PARSER] First scene type: {type(scene_descriptions[0])}")
                if isinstance(scene_descriptions[0], dict):
                    print(f"[SCRIPT PARSER] First scene keys: {list(scene_descriptions[0].keys())}")
    
            
            audio_components = {
                "narrator_segments": [],
                "character_dialogues": [],
                "sound_effects": [],
                "background_music": []
            }
            
            lines = script.split('\n')
            current_scene = 0
            current_character = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                    
                # Detect scene changes
                if line.startswith('SCENE') or line.startswith('INT.') or line.startswith('EXT.'):
                    current_scene += 1
                    current_character = None  # Reset character context on scene change
                    
                    # Extract environmental sounds from scene description
                    scene_sounds = self._extract_scene_sounds(line)
                    if scene_sounds:
                        audio_components["sound_effects"].extend(scene_sounds)
                    continue
                
                # Check if line is a character name (ALL CAPS at start of line, no colon)
                if (line.isupper() and ':' not in line and 
                    not line.startswith('SFX:') and not line.startswith('MUSIC:') and
                    not line.startswith(('SCENE', 'INT.', 'EXT.', 'FADE', 'CUT TO'))):
                    
                    # Verify it's a known character
                    if any(char.upper() == line for char in characters):
                        current_character = line
                        continue
                
                # Check for dialogue using existing method first
                character_match = self._detect_character_dialogue(line, characters)
                if character_match:
                    character_name, dialogue = character_match
                    audio_components["character_dialogues"].append({
                        "character": character_name,
                        "text": dialogue,
                        "scene": current_scene,
                        "line_number": i + 1
                    })
                    current_character = None  # Reset after dialogue
                    continue
                
                # Check for dialogue following character name (cinematic format)
                if current_character and (line.startswith('"') or line.startswith("'") or 
                                        (not line.startswith('(') and len(line.split()) > 1)):
                    dialogue = line.strip('"').strip("'")
                    audio_components["character_dialogues"].append({
                        "character": current_character,
                        "text": dialogue,
                        "scene": current_scene,
                        "line_number": i + 1
                    })
                    current_character = None  # Reset after dialogue
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
                    continue
                
                # Check for explicit sound/music cues
                if line.startswith('SFX:') or 'SOUND:' in line.upper():
                    effect = line.replace('SFX:', '').replace('SOUND:', '').strip()
                    audio_components["sound_effects"].append({
                        "description": effect,
                        "scene": current_scene,
                        "line_number": i + 1
                    })
                    continue
                    
                if line.startswith('MUSIC:') or 'BACKGROUND MUSIC:' in line.upper():
                    music = line.replace('MUSIC:', '').replace('BACKGROUND MUSIC:', '').strip()
                    audio_components["background_music"].append({
                        "description": music,
                        "scene": current_scene,
                        "line_number": i + 1
                    })
                    continue
                
                # Everything else is narration (if not character dialogue context)
                if not current_character and self._is_narrator_text(line, characters):
                    audio_components["narrator_segments"].append({
                        "text": line,
                        "scene": current_scene,
                        "line_number": i + 1
                    })
            
            # Add scene-based background music if none specified
            if not audio_components["background_music"]:
                audio_components["background_music"] = self._generate_background_music_cues(scene_descriptions)
            
            # Add default sound effects if none found
            if not audio_components["sound_effects"]:
                audio_components["sound_effects"] = [{
                    "description": "crickets, owl hoots, night ambiance",
                    "scene": 1,
                    "line_number": 0
                }]
            
            return audio_components
        
    def _parse_narration_script(self, script: str, characters: List[str], scene_descriptions: List[str]) -> Dict[str, Any]:
            """Parse regular narration script (existing logic)"""
            
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
    
      
    def _generate_background_music_cues(self, scene_descriptions: List) -> List[Dict[str, Any]]:
        """Generate background music cues based on scene descriptions, prioritizing audio_requirements from DeepSeek"""

        music_cues = []

        for i, scene in enumerate(scene_descriptions):
            try:
                # ✅ Handle both object and string formats
                if isinstance(scene, dict):
                    scene_number = scene.get('scene_number', i + 1)
                    scene_location = scene.get('location', f'Scene {scene_number}')
                    audio_requirements = scene.get('audio_requirements', '').strip()

                    if audio_requirements:
                        # 🎯 Use DeepSeek-provided audio requirements
                        print(f"[MUSIC PARSER] Scene {scene_number}: Using DeepSeek audio_requirements for music: '{audio_requirements}'")

                        # Parse the audio_requirements string for music cues
                        music_cue = self._parse_audio_requirements_for_music(audio_requirements, scene_number, scene_location)
                        if music_cue:
                            music_cues.append(music_cue)
                        else:
                            # Fallback if parsing fails
                            music_cues.append({
                                "scene": scene_number,
                                "description": f"Background music: {audio_requirements}",
                                "type": "ambient",
                                "duration": 30.0
                            })
                    else:
                        # Fallback to keyword-based generation from visual content
                        scene_text = scene.get('visual_description', '') or scene.get('key_actions', '') or str(scene)
                        music_cue = self._generate_music_from_keywords(scene_text, scene_number, scene_location)
                        music_cues.append(music_cue)

                elif isinstance(scene, str):
                    # Legacy string format - use keyword analysis
                    scene_number = i + 1
                    scene_location = f'Scene {scene_number}'
                    music_cue = self._generate_music_from_keywords(scene, scene_number, scene_location)
                    music_cues.append(music_cue)
                else:
                    # Fallback for unexpected types
                    scene_text = str(scene)
                    scene_number = i + 1
                    scene_location = f'Scene {scene_number}'
                    music_cue = self._generate_music_from_keywords(scene_text, scene_number, scene_location)
                    music_cues.append(music_cue)

            except Exception as e:
                print(f"[MUSIC PARSER] Error processing scene {i}: {e}")
                # Fallback music cue
                music_cues.append({
                    "scene": i + 1,
                    "description": f"Ambient background music for Scene {i + 1}",
                    "type": "ambient",
                    "duration": 30.0
                })

        return music_cues

    def _parse_audio_requirements_for_music(self, audio_requirements: str, scene_number: int, scene_location: str) -> Dict[str, Any] | None:
        """Parse DeepSeek audio_requirements string for music cues"""
        requirements_lower = audio_requirements.lower()

        # Look for music-related keywords
        if any(music_word in requirements_lower for music_word in ['music', 'score', 'theme', 'melody', 'orchestral']):
            # Extract the music description
            music_description = audio_requirements.strip()
            if music_description.startswith('music:'):
                music_description = music_description[6:].strip()

            # Determine music type from description
            music_type = "ambient"
            if any(word in requirements_lower for word in ["battle", "fight", "action", "chase", "war", "intense", "epic"]):
                music_type = "intense"
            elif any(word in requirements_lower for word in ["romantic", "love", "tender", "gentle"]):
                music_type = "romantic"
            elif any(word in requirements_lower for word in ["sad", "death", "cry", "mourn", "tragic", "melancholic"]):
                music_type = "melancholic"
            elif any(word in requirements_lower for word in ["celebration", "party", "joy", "happy", "victory", "uplifting"]):
                music_type = "uplifting"
            elif any(word in requirements_lower for word in ["mystery", "dark", "horror", "scary", "suspense", "mysterious"]):
                music_type = "mysterious"

            return {
                "scene": scene_number,
                "description": music_description,
                "type": music_type,
                "duration": 30.0
            }

        return None

    def _generate_music_from_keywords(self, scene_text: str, scene_number: int, scene_location: str) -> Dict[str, Any]:
        """Fallback: Generate music cues from keyword analysis of scene text"""
        scene_lower = scene_text.lower()

        # Determine music type based on scene content
        music_type = "ambient"
        if any(word in scene_lower for word in ["battle", "fight", "action", "chase", "war"]):
            music_type = "intense"
        elif any(word in scene_lower for word in ["romantic", "love", "tender", "gentle"]):
            music_type = "romantic"
        elif any(word in scene_lower for word in ["sad", "death", "cry", "mourn", "tragic"]):
            music_type = "melancholic"
        elif any(word in scene_lower for word in ["celebration", "party", "joy", "happy", "victory"]):
            music_type = "uplifting"
        elif any(word in scene_lower for word in ["mystery", "dark", "horror", "scary", "suspense"]):
            music_type = "mysterious"

        # Create music description
        music_description = f"{music_type.capitalize()} background music for {scene_location}"

        return {
            "scene": scene_number,
            "description": music_description,
            "type": music_type,
            "duration": 30.0
        }

    # def _generate_background_music_cues(self, scene_descriptions: List[str]) -> List[Dict[str, Any]]:
    #     """Generate background music cues based on scene descriptions"""
    #     music_cues = []
        
    #     for i, scene in enumerate(scene_descriptions):
    #         scene_lower = scene.lower()
            
    #         # Determine music mood based on scene content
    #         if any(word in scene_lower for word in ['battle', 'fight', 'war', 'action']):
    #             music_type = "epic battle music, orchestral"
    #         elif any(word in scene_lower for word in ['sad', 'death', 'tragic', 'sorrow']):
    #             music_type = "melancholic music, slow piano"
    #         elif any(word in scene_lower for word in ['happy', 'celebration', 'joy', 'party']):
    #             music_type = "uplifting music, cheerful melody"
    #         elif any(word in scene_lower for word in ['mysterious', 'dark', 'secret', 'hidden']):
    #             music_type = "mysterious ambient music, suspenseful"
    #         elif any(word in scene_lower for word in ['romance', 'love', 'kiss', 'romantic']):
    #             music_type = "romantic music, soft strings"
    #         else:
    #             music_type = "cinematic background music, orchestral"
            
    #         music_cues.append({
    #             "scene": i + 1,
    #             "description": music_type,
    #             "type": "background_music"
    #         })
        
    #     return music_cues

    def estimate_audio_duration(self, text: str, words_per_minute: int = 150) -> float:
        """Estimate audio duration based on text length"""
        words = len(text.split())
        duration_minutes = words / words_per_minute
        return duration_minutes * 60  # Return seconds