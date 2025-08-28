import openai
from typing import List, Dict, Any, Optional
import json
import asyncio
import re  
import os
from app.core.config import settings
from openai import AsyncOpenAI
from app.services.text_utils import TextSanitizer, TokenCounter, TextChunker, create_safe_openai_messages


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
{content}
--- CONTENT END ---

Ensure the entire output is a single valid JSON object.
"""

            # Use the new safe message creation utility
            try:
                messages, total_tokens = create_safe_openai_messages(
                    system_prompt=system_prompt,
                    user_content=user_prompt,
                    max_tokens=16385,  # gpt-3.5-turbo limit
                    reserved_tokens=2000  # Reserve tokens for response
                )
                
                print(f"[AIService] Token count: {total_tokens}")
                print(f"[AIService] Messages created successfully")
                
            except ValueError as e:
                print(f"[AIService] Error creating safe messages: {e}")
                # Fallback to truncation
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt[:12000] + "\n\n[Content truncated due to length limits]"}
                ]

            # Add timeout to prevent hanging
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo-1106",  # Optimized for JSON mode
                    messages=messages,
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

    async def generate_chapter_ai_elements(self, content: str, book_type: str, difficulty: str) -> Dict[str, Any]:
        """Generate structured AI elements for a chapter (quizzes, key concepts, etc.), but not video scripts."""
        if book_type == "learning":
            return {
                "quiz_questions": await self.generate_quiz(content, difficulty),
                "key_concepts": await self._extract_key_concepts(content),
                "learning_objectives": await self._generate_learning_objectives(content)
            }
        else:  # entertainment
            # This is now separated from video script/scene generation.
            # Return placeholders or other relevant entertainment-focused elements.
            return {
                "story_branches": ["A mysterious figure appears.", "A hidden passage is discovered."],
                "character_profiles": ["Main character: brave and curious."]
            }
    
    async def generate_summary(self, content: str) -> str:
        """Generate content summary"""
        if not self.client:
            return "This is a mock summary of the content."
        
        try:
            # Sanitize and limit content
            sanitized_content = TextSanitizer.sanitize_for_openai(content)
            
            # Create safe messages
            messages, total_tokens = create_safe_openai_messages(
                system_prompt="Summarize the following content concisely.",
                user_content=sanitized_content,
                max_tokens=16385,
                reserved_tokens=500  # Reserve tokens for response
            )
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
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
            # Sanitize content
            sanitized_content = TextSanitizer.sanitize_for_openai(content)
            
            prompt = f"""
You are given the full text of {chapter_title} from the book '{book_title}' by {author}.
Write a concise, clear summary of this chapter, focusing only on its main ideas and key points.
Do not repeat content from other chapters.
Do not include content from the introduction, preface, or appendices.
Return only the summary text, not JSON.

--- CHAPTER CONTENT START ---
{sanitized_content}
--- CHAPTER CONTENT END ---
"""
            
            # Create safe messages
            messages, total_tokens = create_safe_openai_messages(
                system_prompt="You are an expert editor and summarizer.",
                user_content=prompt,
                max_tokens=16385,
                reserved_tokens=1000  # Reserve tokens for response
            )
            
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo-1106",
                    messages=messages,
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

    async def generate_text_from_prompt(self, prompt: str) -> str:
        """Generate text from a custom prompt"""
        if not self.client:
            return f"Mock response for: {prompt[:100]}..."
        
        try:
            # Sanitize prompt
            sanitized_prompt = TextSanitizer.sanitize_for_openai(prompt)
            
            # Create safe messages
            messages, total_tokens = create_safe_openai_messages(
                system_prompt="You are a helpful AI assistant that generates high-quality content based on user prompts.",
                user_content=sanitized_prompt,
                max_tokens=16385,
                reserved_tokens=2000  # Reserve tokens for response
            )
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI service error in generate_text_from_prompt: {e}")
            return f"Error generating content: {str(e)}"

    async def generate_tutorial_script(self, prompt: str) -> str:
        """Generate tutorial script for learning content"""
        if not self.client:
            return f"Mock tutorial script for: {prompt[:100]}..."
        
        try:
            # Sanitize prompt
            sanitized_prompt = TextSanitizer.sanitize_for_openai(prompt)
            
            # Create safe messages
            messages, total_tokens = create_safe_openai_messages(
                system_prompt="You are an expert educator and content creator. Create engaging, clear tutorial scripts that are perfect for audio narration or video presentation. Focus on making complex topics accessible and engaging.",
                user_content=sanitized_prompt,
                max_tokens=16385,
                reserved_tokens=2000  # Reserve tokens for response
            )
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI service error in generate_tutorial_script: {e}")
            return f"Error generating tutorial script: {str(e)}"

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
        
        # Construct the prompt using the total_context from RAG
        prompt = f"""
Given the following book and chapter context, generate a list of detailed scene descriptions for a video adaptation. Each scene should be a concise, vivid description suitable for a video generator like Tavus.

Book: {book['title']}
Chapter: {chapter['title']}
Content: {chapter_context['total_context']}

Format:

Scene 1: ...
Scene 2: ...
...
Return only the list of scene descriptions.
"""
        # Log the RAG context and AI prompt
        print("[RAG DEBUG] Enhanced Context for Scene Descriptions:")
        print(chapter_context['total_context'])
        print("[RAG DEBUG] AI Prompt for Scene Descriptions:")
        print(prompt)
        # Directly call OpenAI with the constructed prompt
        response_text = await self.generate_text_from_prompt(prompt)

        # Parse the response text into a list of scenes
        if response_text:
            # Assuming scenes are line-separated, e.g., "- Scene 1: ..."
            scenes = [line.strip('- ').strip() for line in response_text.split('\n') if line.strip()]
            return scenes
        return []
    
     # In ai_service.py (if you have one) or wherever extract_real_chapters_from_list is defined
    async def extract_real_chapters_from_list(self, prompt: str) -> Dict[str, Any]:
        """Extract real chapters using the provided prompt with book content"""
        try:
            if not self.client:
                raise Exception("OpenAI client is not initialized.")
            
            response = await self.client.chat.completions.create(
                model="gpt-4",  # or whatever model you're using
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing book structure."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # Parse the response
            text = response.choices[0].message.content
            
            # Extract chapter numbers
            chapters_match = re.search(r'CHAPTERS:\s*\[(.*?)\]', text, re.IGNORECASE)
            if chapters_match:
                chapters_str = chapters_match.group(1)
                chapters = [int(x.strip()) for x in chapters_str.split(',') if x.strip().isdigit()]
            else:
                chapters = []
            
            # Extract total
            total_match = re.search(r'TOTAL:\s*(\d+)', text, re.IGNORECASE)
            total = int(total_match.group(1)) if total_match else len(chapters)
            
            # Extract reason
            reason_match = re.search(r'REASON:\s*(.+)', text, re.IGNORECASE)
            reason = reason_match.group(1).strip() if reason_match else "Analysis based on book content"
            
            return {
                'chapters': chapters,
                'total_chapters': total,
                'reasoning': reason
            }
            
        except Exception as e:
            print(f"[AI SERVICE] Error: {e}")
            raise
    