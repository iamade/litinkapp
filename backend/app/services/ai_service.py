import openai
from typing import List, Dict, Any, Optional
import json
import asyncio
import os
from app.core.config import settings
from openai import AsyncOpenAI


class AIService:
    """AI service for generating educational content"""
    
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def generate_quiz(self, content: str, difficulty: str = "medium") -> List[Dict[str, Any]]:
        """Generate quiz questions from content"""
        if not self.client:
            return self._get_mock_quiz(difficulty)
        
        try:
            prompt = f"""
            Generate 5 {difficulty} level quiz questions based on this content:
            
            {content[:2000]}
            
            Return JSON format:
            {{
                "questions": [
                    {{
                        "id": "1",
                        "question": "Question text",
                        "options": ["Option A", "Option B", "Option C", "Option D"],
                        "correctAnswer": 0,
                        "explanation": "Explanation text",
                        "difficulty": "{difficulty}"
                    }}
                ]
            }}
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert educator creating quiz questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("questions", [])
            
        except Exception as e:
            print(f"AI service error: {e}")
            return self._get_mock_quiz(difficulty)
    
    async def generate_lesson(self, content: str, topic: str) -> Dict[str, Any]:
        """Generate lesson content"""
        if not self.client:
            return self._get_mock_lesson(topic)
        
        try:
            prompt = f"""
            Create an engaging lesson about "{topic}" based on this content:
            
            {content[:2000]}
            
            Return JSON format:
            {{
                "title": "Lesson title",
                "content": "Detailed lesson content",
                "keyPoints": ["Point 1", "Point 2", "Point 3"],
                "examples": ["Example 1", "Example 2"],
                "exercises": ["Exercise 1", "Exercise 2"]
            }}
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert educator creating lesson content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"AI service error: {e}")
            return self._get_mock_lesson(topic)
    
    async def generate_chapters_from_content(
        self, content: str, book_type: str
    ) -> List[Dict[str, Any]]:
        """Generate chapters from book content using a structured approach."""
        if not self.client:
            return self._get_mock_chapters(book_type)

        try:
            # System prompt to set the context for the AI
            system_prompt = f"""
You are an expert editor specializing in {book_type} content. 
Your task is to analyze the provided text and divide it into logical chapters. 
Focus on identifying natural breaks in the narrative or subject matter.

IMPORTANT GUIDELINES:
1. Create 1-3 chapters from the provided content
2. Each chapter should have a clear, descriptive title that reflects its content
3. Avoid generic titles like "Introduction" or "Overview" - be specific
4. Do NOT include page numbers, dots, or formatting artifacts in titles
5. Keep titles concise but descriptive (5-15 words)
6. Ensure each chapter has substantial content

Return the output as a valid JSON object with a single key "chapters" that contains a list of chapter objects.
Each chapter object must have 'title' and 'content' keys.
"""

            # User prompt with the actual content
            user_prompt = f"""
Please process the following content and structure it into chapters:

--- CONTENT START ---
{content[:15000]} 
--- CONTENT END ---

Ensure the entire output is a single valid JSON object.
"""

            # LOGGING: Print prompt and content length
            print("[AIService] System prompt:\n", system_prompt)
            print("[AIService] User prompt (first 500 chars):\n", user_prompt[:500])
            print(f"[AIService] Content length: {len(content)} characters (truncated to 15000)")

            # Add timeout to prevent hanging
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo-1106",  # Optimized for JSON mode
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                ),
                timeout=settings.AI_TIMEOUT_SECONDS  # Use configurable timeout
            )

            response_content = response.choices[0].message.content
            # LOGGING: Print raw AI response
            print("[AIService] Raw AI response:\n", response_content)
            if not response_content:
                raise ValueError("Received empty content from OpenAI API.")

            result = json.loads(response_content)
            
            # Basic validation
            if "chapters" not in result or not isinstance(result["chapters"], list):
                raise ValueError("Invalid JSON structure received from AI.")

            return result.get("chapters", [])

        except asyncio.TimeoutError:
            print("AI service request timed out after 30 seconds")
            return self._get_mock_chapters(book_type)
        except json.JSONDecodeError as e:
            print(f"AI service JSON decoding error: {e}")
            print(f"Invalid JSON received: {response_content}")
            return self._get_mock_chapters(book_type)
        except Exception as e:
            print(f"AI service error in generate_chapters_from_content: {e}")
            return self._get_mock_chapters(book_type)

    def generate_chapters_from_content_sync(
        self, content: str, book_type: str
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for generate_chapters_from_content."""
        return asyncio.run(self.generate_chapters_from_content(content, book_type))

    async def generate_chapter_content(self, content: str, book_type: str, difficulty: str, rag_service=None) -> Dict[str, Any]:
        """Generate AI content for a chapter"""
        if book_type == "learning":
            return {
                "quiz_questions": await self.generate_quiz(content, difficulty),
                "key_concepts": await self._extract_key_concepts(content),
                "learning_objectives": await self._generate_learning_objectives(content)
            }
        else:  # entertainment
            # If rag_service is provided and content is a chapter_id, use the new scene description logic
            if rag_service is not None and isinstance(content, str) and content.startswith("chapter_"):
                return {
                    "story_branches": await self._generate_story_branches(content),
                    "character_profiles": await self._generate_character_profiles(content),
                    "scene_descriptions": await self._generate_scene_descriptions(content, rag_service)
                }
            else:
                # Fallback to old logic (may still error if _generate_scene_descriptions signature is wrong)
                return {
                    "story_branches": await self._generate_story_branches(content),
                    "character_profiles": await self._generate_character_profiles(content),
                    "scene_descriptions": await self._generate_scene_descriptions(content, rag_service) if rag_service else await self._generate_scene_descriptions(content, self)
                }
    
    async def generate_summary(self, content: str) -> str:
        """Generate content summary"""
        if not self.client:
            return "This is a mock summary of the content."
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Summarize the following content concisely."},
                    {"role": "user", "content": content[:2000]}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI service error: {e}")
            return "Error generating summary."
    
    async def extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        if not self.client:
            return ["keyword1", "keyword2", "keyword3"]
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Extract 5-10 key terms from this content. Return as comma-separated list."},
                    {"role": "user", "content": content[:1000]}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            keywords = response.choices[0].message.content.split(", ")
            return [kw.strip() for kw in keywords]
            
        except Exception as e:
            print(f"AI service error: {e}")
            return ["error", "generating", "keywords"]
    
    async def assess_difficulty(self, content: str) -> str:
        """Assess content difficulty level"""
        if not self.client:
            return "medium"
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Assess the difficulty level of this content. Return only: easy, medium, or hard"},
                    {"role": "user", "content": content[:1000]}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            difficulty = response.choices[0].message.content.strip().lower()
            return difficulty if difficulty in ["easy", "medium", "hard"] else "medium"
            
        except Exception as e:
            print(f"AI service error: {e}")
            return "medium"
    
    # Helper methods for mock data
    def _get_mock_quiz(self, difficulty: str) -> List[Dict[str, Any]]:
        """Return mock quiz data"""
        return [
            {
                "id": "1",
                "question": f"What is the main concept in this {difficulty} level content?",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correctAnswer": 1,
                "explanation": "This is the correct answer because...",
                "difficulty": difficulty
            }
        ]
    
    def _get_mock_lesson(self, topic: str) -> Dict[str, Any]:
        """Return mock lesson data"""
        return {
            "title": f"Understanding {topic}",
            "content": f"This lesson covers the fundamentals of {topic}...",
            "keyPoints": [f"Key concept 1 about {topic}", f"Key concept 2 about {topic}"],
            "examples": [f"Example 1 for {topic}", f"Example 2 for {topic}"],
            "exercises": [f"Practice exercise 1", f"Practice exercise 2"]
        }
    
    def _get_mock_chapters(self, book_type: str) -> List[Dict[str, Any]]:
        """Return mock chapters data"""
        return [
            {
                "title": f"Introduction to {book_type.title()}",
                "content": f"This chapter introduces the basics of {book_type}...",
                "summary": f"Overview of {book_type} fundamentals",
                "duration": 15,
                "ai_content": {
                    "key_concepts": ["Concept 1", "Concept 2"],
                    "learning_objectives": ["Objective 1", "Objective 2"]
                }
            }
        ]
    
    async def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts from content"""
        # Simplified implementation
        return ["Key Concept 1", "Key Concept 2", "Key Concept 3"]
    
    async def _generate_learning_objectives(self, content: str) -> List[str]:
        """Generate learning objectives"""
        return ["Understand the main concepts", "Apply the knowledge", "Analyze the information"]
    
    async def _generate_story_branches(self, content: str) -> List[Dict[str, Any]]:
        """Generate story branches for entertainment content"""
        return [
            {
                "id": "branch1",
                "content": "Story branch 1 content...",
                "choices": [
                    {"text": "Choice 1", "next_branch": "branch2"},
                    {"text": "Choice 2", "next_branch": "branch3"}
                ]
            }
        ]
    
    async def _generate_character_profiles(self, content: str) -> List[Dict[str, Any]]:
        """Generate character profiles"""
        return [
            {
                "name": "Character 1",
                "description": "Character description...",
                "personality": "Brave and curious"
            }
        ]
    

    async def generate_book_metadata(
        self, content: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        # Implementation of generate_book_metadata method
        pass

    def generate_chapter_summary_sync(self, content: str, chapter_title: str, book_title: str, author: str) -> str:
        """Generate a focused summary for a single chapter using a custom prompt."""
        return asyncio.run(self._generate_chapter_summary(content, chapter_title, book_title, author))

    async def _generate_chapter_summary(self, content: str, chapter_title: str, book_title: str, author: str) -> str:
        if not self.client:
            return f"Summary for {chapter_title}"
        try:
            prompt = f"""
You are given the full text of {chapter_title} from the book '{book_title}' by {author}.
Write a concise, clear summary of this chapter, focusing only on its main ideas and key points.
Do not repeat content from other chapters.
Do not include content from the introduction, preface, or appendices.
Return only the summary text, not JSON.

--- CHAPTER CONTENT START ---
{content[:12000]}
--- CHAPTER CONTENT END ---
"""
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo-1106",
                    messages=[
                        {"role": "system", "content": "You are an expert editor and summarizer."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=600,
                ),
                timeout=settings.AI_TIMEOUT_SECONDS
            )
            summary = response.choices[0].message.content.strip()
            return summary
        except Exception as e:
            print(f"AIService error in generate_chapter_summary: {e}")
            return f"Summary for {chapter_title}"

    async def _generate_scene_descriptions(self, chapter_id: str, rag_service) -> List[str]:
        """Generate scene descriptions using OpenAI and RAGService context."""
        # Get chapter context using RAGService
        chapter_context = await rag_service.get_chapter_with_context(
            chapter_id=chapter_id,
            include_adjacent=True,
            use_vector_search=True
        )
        chapter = chapter_context['chapter']
        book = chapter_context['book']
        prompt = f"""
Given the following book and chapter context, generate a list of detailed scene descriptions for a video adaptation. Each scene should be a concise, vivid description suitable for a video generator like Tavus.

Book: {book['title']}
Chapter: {chapter['title']}
Content: {chapter_context['total_context']}

Format:
- Scene 1: ...
- Scene 2: ...
- ...

Return only the list of scene descriptions.
"""
        if not self.client:
            # Fallback for development/testing
            return ["Scene 1: A mystical forest...", "Scene 2: An ancient castle..."]
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates scene descriptions for video adaptation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=512
            )
            content = response.choices[0].message.content
            # Try to split by lines and clean up
            scenes = [line.strip('- ').strip() for line in content.split('\n') if line.strip()]
            return scenes
        except Exception as e:
            print(f"AIService error in _generate_scene_descriptions: {e}")
            return []