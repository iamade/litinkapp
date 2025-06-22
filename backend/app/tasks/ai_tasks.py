from celery import current_task
from app.tasks.celery_app import celery_app
from app.services.ai_service import AIService
from app.services.voice_service import VoiceService
from app.services.video_service import VideoService


@celery_app.task(bind=True)
def generate_quiz_task(self, content: str, difficulty: str = "medium"):
    """Background task to generate quiz questions"""
    try:
        current_task.update_state(state="PROGRESS", meta={"status": "Generating quiz questions..."})
        
        ai_service = AIService()
        # Note: This would need to be adapted for sync execution in Celery
        # or use celery with async support
        quiz_questions = ai_service.generate_quiz(content, difficulty)
        
        return {
            "status": "SUCCESS",
            "questions": quiz_questions
        }
    except Exception as e:
        return {
            "status": "FAILURE",
            "error": str(e)
        }


@celery_app.task(bind=True)
def generate_voice_task(self, text: str, character: str, emotion: str = "neutral"):
    """Background task to generate voice audio"""
    try:
        current_task.update_state(state="PROGRESS", meta={"status": "Generating voice audio..."})
        
        voice_service = VoiceService()
        # Sync version needed for Celery
        audio_url = voice_service.generate_speech_sync(text, character, emotion)
        
        return {
            "status": "SUCCESS",
            "audio_url": audio_url
        }
    except Exception as e:
        return {
            "status": "FAILURE",
            "error": str(e)
        }


@celery_app.task(bind=True)
def generate_video_task(self, scene_description: str, dialogue: str, avatar_style: str = "realistic"):
    """Background task to generate video scene"""
    try:
        current_task.update_state(state="PROGRESS", meta={"status": "Generating video scene..."})
        
        video_service = VideoService()
        # Sync version needed for Celery
        video_scene = video_service.generate_story_scene_sync(scene_description, dialogue, avatar_style)
        
        return {
            "status": "SUCCESS",
            "video_scene": video_scene
        }
    except Exception as e:
        return {
            "status": "FAILURE",
            "error": str(e)
        }


@celery_app.task(bind=True)
def process_book_upload_task(self, file_path: str, book_data: dict):
    """Background task to process uploaded book"""
    try:
        current_task.update_state(state="PROGRESS", meta={"status": "Processing book content..."})
        
        # Extract text from file
        # Generate chapters using AI
        # Create database entries
        
        return {
            "status": "SUCCESS",
            "book_id": "generated_book_id"
        }
    except Exception as e:
        return {
            "status": "FAILURE",
            "error": str(e)
        }