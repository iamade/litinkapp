import httpx
from typing import Dict, Any, List, Optional
from app.services.ai_service import AIService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class PlotDriveService:
    """PlotDrive-style service for creating screenplay scripts from entertainment content"""
    
    def __init__(self):
        self.api_key = settings.PLOTDRIVE_API_KEY
        self.base_url = "https://api.plotdrive.com/v1"  # Example PlotDrive API URL
        self.use_external_api = bool(self.api_key)
    
    async def create_screenplay_script(
        self, 
        story_content: str, 
        style: str = "realistic",
        title: str = None,
        book_title: str = None
    ) -> Dict[str, Any]:
        """Generate screenplay using AI with PlotDrive-style prompts"""
        try:
            if self.use_external_api:
                return await self._call_plotdrive_api(story_content, style, title, book_title)
            else:
                return await self._generate_screenplay_ai(story_content, style, title, book_title)
        except Exception as e:
            logger.error(f"PlotDrive service error: {e}")
            return await self._generate_screenplay_ai(story_content, style, title, book_title)
    
    async def _call_plotdrive_api(
        self, 
        story_content: str, 
        style: str, 
        title: str, 
        book_title: str
    ) -> Dict[str, Any]:
        """Call actual PlotDrive API if available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/screenplay",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "story_content": story_content,
                        "style": style,
                        "title": title,
                        "book_title": book_title,
                        "output_format": "screenplay"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"PlotDrive API returned {response.status_code}, falling back to AI generation")
                    return await self._generate_screenplay_ai(story_content, style, title, book_title)
                    
        except Exception as e:
            logger.error(f"PlotDrive API call failed: {e}")
            return await self._generate_screenplay_ai(story_content, style, title, book_title)
    
    async def _generate_screenplay_ai(
        self, 
        story_content: str, 
        style: str, 
        title: str, 
        book_title: str
    ) -> Dict[str, Any]:
        """Generate screenplay using AI with PlotDrive-style formatting"""
        from app.services.ai_service import AIService
        
        ai_service = AIService()
        
        # Create PlotDrive-style prompt
        prompt = f"""
Create a professional screenplay script in PlotDrive format for this story content:

Book: {book_title}
Chapter: {title}
Style: {style}

Story Content:
{story_content[:3000]}

Generate a screenplay that includes:

1. SCENE HEADINGS (INT./EXT. - LOCATION - TIME)
2. ACTION DESCRIPTIONS (detailed visual descriptions)
3. CHARACTER NAMES (in CAPS)
4. DIALOGUE (properly formatted)
5. PARENTHETICALS (character actions/emotions)
6. TRANSITIONS (CUT TO:, FADE OUT:, etc.)

Style Guidelines for {style}:
- Use cinematic language and visual storytelling
- Include detailed scene descriptions
- Create engaging character dialogue
- Maintain story pacing and emotional beats
- Add visual cues and camera directions where appropriate

Format the screenplay in standard industry format with proper spacing and indentation.
Keep the script to 2-3 minutes in duration (approximately 2-3 pages).

Return the screenplay text only, no additional formatting or explanations.
"""
        
        try:
            script = await ai_service.generate_chapter_content(
                content=prompt,
                book_type="entertainment",
                difficulty="medium"
            )
            
            # Estimate metadata
            estimated_duration = self._estimate_duration(str(script))
            scene_count = str(script).count("SCENE") + str(script).count("INT.") + str(script).count("EXT.")
            character_count = len(set([line.strip() for line in str(script).split('\n') if line.strip().isupper() and len(line.strip()) > 2]))
            
            return {
                'script': str(script),
                'metadata': {
                    'estimated_duration': estimated_duration,
                    'scene_count': max(scene_count, 1),
                    'character_count': max(character_count, 1),
                    'style': style,
                    'format': 'screenplay'
                }
            }
            
        except Exception as e:
            logger.error(f"AI screenplay generation failed: {e}")
            return {
                'script': f"SCENE 1 - {title}\n\n{story_content[:500]}...",
                'metadata': {
                    'estimated_duration': 180,
                    'scene_count': 1,
                    'character_count': 1,
                    'style': style,
                    'format': 'basic'
                }
            }
    
    def _estimate_duration(self, script: str) -> int:
        """Estimate video duration from script (rough calculation)"""
        # Rough estimation: 150 words per minute for speech
        words = len(script.split())
        estimated_minutes = max(2, min(5, words // 150))  # Between 2-5 minutes
        return estimated_minutes * 60  # Return in seconds
    
    async def enhance_entertainment_content(
        self, 
        story_content: str, 
        title: str = None, 
        book_title: str = None
    ) -> Dict[str, Any]:
        """Enhance entertainment content using PlotDrive service"""
        try:
            if self.use_external_api:
                return await self._call_plotdrive_enhancement_api(story_content, title, book_title)
            else:
                return await self._enhance_content_ai(story_content, title, book_title)
        except Exception as e:
            logger.error(f"PlotDrive enhancement error: {e}")
            return await self._enhance_content_ai(story_content, title, book_title)
    
    async def _call_plotdrive_enhancement_api(
        self, 
        story_content: str, 
        title: str, 
        book_title: str
    ) -> Dict[str, Any]:
        """Call PlotDrive enhancement API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/enhance",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "story_content": story_content,
                        "title": title,
                        "book_title": book_title,
                        "enhancement_type": "story_development"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"PlotDrive enhancement API returned {response.status_code}")
                    return await self._enhance_content_ai(story_content, title, book_title)
                    
        except Exception as e:
            logger.error(f"PlotDrive enhancement API call failed: {e}")
            return await self._enhance_content_ai(story_content, title, book_title)
    
    async def _enhance_content_ai(
        self, 
        story_content: str, 
        title: str, 
        book_title: str
    ) -> Dict[str, Any]:
        """Enhance content using AI with PlotDrive-style analysis"""
        from app.services.ai_service import AIService
        
        ai_service = AIService()
        
        prompt = f"""
Enhance this entertainment content using PlotDrive-style story development techniques:

Book: {book_title}
Chapter: {title}

Original Content:
{story_content[:2000]}

Enhance the content by:

1. Adding character development and motivations
2. Enhancing scene descriptions and atmosphere
3. Improving dialogue and character interactions
4. Adding dramatic tension and emotional beats
5. Creating visual storytelling elements
6. Developing plot structure and pacing

Focus on making the content more cinematic and engaging for video adaptation.
Maintain the original story while adding depth and visual appeal.

Return the enhanced content with clear scene breaks and character development.
"""
        
        try:
            enhanced_content = await ai_service.generate_chapter_content(
                content=prompt,
                book_type="entertainment",
                difficulty="medium"
            )
            
            return {
                'enhanced_content': str(enhanced_content),
                'enhancement_type': 'plotdrive_story_development',
                'original_length': len(story_content),
                'enhanced_length': len(str(enhanced_content))
            }
            
        except Exception as e:
            logger.error(f"AI content enhancement failed: {e}")
            return {
                'enhanced_content': story_content,
                'enhancement_type': 'basic',
                'original_length': len(story_content),
                'enhanced_length': len(story_content)
            } 