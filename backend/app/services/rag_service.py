from typing import Dict, Any, List, Optional
from supabase import create_client
from app.core.database import get_supabase
from app.services.ai_service import AIService
from app.services.embeddings_service import EmbeddingsService


class RAGService:
    """Retrieval Augmented Generation service for video content with PlotDrive integration"""
    
    def __init__(self, supabase_client=None):
        self.db = supabase_client
        self.ai_service = AIService()
        self.embeddings_service = EmbeddingsService(supabase_client)
    
    async def get_chapter_with_context(
        self, 
        chapter_id: str, 
        include_adjacent: bool = True,
        use_vector_search: bool = True
    ) -> Dict[str, Any]:
        """Retrieve chapter with surrounding context for better video generation"""
        try:
            # Get the target chapter
            chapter_response = self.db.table('chapters').select('*').eq('id', chapter_id).single().execute()
            if not chapter_response.data:
                raise ValueError(f"Chapter {chapter_id} not found")
            
            chapter = chapter_response.data
            
            # Get book context
            book_response = self.db.table('books').select('*').eq('id', chapter['book_id']).single().execute()
            book = book_response.data
            
            context = {
                'chapter': chapter,
                'book': book,
                'adjacent_chapters': [],
                'similar_chunks': [],
                'total_context': chapter['content']
            }
            
            # Get adjacent chapters if requested
            if include_adjacent:
                adjacent_response = self.db.table('chapters').select('*').eq('book_id', chapter['book_id']).order('chapter_number').execute()
                all_chapters = adjacent_response.data
                
                # Find current chapter index
                current_index = next((i for i, c in enumerate(all_chapters) if c['id'] == chapter_id), -1)
                
                if current_index >= 0:
                    # Get previous and next chapters
                    prev_chapters = all_chapters[max(0, current_index - 2):current_index]
                    next_chapters = all_chapters[current_index + 1:min(len(all_chapters), current_index + 3)]
                    
                    context['adjacent_chapters'] = prev_chapters + next_chapters
                    
                    # Add adjacent chapter content to total context
                    adjacent_content = []
                    for adj_chapter in context['adjacent_chapters']:
                        adjacent_content.append(f"Chapter {adj_chapter['chapter_number']}: {adj_chapter['title']}\n{adj_chapter['content'][:1000]}")
                    
                    if adjacent_content:
                        context['total_context'] = "\n\n".join(adjacent_content) + "\n\n" + context['total_context']
            
            # Use vector search for similar content if enabled
            if use_vector_search:
                try:
                    similar_chunks = await self.embeddings_service.get_context_for_chapter(
                        chapter_id=chapter_id,
                        context_chunks=5
                    )
                    context['similar_chunks'] = similar_chunks
                    
                    # Add similar content to total context
                    if similar_chunks:
                        similar_content = []
                        for chunk in similar_chunks:
                            if chunk['chapter']['id'] != chapter_id:  # Don't include the current chapter
                                similar_content.append(f"Related content from Chapter {chunk['chapter']['chapter_number']}: {chunk['content_chunk']}")
                        
                        if similar_content:
                            context['total_context'] = context['total_context'] + "\n\nRelated content:\n" + "\n".join(similar_content)
                            
                except Exception as e:
                    print(f"Vector search failed, falling back to basic context: {e}")
            
            return context
            
        except Exception as e:
            print(f"Error getting chapter context: {e}")
            raise
    
    async def search_similar_content(self, query: str, book_id: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar content using vector embeddings"""
        try:
            return await self.embeddings_service.search_similar_chapters(
                query=query,
                book_id=book_id,
                limit=limit
            )
        except Exception as e:
            print(f"Error searching similar content: {e}")
            return []
    
    async def generate_video_script(
        self, 
        chapter_context: Dict[str, Any], 
        video_style: str = "realistic",
        script_style: str = "cinematic_movie"
    ) -> Dict[str, Any]:
        """Generate optimized video script from chapter context using the full RAG-enhanced prompt. script_style can be 'cinematic_movie' or 'cinematic_narration'."""
        try:
            enhanced_context = chapter_context.get('total_context', chapter_context['chapter']['content'])
            prompt = self._get_script_generation_prompt(enhanced_context, video_style, script_style)
            print(f"[RAG DEBUG] AI Prompt for Video Script:\n{prompt}\n")
            script = await self.ai_service.generate_text_from_prompt(prompt)
            
            # Extract characters from the generated script
            characters = self._extract_characters_from_script(script)
            
            # Generate character details for each character
            character_details = await self._generate_character_details(characters, enhanced_context)
            
            return {
                "script": script,
                "characters": characters,
                "character_details": character_details,
                "script_style": script_style,
                "video_style": video_style
            }
        except Exception as e:
            print(f"Error generating video script: {e}")
            return {
                "script": "",
                "characters": [],
                "character_details": "",
                "script_style": script_style,
                "video_style": video_style
            }
    
    def _get_script_generation_prompt(self, context: str, video_style: str, script_style: str = "cinematic_movie") -> str:
        """Construct a prompt based on the full RAG-enhanced context and script_style."""
        if script_style == "cinematic_movie":
            return f"""
Given the following book and chapter context, generate a detailed tutorial script for a {video_style} style video. 

The script should include:
1. Clear educational content delivery
2. Conversational teaching tone
3. Step-by-step explanations
4. Examples and demonstrations
5. Natural speech patterns and transitions
6. Engaging educational narrative
7. Focus on learning objectives

Use the context below:

{context}

Format the script as a tutorial with:
- Clear introduction of the topic
- Educational content delivery
- Examples and explanations
- Natural speech patterns
- Engaging teaching style

Return only the tutorial script.
"""
        else:  # cinematic_narration
            return f"""
Given the following book and chapter context, generate a detailed tutorial narration script for a {video_style} style video.

The script should include:
1. Engaging educational storytelling
2. Descriptive language that explains concepts
3. Clear learning objectives
4. Educational content delivery
5. Smooth transitions between topics
6. Multiple educational segments that build understanding
7. Rich, educational language suitable for voice-over

Use the context below:

{context}

Format the script as educational narration with:
- Clear topic introductions
- Concept explanations and descriptions
- Educational examples and demonstrations
- Smooth transitions between topics
- Engaging educational language

Return only the tutorial narration script.
"""
    
    def _extract_characters_from_script(self, script: str) -> List[str]:
        """Extract character names from the generated script"""
        try:
            # Look for character names in ALL CAPS (screenplay format)
            import re
            character_pattern = r'\b[A-Z][A-Z\s]+\b'
            potential_characters = re.findall(character_pattern, script)
            
            # Filter out common non-character words and clean up
            non_characters = {
                'SCENE', 'INT', 'EXT', 'DAY', 'NIGHT', 'MORNING', 'EVENING', 'CONTINUOUS', 
                'LATER', 'MOMENTS', 'LATER', 'FADE', 'CUT', 'DISSOLVE', 'THE', 'AND', 'OR',
                'BUT', 'FOR', 'WITH', 'FROM', 'THAT', 'THIS', 'THESE', 'THOSE', 'WHAT',
                'WHEN', 'WHERE', 'WHY', 'HOW', 'WHO', 'WHICH', 'WHOSE', 'WHOM'
            }
            
            characters = []
            for char in potential_characters:
                char_clean = char.strip()
                if (len(char_clean) > 2 and 
                    char_clean not in non_characters and 
                    not char_clean.isdigit() and
                    char_clean not in characters):
                    characters.append(char_clean)
            
            # If no characters found in CAPS, try to extract from dialogue
            if not characters:
                # Look for dialogue patterns and extract speaker names
                dialogue_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):\s*["\']'
                dialogue_characters = re.findall(dialogue_pattern, script)
                characters = list(set(dialogue_characters))
            
            return characters[:10]  # Limit to 10 characters
            
        except Exception as e:
            print(f"Error extracting characters: {e}")
            return []
    
    async def _generate_character_details(self, characters: List[str], context: str) -> str:
        """Generate detailed character descriptions for the extracted characters"""
        try:
            if not characters:
                return "Main character from the story"
            
            character_list = ", ".join(characters[:5])  # Limit to 5 characters for details
            
            prompt = f"""
Based on the following story context, provide brief character descriptions for: {character_list}

Context: {context[:2000]}

For each character, provide:
- Physical appearance
- Personality traits
- Role in the story
- Key characteristics

Format as a concise character guide suitable for video generation.
"""
            
            character_details = await self.ai_service.generate_text_from_prompt(prompt)
            return character_details
            
        except Exception as e:
            print(f"Error generating character details: {e}")
            return f"Characters: {', '.join(characters)}"
    
    async def _generate_entertainment_script(self, chapter_context: Dict[str, Any], video_style: str) -> str:
        """Generate entertainment script using OpenAI only (no PlotDrive)."""
        try:
            chapter = chapter_context['chapter']
            book = chapter_context['book']
            prompt = f"""
Create an engaging story script for a {video_style} style video based on this entertainment content:

Book: {book['title']}
Chapter: {chapter['title']}
Content: {chapter_context['total_context']}

The script should:
1. Be dramatic and engaging
2. Include character dialogue and actions
3. Be suitable for {video_style} video generation
4. Be 2-3 minutes in duration
5. Maintain the story's emotional impact

Format as a narrative script with clear scene descriptions and dialogue.
"""
            # Log the AI prompt
            print("[RAG DEBUG] AI Prompt for Entertainment Script:")
            print(prompt)
            response = await self.ai_service.generate_text_from_prompt(prompt)
            return str(response)
        except Exception as e:
            print(f"Error generating entertainment script: {e}")
            return chapter_context['chapter']['content']
    
    def _map_video_style_to_plotdrive(self, video_style: str) -> str:
        """Map video style to PlotDrive screenplay style"""
        style_mapping = {
            'realistic': 'realistic',
            'cinematic': 'cinematic',
            'animated': 'animated',
            'documentary': 'documentary',
            'dramatic': 'dramatic',
            'fantasy': 'fantasy',
            'sci-fi': 'sci-fi',
            'historical': 'historical',
            'modern': 'modern'
        }
        return style_mapping.get(video_style, 'realistic')
    
    async def get_video_metadata(
        self, 
        chapter_context: Dict[str, Any], 
        video_style: str = "realistic"
    ) -> Dict[str, Any]:
        """Generate metadata for video generation with PlotDrive enhancement"""
        try:
            chapter = chapter_context['chapter']
            book = chapter_context['book']
            
            metadata = {
                'title': f"{chapter['title']} - {book['title']}",
                'description': f"Video adaptation of chapter {chapter['chapter_number']} from {book['title']}",
                'book_type': book['book_type'],
                'video_style': video_style,
                'estimated_duration': 180,  # 3 minutes default
                'scene_count': 1,
                'character_count': 1,
                'enhancement_type': 'basic'
            }
            
            return metadata
            
        except Exception as e:
            print(f"Error generating video metadata: {e}")
            return {
                'title': f"Video - {chapter_context['chapter']['title']}",
                'description': "Video generation",
                'estimated_duration': 180
            }
    
    async def enhance_entertainment_content(self, chapter_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance entertainment content using PlotDrive service"""
        try:
            chapter = chapter_context['chapter']
            book = chapter_context['book']
            
            # Use PlotDrive service for enhancement
            enhancement = await self.plotdrive_service.enhance_entertainment_content(
                story_content=chapter_context['total_context'],
                title=chapter['title'],
                book_title=book['title']
            )
            
            return enhancement
            
        except Exception as e:
            print(f"Error enhancing entertainment content: {e}")
            return {
                'enhanced_content': chapter_context['total_context'],
                'enhancement_type': 'basic'
            }
    
    async def generate_screenplay_with_openai(self, chapter_id: str, style: str = "cinematic") -> str:
        """Generate a screenplay for entertainment using OpenAI (not PlotDrive)"""
        chapter_context = await self.get_chapter_with_context(chapter_id, include_adjacent=True)
        chapter = chapter_context['chapter']
        book = chapter_context['book']
        prompt = f"""
Create an engaging screenplay for a {style} style video based on this entertainment content:

Book: {book['title']}
Chapter: {chapter['title']}
Content: {chapter_context['total_context']}

The screenplay should:
1. Be dramatic and engaging
2. Include character dialogue and actions
3. Be suitable for {style} video generation
4. Be 2-3 minutes in duration
5. Maintain the story's emotional impact

Format as a narrative script with clear scene descriptions and dialogue.
"""
        response = await self.ai_service.generate_chapter_content(
            content=prompt,
            book_type='entertainment',
            difficulty='medium'
        )
        return str(response) 