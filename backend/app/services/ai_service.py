import openai
from typing import List, Dict, Any, Optional
import json
import asyncio
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY


class AIService:
    """AI service for generating educational content"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
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
    
    async def generate_chapters_from_content(self, content: str, book_type: str) -> List[Dict[str, Any]]:
        """Generate chapters from book content without hardcoding chapter count"""
        if not self.client:
            return self._get_mock_chapters(book_type)

        try:
            prompt = f"""
    You are an expert at analyzing and structuring {book_type} books.

    Your task is to:
    - Break the input content into logical, well-structured **chapters**
    - Use **natural topic boundaries**, not arbitrary text lengths
    - Avoid over-segmenting (don’t create chapters that are too short or redundant)
    - Only create a new chapter when there is a clear shift in theme or subject
    - Return all output in **valid JSON** format like this:

    {{
    "chapters": [
        {{
        "title": "Chapter title",
        "content": "Chapter content",
        "summary": "Brief summary",
        "duration": 15,
        "ai_content": {{
            "key_concepts": ["Concept 1", "Concept 2"],
            "learning_objectives": ["Objective 1", "Objective 2"]
        }}
        }}
    ]
    }}

    Here is the book content sample:
    {content[:7000]}
    """

            response = await self.client.chat.completions.create(
                model="gpt-4",  # Strongly recommended for structured output
                messages=[
                    {"role": "system", "content": f"You are an expert at structuring {book_type} books."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=4000
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("chapters", [])

        except Exception as e:
            print(f"AI service error: {e}")
            return self._get_mock_chapters(book_type)

    
    async def generate_chapter_content(self, content: str, book_type: str, difficulty: str) -> Dict[str, Any]:
        """Generate AI content for a chapter"""
        if book_type == "learning":
            return {
                "quiz_questions": await self.generate_quiz(content, difficulty),
                "key_concepts": await self._extract_key_concepts(content),
                "learning_objectives": await self._generate_learning_objectives(content)
            }
        else:  # entertainment
            return {
                "story_branches": await self._generate_story_branches(content),
                "character_profiles": await self._generate_character_profiles(content),
                "scene_descriptions": await self._generate_scene_descriptions(content)
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
    
    async def _generate_scene_descriptions(self, content: str) -> List[str]:
        """Generate scene descriptions"""
        return ["Scene 1: A mystical forest...", "Scene 2: An ancient castle..."]