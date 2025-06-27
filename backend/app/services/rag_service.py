from typing import Dict, Any, List, Optional
from supabase import Client
from app.core.database import get_supabase
from app.services.ai_service import AIService
from app.services.plotdrive_service import PlotDriveService
from app.services.embeddings_service import EmbeddingsService


class RAGService:
    """Retrieval Augmented Generation service for video content with PlotDrive integration"""
    
    def __init__(self, supabase_client: Client):
        self.db = supabase_client
        self.ai_service = AIService()
        self.plotdrive_service = PlotDriveService()
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
        video_style: str = "realistic"
    ) -> str:
        """Generate optimized video script from chapter context using OpenAI only (no PlotDrive)."""
        try:
            chapter = chapter_context['chapter']
            book = chapter_context['book']
            
            # Build enhanced context with similar chunks
            enhanced_context = f"""
Book: {book['title']} by {book['author_name']}
Book Type: {book['book_type']}
Chapter: {chapter['title']}

Main Content:
{chapter['content']}

Total Context:
{chapter_context['total_context']}

Video Style: {video_style}
"""
            
            # Use different prompts based on book type
            if book['book_type'] == 'entertainment':
                prompt = f"""
Create a screenplay script for a {video_style} style video based on this entertainment content:

{enhanced_context}

The screenplay should:
1. Be dramatic and engaging
2. Include character dialogue and actions in proper screenplay format
3. Be suitable for {video_style} video generation
4. Be 2-3 minutes in duration
5. Maintain the story's emotional impact

Format as a proper screenplay with:
- Character names in ALL CAPS
- Dialogue indented under character names
- Scene descriptions and actions
- Clear character interactions

Example format:
NARRATOR
    Welcome to the world of angel magic...

SAGE
    The ancient art of summoning requires...

STUDENT
    How do I begin?

SAGE
    First, you must understand...
"""
            else:
                # For learning content, create a tutorial script
                prompt = f"""
Create a tutorial video script for a {video_style} style video based on this learning content:

{enhanced_context}

The script should:
1. Be educational and informative
2. Include clear explanations and examples
3. Be suitable for {video_style} video generation
4. Be 2-3 minutes in duration
5. Have a logical flow from introduction to conclusion

Format as a tutorial script with:
- INSTRUCTOR character for explanations
- Clear section breaks
- Examples and demonstrations
- Engaging delivery

Example format:
INSTRUCTOR
    Welcome to this tutorial on...

    Today we'll learn about...

    Let me show you how...

    Here's an example...

    Remember, the key points are...
"""
            
            response = await self.ai_service.generate_chapter_content(
                content=prompt,
                book_type=book['book_type'],
                difficulty=book.get('difficulty', 'medium')
            )
            return str(response)
        except Exception as e:
            print(f"Error generating video script: {e}")
            return chapter_context['chapter']['content']
    
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
            response = await self.ai_service.generate_chapter_content(
                content=prompt,
                book_type='entertainment',
                difficulty='medium'
            )
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
            
            # Add PlotDrive metadata for entertainment content
            if book['book_type'] == 'entertainment':
                try:
                    screenplay_result = await self.plotdrive_service.create_screenplay_script(
                        story_content=chapter_context['total_context'],
                        style=self._map_video_style_to_plotdrive(video_style),
                        title=chapter['title'],
                        book_title=book['title']
                    )
                    
                    if screenplay_result and 'metadata' in screenplay_result:
                        plotdrive_metadata = screenplay_result['metadata']
                        metadata.update({
                            'estimated_duration': plotdrive_metadata.get('estimated_duration', 180),
                            'scene_count': plotdrive_metadata.get('scene_count', 1),
                            'character_count': plotdrive_metadata.get('character_count', 1),
                            'enhancement_type': 'plotdrive_screenplay'
                        })
                        
                except Exception as e:
                    print(f"Error getting PlotDrive metadata: {e}")
            
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