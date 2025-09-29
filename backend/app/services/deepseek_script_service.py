from typing import Dict, Any, Optional, List
import asyncio
from openai import AsyncOpenAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class DeepSeekScriptService:
    """DeepSeek API service for script generation using OpenAI-compatible interface"""
    
    def __init__(self):
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is required")
            
        self.client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL
        )
        self.model = settings.DEEPSEEK_MODEL
        self.reasoner_model = settings.DEEPSEEK_REASONER_MODEL
        
        # ✅ Your specific system prompt
        self.screenplay_system_prompt = """You are a professional screenwriter. Convert the provided content into a cinematic screenplay format with:
    - Proper scene headings (INT./EXT. LOCATION - TIME)
    - Character names in uppercase when introduced and before dialogue
    - Dialogue centered on the page
    - Parentheticals for actor directions
    - Action descriptions in present tense
    - Appropriate screenplay formatting and spacing"""
    
    async def generate_screenplay(
        self,
        content: str,
        target_duration: Optional[int] = None,
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate a cinematic screenplay from content using your specific prompt"""
        
        try:
            # Choose model based on complexity
            model = self.reasoner_model if use_reasoning else self.model
            
            # Create user prompt with content
            user_prompt = self._create_screenplay_user_prompt(content, target_duration)
            
            logger.info(f"[DEEPSEEK] Generating screenplay with {model}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self.screenplay_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                stream=False
            )
            
            screenplay_content = response.choices[0].message.content
            
            # Parse the screenplay into structured format
            parsed_screenplay = self._parse_screenplay(screenplay_content)
            
            return {
                "status": "success",
                "screenplay": screenplay_content,
                "parsed_data": parsed_screenplay,
                "model_used": model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "metadata": {
                    "target_duration": target_duration,
                    "reasoning_enabled": use_reasoning
                }
            }
            
        except Exception as e:
            logger.error(f"[DEEPSEEK ERROR] Screenplay generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "screenplay": None,
                "parsed_data": None
            }
    
    async def generate_scene_breakdown(
        self,
        screenplay: str,
        max_scenes: int = 10
    ) -> Dict[str, Any]:
        """Break down screenplay into individual scenes for video production"""
        
        try:
            system_prompt = """You are a film production assistant. Break down the provided screenplay into individual scenes for video production.
            
            For each scene, provide:
            - Scene number
            - Location (INT./EXT. and setting)
            - Time of day
            - Characters present
            - Key actions/dialogue summary
            - Estimated duration in seconds
            - Visual description for image generation
            - Audio requirements (dialogue, sound effects, music)
            
            Return the response as a JSON array with scene objects."""
            
            user_prompt = f"""Break down this screenplay into {max_scenes} or fewer scenes:

{screenplay}

Provide detailed scene breakdown for video production pipeline."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=False
            )
            
            breakdown_content = response.choices[0].message.content
            
            # Try to parse JSON response
            import json
            try:
                # Clean up the response and extract JSON
                clean_content = self._extract_json_from_response(breakdown_content)
                breakdown_data = json.loads(clean_content)
            except Exception as json_error:
                logger.warning(f"[DEEPSEEK] JSON parsing failed: {json_error}")
                # If JSON parsing fails, create structured data from text
                breakdown_data = self._parse_scene_breakdown_text(breakdown_content)
            
            return {
                "status": "success",
                "scene_breakdown": breakdown_data,
                "raw_content": breakdown_content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"[DEEPSEEK ERROR] Scene breakdown failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "scene_breakdown": None
            }
    
    async def generate_character_profiles(
        self,
        screenplay: str
    ) -> Dict[str, Any]:
        """Extract and create character profiles from screenplay for voice generation"""
        
        try:
            system_prompt = """You are a casting director and voice director. Analyze the screenplay and create detailed character profiles for voice generation.
            
            For each speaking character, provide:
            - Character name (exactly as it appears in screenplay)
            - Age range
            - Gender
            - Personality traits
            - Voice characteristics (pitch, tone, accent, speaking style)
            - Emotional range in the story
            - Key dialogue examples
            
            Return as a JSON object with 'characters' array."""
            
            user_prompt = f"""Analyze this screenplay and create character profiles for voice generation:

{screenplay}

Focus on all speaking characters and their voice requirements."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                max_tokens=1500,
                stream=False
            )
            
            profiles_content = response.choices[0].message.content
            
            # Parse character profiles
            import json
            try:
                clean_content = self._extract_json_from_response(profiles_content)
                profiles_data = json.loads(clean_content)
            except Exception as json_error:
                logger.warning(f"[DEEPSEEK] JSON parsing failed: {json_error}")
                profiles_data = self._parse_character_profiles_text(profiles_content)
            
            return {
                "status": "success",
                "character_profiles": profiles_data,
                "raw_content": profiles_content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"[DEEPSEEK ERROR] Character profiles failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "character_profiles": None
            }
    
    async def extract_dialogue_segments(
        self,
        screenplay: str
    ) -> Dict[str, Any]:
        """Extract dialogue segments for audio generation"""
        
        try:
            system_prompt = """You are a dialogue editor. Extract all dialogue segments from the screenplay for audio generation.
            
            For each dialogue segment, provide:
            - Character name
            - Dialogue text (clean, without formatting)
            - Scene number/context
            - Emotional tone
            - Duration estimate in seconds
            
            Return as JSON with 'dialogue_segments' array."""
            
            user_prompt = f"""Extract all dialogue segments from this screenplay:

{screenplay}

Provide clean dialogue text ready for text-to-speech generation."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000,
                stream=False
            )
            
            dialogue_content = response.choices[0].message.content
            
            # Parse dialogue segments
            import json
            try:
                clean_content = self._extract_json_from_response(dialogue_content)
                dialogue_data = json.loads(clean_content)
            except Exception as json_error:
                logger.warning(f"[DEEPSEEK] JSON parsing failed: {json_error}")
                dialogue_data = self._parse_dialogue_from_text(dialogue_content)
            
            return {
                "status": "success",
                "dialogue_segments": dialogue_data,
                "raw_content": dialogue_content,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }
            
        except Exception as e:
            logger.error(f"[DEEPSEEK ERROR] Dialogue extraction failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "dialogue_segments": None
            }
    
    def _create_screenplay_user_prompt(self, content: str, target_duration: Optional[int]) -> str:
        """Create user prompt with content and requirements"""
        
        duration_note = f"\n\nTarget duration: {target_duration} minutes (aim for about 1 page per minute)" if target_duration else ""
        
        return f"""Convert this content into a cinematic screenplay:

{content}{duration_note}

Make it engaging, visual, and suitable for video production. Include detailed scene descriptions that will help with image generation and clear dialogue for voice generation."""
    
    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from response that might have additional text"""
        
        # Look for JSON blocks
        import re
        
        # Try to find JSON between ```json and ``` or just { }
        json_pattern = r'```json\s*(.*?)\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try to find JSON between { and }
        brace_pattern = r'(\{.*\})'
        match = re.search(brace_pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Try to find JSON between [ and ]
        bracket_pattern = r'(\[.*\])'
        match = re.search(bracket_pattern, content, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return content.strip()

    def _parse_screenplay(self, screenplay_content: str) -> Dict[str, Any]:
        """Parse screenplay into structured data"""
        
        lines = screenplay_content.split('\n')
        scenes = []
        characters = set()
        current_scene = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Scene headings
            if line.startswith(('INT.', 'EXT.', 'FADE IN:', 'FADE OUT:')):
                if current_scene:
                    # Convert set to list before appending
                    current_scene['characters'] = list(current_scene['characters'])
                    scenes.append(current_scene)
                current_scene = {
                    'heading': line,
                    'dialogue': [],
                    'actions': [],
                    'characters': set()
                }
            
            # Character dialogue (uppercase names)
            elif line.isupper() and len(line.split()) <= 3 and current_scene and not line.startswith(('INT.', 'EXT.')):
                # This is likely a character name
                characters.add(line)
                current_scene['characters'].add(line)
                current_scene['dialogue'].append({'type': 'character', 'name': line})
            
            # Action or dialogue
            elif current_scene:
                if line.startswith('(') and line.endswith(')'):
                    # Parenthetical
                    current_scene['dialogue'].append({'type': 'parenthetical', 'text': line})
                else:
                    # Regular dialogue or action
                    if current_scene['dialogue'] and current_scene['dialogue'][-1].get('type') == 'character':
                        # This is dialogue following a character name
                        current_scene['dialogue'].append({'type': 'dialogue', 'text': line})
                    else:
                        # This is action
                        current_scene['actions'].append(line)
        
        # Add final scene
        if current_scene:
            current_scene['characters'] = list(current_scene['characters'])
            scenes.append(current_scene)
        
        return {
            'scenes': scenes,
            'characters': list(characters),
            'scene_count': len(scenes),
            'character_count': len(characters)
        }
    
    def _parse_scene_breakdown_text(self, content: str) -> Dict[str, Any]:
        """Parse scene breakdown from text if JSON parsing fails"""
        
        scenes = []
        lines = content.split('\n')
        current_scene = {}
        scene_number = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.lower().startswith(('scene', 'int.', 'ext.')):
                if current_scene:
                    scenes.append(current_scene)
                current_scene = {
                    'scene_number': scene_number,
                    'heading': line,
                    'description': '',
                    'duration': 30  # default duration
                }
                scene_number += 1
            elif current_scene:
                current_scene['description'] += ' ' + line
        
        if current_scene:
            scenes.append(current_scene)
        
        return {'scenes': scenes}
    
    def _parse_character_profiles_text(self, content: str) -> Dict[str, Any]:
        """Parse character profiles from text if JSON parsing fails"""
        
        characters = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    characters.append({
                        'name': parts[0].strip(),
                        'description': parts[1].strip(),
                        'voice_characteristics': 'neutral adult voice'
                    })
        
        return {'characters': characters}
    
    def _parse_dialogue_from_text(self, content: str) -> Dict[str, Any]:
        """Parse dialogue segments from text if JSON parsing fails"""
        
        dialogue_segments = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    dialogue_segments.append({
                        'character': parts[0].strip(),
                        'text': parts[1].strip(),
                        'scene': i + 1,
                        'duration': len(parts[1].strip()) // 10  # rough estimate
                    })
        
        return {'dialogue_segments': dialogue_segments}
    
    
        # Add this method to the DeepSeekScriptService class
    
    async def generate_narration_script(
        self,
        content: str,
        target_duration: Optional[int] = None,
        use_reasoning: bool = False
    ) -> Dict[str, Any]:
        """Generate a narration-style script from content"""
        
        try:
            # Choose model based on complexity
            model = self.reasoner_model if use_reasoning else self.model
            
            # ✅ Different system prompt for narration style
            narration_system_prompt = """You are a professional narrator and storyteller. Convert the provided content into a cinematic narration script with:
    - Rich, descriptive narration that tells the story
    - Vivid scene descriptions and visual storytelling
    - Engaging narrative voice suitable for voice-over
    - Present tense action descriptions
    - Emotional and atmospheric descriptions
    - Clear transitions between scenes and moments
    - Descriptive language that paints pictures with words"""
            
            # Create user prompt for narration
            user_prompt = self._create_narration_user_prompt(content, target_duration)
            
            logger.info(f"[DEEPSEEK] Generating narration script with {model}")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": narration_system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000,
                stream=False
            )
            
            narration_content = response.choices[0].message.content
            
            # Parse the narration script (different parsing for narration)
            parsed_narration = self._parse_narration_script(narration_content)
            
            return {
                "status": "success",
                "screenplay": narration_content,
                "parsed_data": parsed_narration,
                "model_used": model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "metadata": {
                    "target_duration": target_duration,
                    "reasoning_enabled": use_reasoning,
                    "script_type": "narration"
                }
            }
            
        except Exception as e:
            logger.error(f"[DEEPSEEK ERROR] Narration script generation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "screenplay": None,
                "parsed_data": None
            }
    
    def _create_narration_user_prompt(self, content: str, target_duration: Optional[int]) -> str:
        """Create user prompt for narration script"""
        
        duration_note = f"\n\nTarget duration: {target_duration} minutes of narration" if target_duration else ""
        
        return f"""Convert this content into a cinematic narration script:
    
    {content}{duration_note}
    
    Create an engaging narration that:
    - Tells the story through descriptive voice-over
    - Includes vivid scene descriptions for visual understanding
    - Uses rich, atmospheric language
    - Maintains narrative flow and pacing
    - Is suitable for a narrator to read aloud over visuals
    
    Focus on storytelling through narration rather than character dialogue."""
    
    def _parse_narration_script(self, narration_content: str) -> Dict[str, Any]:
        """Parse narration script into structured data (different from screenplay parsing)"""
        
        lines = narration_content.split('\n')
        scenes = []
        narrative_segments = []
        current_scene = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for scene indicators or new paragraphs as scene breaks
            if (line.startswith(('Scene', 'SCENE', 'Chapter', 'CHAPTER')) or
                len(line) > 100):  # Long descriptive paragraphs
                
                if current_scene:
                    scenes.append(current_scene)
                
                current_scene = {
                    'heading': line[:50] + "..." if len(line) > 50 else line,
                    'narration': [],
                    'descriptions': [],
                    'characters': set()
                }
            
            # Add content to current scene
            elif current_scene:
                # Check if line mentions character names (proper nouns)
                words = line.split()
                for word in words:
                    if word.istitle() and len(word) > 2:
                        current_scene['characters'].add(word)
                
                current_scene['narration'].append(line)
                narrative_segments.append(line)
        
        # Add final scene
        if current_scene:
            current_scene['characters'] = list(current_scene['characters'])
            scenes.append(current_scene)
        
        # Extract any character names mentioned in narration
        all_characters = set()
        for scene in scenes:
            all_characters.update(scene.get('characters', []))
        
        return {
            'scenes': scenes,
            'characters': list(all_characters),
            'narrative_segments': narrative_segments,
            'scene_count': len(scenes),
            'character_count': len(all_characters),
            'script_type': 'narration'
        }