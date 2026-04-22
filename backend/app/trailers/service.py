"""
Trailer Scene Selection Service — KAN-149

AI-powered scene selection for trailer generation.
Analyzes chapters/artifacts and scores scenes for trailer suitability.

Scoring dimensions:
- Action Score: Movement intensity, conflict, excitement
- Emotional Score: Impact, resonance, character moments
- Visual Score: Cinematic potential, imagery quality
- Narrative Score: Plot importance, story arc contribution
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import logging
import json
import asyncio

from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trailers.models import (
    TrailerGeneration,
    TrailerScene,
    TrailerStatus,
    SelectionMethod,
)
from app.trailers.schemas import (
    TrailerAnalyzeRequest,
    TrailerConfig,
    SceneScore,
    SceneAnalysisResult,
)
from app.core.services.openrouter import OpenRouterService
from app.core.model_config import get_model_config

logger = logging.getLogger(__name__)


# Scoring weights for different trailer tones
TONE_WEIGHTS = {
    "epic": {"action": 0.35, "emotional": 0.20, "visual": 0.25, "narrative": 0.20},
    "dramatic": {"action": 0.15, "emotional": 0.40, "visual": 0.20, "narrative": 0.25},
    "action": {"action": 0.45, "emotional": 0.15, "visual": 0.25, "narrative": 0.15},
    "romantic": {"action": 0.10, "emotional": 0.45, "visual": 0.25, "narrative": 0.20},
    "mysterious": {"action": 0.20, "emotional": 0.25, "visual": 0.30, "narrative": 0.25},
    "default": {"action": 0.30, "emotional": 0.25, "visual": 0.25, "narrative": 0.20},
}


class TrailerSceneService:
    """KAN-149: AI Scene Selection Service
    
    Analyzes project content to identify highlight scenes for trailer inclusion.
    Uses LLM-based analysis to score scenes across multiple dimensions.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ai_service = OpenRouterService()
    
    async def analyze_project_for_trailer(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        config: TrailerAnalyzeRequest,
    ) -> TrailerGeneration:
        """Main entry point: Analyze a project and select scenes for trailer.
        
        Returns a TrailerGeneration record with selected scenes.
        """
        logger.info(f"[KAN-149] Starting trailer analysis for project {project_id}")
        
        # 1. Create trailer generation record
        trailer_gen = TrailerGeneration(
            project_id=project_id,
            user_id=user_id,
            target_duration_seconds=config.target_duration_seconds,
            tone=config.tone,
            style=config.style,
            status=TrailerStatus.ANALYZING,
            selection_method=SelectionMethod.AI_AUTO,
        )
        self.session.add(trailer_gen)
        await self.session.commit()
        await self.session.refresh(trailer_gen)
        
        try:
            # 2. Get project chapters
            chapters = await self._get_project_chapters(project_id)
            trailer_gen.total_scenes_analyzed = len(chapters)
            await self.session.commit()
            
            # 3. Analyze each chapter for highlight scenes
            all_scenes: List[TrailerScene] = []
            weights = TONE_WEIGHTS.get(config.tone, TONE_WEIGHTS["default"])
            
            # Apply preference overrides if specified
            if config.prefer_action:
                weights = {"action": 0.45, "emotional": 0.15, "visual": 0.25, "narrative": 0.15}
            elif config.prefer_dialogue:
                weights = {"action": 0.15, "emotional": 0.35, "visual": 0.20, "narrative": 0.30}
            elif config.prefer_emotional:
                weights = {"action": 0.15, "emotional": 0.45, "visual": 0.20, "narrative": 0.20}
            
            for chapter in chapters:
                chapter_scenes = await self._analyze_chapter(chapter, trailer_gen.id, weights)
                all_scenes.extend(chapter_scenes)
            
            # 4. Rank and select top scenes
            all_scenes.sort(key=lambda s: s.overall_score, reverse=True)
            max_scenes = min(config.max_scenes, len(all_scenes))
            selected_scenes = all_scenes[:max_scenes]
            
            # 5. Assign scene numbers to selected scenes
            total_duration = 0.0
            for i, scene in enumerate(selected_scenes):
                scene.is_selected = True
                scene.scene_number = i + 1
                scene.start_time_seconds = total_duration
                scene.duration_seconds = self._estimate_scene_duration(scene)
                total_duration += scene.duration_seconds
            
            # 6. Mark remaining scenes as not selected
            for scene in all_scenes[max_scenes:]:
                scene.is_selected = False
            
            # 7. Add all scenes to DB
            self.session.add_all(all_scenes)
            await self.session.commit()
            
            # 8. Update trailer generation status
            trailer_gen.scenes_selected_count = len(selected_scenes)
            trailer_gen.status = TrailerStatus.SCENES_SELECTED
            if total_duration > 0:
                # Calculate actual estimated duration
                trailer_gen.actual_duration_seconds = int(total_duration)
            await self.session.commit()
            await self.session.refresh(trailer_gen)
            
            logger.info(
                f"[KAN-149] Analysis complete: {len(selected_scenes)} scenes selected, "
                f"~{total_duration:.1f}s estimated duration"
            )
            
            return trailer_gen
            
        except Exception as e:
            logger.error(f"[KAN-149] Scene analysis failed: {e}")
            trailer_gen.status = TrailerStatus.FAILED
            trailer_gen.error_message = str(e)
            await self.session.commit()
            raise
    
    async def _get_project_chapters(self, project_id: uuid.UUID) -> List[Any]:
        """Fetch all chapters for a project.
        
        Returns list of chapter objects with content.
        """
        from app.books.models import Book, Chapter
        
        # Get all books for this project
        books_result = await self.session.execute(
            select(Book).where(Book.project_id == project_id)
        )
        books = books_result.scalars().all()
        
        # Get all chapters from all books
        all_chapters = []
        for book in books:
            chapters_result = await self.session.execute(
                select(Book.__fields__['chapters'].type).where(
                    Book.__fields__['id'].type.book_id == book.id
                )
            )
            # Get chapters through relationship
            chapters_result = await self.session.execute(
                select(Chapter).where(Chapter.book_id == book.id).order_by(Chapter.chapter_number)
            )
            chapters = chapters_result.scalars().all()
            all_chapters.extend(chapters)
        
        logger.info(f"[KAN-149] Found {len(all_chapters)} chapters for project {project_id}")
        return list(all_chapters)
    
    async def _analyze_chapter(
        self,
        chapter: Any,
        trailer_gen_id: uuid.UUID,
        weights: Dict[str, float],
    ) -> List[TrailerScene]:
        """Analyze a single chapter for highlight moments.
        
        Uses AI to identify and score key scenes.
        """
        scene_scores = await self._score_chapter_content(chapter)
        
        trailer_scenes = []
        for score in scene_scores:
            overall = (
                score["action_score"] * weights["action"]
                + score["emotional_score"] * weights["emotional"]
                + score["visual_score"] * weights["visual"]
                + score["narrative_score"] * weights["narrative"]
            )
            
            trailer_scene = TrailerScene(
                trailer_generation_id=trailer_gen_id,
                chapter_id=chapter.id,
                scene_number=0,  # Will be assigned during selection
                scene_title=score.get("scene_title"),
                scene_description=score.get("scene_description"),
                action_score=score["action_score"],
                emotional_score=score["emotional_score"],
                visual_score=score["visual_score"],
                narrative_score=score["narrative_score"],
                overall_score=overall,
                is_selected=False,
                selection_reason=score.get("selection_reason"),
                duration_seconds=self._estimate_scene_duration_from_scores(score),
            )
            trailer_scenes.append(trailer_scene)
        
        return trailer_scenes
    
    async def _score_chapter_content(self, chapter: Any) -> List[Dict[str, Any]]:
        """Use AI to score chapter content for trailer moments.
        
        Returns list of scene scores with all dimensions.
        """
        chapter_content = getattr(chapter, "content", "") or ""
        chapter_title = getattr(chapter, "title", "") or f"Chapter {getattr(chapter, 'chapter_number', '?')}"
        
        if len(chapter_content) < 100:
            # Not enough content to analyze
            return []
        
        system_prompt = """You are a professional film trailer editor. Analyze the provided chapter content and identify potential trailer highlight moments.

For each highlight moment you identify, provide:
1. A brief scene title (5-10 words)
2. A description of what makes this moment compelling (20-40 words)
3. Scores from 0.0 to 1.0 for each dimension:
   - action_score: Movement, conflict, excitement level
   - emotional_score: Impact, resonance, character moments
   - visual_score: Cinematic potential, imagery quality
   - narrative_score: Plot importance, story arc contribution
4. A brief explanation of why this scene is good for a trailer

Return a JSON array of highlight scenes. Each scene should be:
{
  "scene_title": "string",
  "scene_description": "string",
  "action_score": float (0.0-1.0),
  "emotional_score": float (0.0-1.0),
  "visual_score": float (0.0-1.0),
  "narrative_score": float (0.0-1.0),
  "selection_reason": "string"
}

Identify 3-8 highlight moments per chapter. Focus on moments that would create compelling trailer content."""

        user_prompt = f"""Analyze this chapter for trailer highlight moments:

Chapter Title: {chapter_title}

Content:
{chapter_content[:3000]}

Identify key moments suitable for a trailer and score them."""

        try:
            # Use OpenRouterService via provider_router for flexible model selection
            from app.core.services.provider_router import provider_router
            
            response = await provider_router.chat_completion(
                model="openai/gpt-4o-mini",  # Fast, cost-effective for analysis
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            # Extract content from response
            content = response.choices[0].message.content if hasattr(response, 'choices') else str(response)
            # Try to extract JSON array from response
            json_start = content.find("[")
            json_end = content.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                scenes = json.loads(json_str)
                return scenes
            
            return []
            
        except Exception as e:
            logger.warning(f"[KAN-149] AI scoring failed for chapter {chapter.id}: {e}")
            # Fallback: Return a single scene based on chapter presence
            return [{
                "scene_title": chapter_title,
                "scene_description": f"Key moment from {chapter_title}",
                "action_score": 0.5,
                "emotional_score": 0.5,
                "visual_score": 0.5,
                "narrative_score": 0.5,
                "selection_reason": "Included as chapter representative (AI fallback)",
            }]
    
    def _estimate_scene_duration(self, scene: TrailerScene) -> float:
        """Estimate scene duration for trailer pacing.
        
        Higher action/emotional scores = shorter clips (more dynamic).
        Higher narrative scores = longer clips (more story context).
        """
        base_duration = 5.0  # 5 seconds base
        
        # Action scenes tend to be shorter and punchier
        action_modifier = -2.0 * scene.action_score
        
        # Narrative scenes need more time to establish
        narrative_modifier = 2.0 * scene.narrative_score
        
        duration = base_duration + action_modifier + narrative_modifier
        return max(3.0, min(10.0, duration))  # Clamp between 3-10 seconds
    
    def _estimate_scene_duration_from_scores(self, scores: Dict[str, float]) -> float:
        """Estimate duration from raw scores before TrailerScene creation."""
        base_duration = 5.0
        action_modifier = -2.0 * scores.get("action_score", 0.5)
        narrative_modifier = 2.0 * scores.get("narrative_score", 0.5)
        duration = base_duration + action_modifier + narrative_modifier
        return max(3.0, min(10.0, duration))


class TrailerGenerationService:
    """Coordinator service for trailer generation workflow.
    
    Manages the full pipeline from analysis to final output.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.scene_service = TrailerSceneService(session)
    
    async def get_trailer_status(self, trailer_id: uuid.UUID) -> Optional[TrailerGeneration]:
        """Get current status of a trailer generation."""
        result = await self.session.execute(
            select(TrailerGeneration).where(TrailerGeneration.id == trailer_id)
        )
        return result.scalar_one_or_none()
    
    async def get_selected_scenes(self, trailer_id: uuid.UUID) -> List[TrailerScene]:
        """Get all selected scenes for a trailer, ordered by sequence."""
        result = await self.session.execute(
            select(TrailerScene)
            .where(TrailerScene.trailer_generation_id == trailer_id)
            .where(TrailerScene.is_selected == True)
            .order_by(TrailerScene.scene_number)
        )
        return list(result.scalars().all())

    # ============================================================
    # KAN-150: Trailer Script + Narration Generation
    # ============================================================

    async def generate_trailer_script_and_narration(
        self,
        trailer_id: uuid.UUID,
        include_narration: bool = True,
        narration_voice: str = "male_deep",
        title_cards: Optional[Dict[str, Any]] = None,
    ) -> TrailerGeneration:
        """KAN-150: Generate trailer script and optional narration audio.

        Pipeline step: SCENES_SELECTED → SCRIPT_GENERATING → SCRIPT_READY
                                               → AUDIO_GENERATING → AUDIO_READY

        1. Fetch selected scenes from KAN-149 analysis
        2. Use AI to generate a coherent trailer script tying scenes together
        3. Extract narration text from the script
        4. If include_narration=True, generate narration audio via ElevenLabs
        5. Update TrailerGeneration record with script, narration_text, audio_url
        """
        logger.info(f"[KAN-150] Starting script+ narration for trailer {trailer_id}")

        # 1. Fetch the trailer generation record
        trailer = await self.get_trailer_status(trailer_id)
        if not trailer:
            raise ValueError(f"Trailer generation {trailer_id} not found")

        if trailer.status not in (TrailerStatus.SCENES_SELECTED, TrailerStatus.SCRIPT_READY):
            raise ValueError(
                f"Cannot generate script: status is {trailer.status.value}, "
                f"expected scenes_selected or script_ready"
            )

        # 2. Fetch selected scenes
        scenes = await self.get_selected_scenes(trailer_id)
        if not scenes:
            raise ValueError(f"No selected scenes found for trailer {trailer_id}")

        try:
            # === PHASE 1: Script Generation ===
            trailer.status = TrailerStatus.SCRIPT_GENERATING
            await self.session.commit()

            script_result = await self._generate_trailer_script(
                scenes=scenes,
                tone=trailer.tone,
                style=trailer.style,
                target_duration=trailer.target_duration_seconds,
                title_cards=title_cards,
            )

            trailer.trailer_script = script_result["script"]
            trailer.narration_text = script_result["narration_text"]
            trailer.status = TrailerStatus.SCRIPT_READY
            await self.session.commit()
            logger.info(
                f"[KAN-150] Script generated for trailer {trailer_id}, "
                f"narration length={len(script_result.get('narration_text', '') or '')} chars"
            )

            # === PHASE 2: Narration Audio Generation ===
            if include_narration and trailer.narration_text:
                trailer.status = TrailerStatus.AUDIO_GENERATING
                await self.session.commit()

                narration_url = await self._generate_narration_audio(
                    narration_text=trailer.narration_text,
                    voice=narration_voice,
                    user_id=trailer.user_id,
                )

                if narration_url:
                    trailer.narration_audio_url = narration_url
                    trailer.status = TrailerStatus.AUDIO_READY
                    logger.info(f"[KAN-150] Narration audio generated: {narration_url}")
                else:
                    # Script is ready even if audio fails
                    trailer.status = TrailerStatus.SCRIPT_READY
                    logger.warning(f"[KAN-150] Narration audio generation failed, script still available")

                await self.session.commit()

            await self.session.refresh(trailer)
            return trailer

        except Exception as e:
            logger.error(f"[KAN-150] Script/narration generation failed: {e}")
            trailer.status = TrailerStatus.FAILED
            trailer.error_message = str(e)
            await self.session.commit()
            raise

    async def _generate_trailer_script(
        self,
        scenes: List[TrailerScene],
        tone: str,
        style: str,
        target_duration: int,
        title_cards: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Use AI to generate a trailer script from selected scenes.

        Returns:
            {
                "script": str,       # Full trailer script (JSON string)
                "narration_text": str # Clean narration text for TTS
            }
        """
        # Build scene descriptions for the AI prompt
        scene_descriptions = []
        for i, scene in enumerate(scenes):
            desc = (
                f"Scene {i+1}: {scene.scene_title or 'Untitled'}\n"
                f"  Description: {scene.scene_description or 'No description'}\n"
                f"  Duration: {scene.duration_seconds:.1f}s\n"
                f"  Scores: action={scene.action_score:.2f}, emotional={scene.emotional_score:.2f}, "
                f"visual={scene.visual_score:.2f}, narrative={scene.narrative_score:.2f}"
            )
            scene_descriptions.append(desc)

        scenes_text = "\n".join(scene_descriptions)

        # Build title card context
        title_card_text = ""
        if title_cards:
            parts = []
            if title_cards.get("series_name"):
                parts.append(f'Series/Book: "{title_cards["series_name"]}"')
            if title_cards.get("tagline"):
                parts.append(f'Tagline: "{title_cards["tagline"]}"')
            if title_cards.get("cta_text"):
                parts.append(f'Call-to-action: "{title_cards["cta_text"]}"')
            if parts:
                title_card_text = "\nTitle cards to include:\n" + "\n".join(f"  - {p}" for p in parts)

        system_prompt = f"""You are a professional film trailer scriptwriter. Create a compelling trailer script from the selected scenes.

Tone: {tone}
Style: {style}
Target total duration: {target_duration} seconds

Your script must include:
1. A JSON "script" object with a scene_sequence array, each entry having:
   - scene_number (int)
   - narration (str or null if no narration for this scene)
   - visual_description (str, overriding/enhancing the scene's visual)
   - duration_seconds (float)
2. A clean "narration_text" string — the voiceover text only, with no stage directions or JSON markup. This will be sent directly to a TTS engine.

Rules:
- Scene sequence should flow naturally even if the original scene order is rearranged
- Narration should complement the visuals, not describe them literally
- Keep total duration close to {target_duration}s
- Narration text should be 2-5 sentences per scene, pacing appropriate for the tone
- For {tone} tone, narration should be {self._tone_narration_style(tone)}

Return a JSON object:
{{
  "script": {{
    "title": "string",
    "tone": "{tone}",
    "total_duration_seconds": float,
    "scene_sequence": [
      {{"scene_number": int, "narration": "str or null", "visual_description": "str", "duration_seconds": float}}
    ],
    "title_cards": {{}}  
  }},
  "narration_text": "Clean voiceover text only, no stage directions"
}}"""

        user_prompt = f"""Create a trailer script from these selected scenes:

{scenes_text}
{title_card_text}

Write the script and narration now."""

        try:
            from app.core.services.provider_router import provider_router

            response = await provider_router.chat_completion(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,  # Creative task
                max_tokens=3000,
            )

            content = response.choices[0].message.content if hasattr(response, 'choices') else str(response)

            # Extract JSON from response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
                return {
                    "script": json.dumps(result.get("script", {}), ensure_ascii=False),
                    "narration_text": result.get("narration_text", ""),
                }

            # Fallback: treat entire content as narration text
            logger.warning("[KAN-150] Could not parse script JSON, using content as narration")
            return {"script": content, "narration_text": content}

        except Exception as e:
            logger.error(f"[KAN-150] AI script generation failed: {e}")
            raise

    async def _generate_narration_audio(
        self,
        narration_text: str,
        voice: str = "male_deep",
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[str]:
        """Generate narration audio using ElevenLabs TTS.

        Returns the S3 storage URL of the generated audio, or None on failure.
        """
        if not narration_text or not narration_text.strip():
            logger.warning("[KAN-150] Empty narration text, skipping audio generation")
            return None

        # Map voice name to ElevenLabs voice ID
        voice_map = {
            "male_deep": "21m00Tcm4TlvDq8ikWAM",       # Adam
            "female_soft": "EXAVITQu4vr4xnSDxMaL",     # Bella
            "male_narrator": "nPczCjzK2NnW1Nn0iX0G",    # Marcus
            "female_narrator": "mTSvIrmUhORL3Bq3Bq7M",  # Lily
        }
        voice_id = voice_map.get(voice, voice_map["male_deep"])

        try:
            from app.core.services.elevenlabs import ElevenLabsService
            tts = ElevenLabsService()

            result = await tts.generate_enhanced_speech(
                text=narration_text,
                voice_id=voice_id,
                user_id=str(user_id) if user_id else None,
                emotion="neutral",
                speed=1.0,
            )

            audio_url = result.get("audio_url")
            if audio_url:
                # Persist to S3 storage
                try:
                    from app.core.services.storage import get_storage_service, S3StorageService
                    import uuid as _uuid_mod
                    storage = get_storage_service()
                    s3_path = S3StorageService.build_media_path(
                        user_id=str(user_id) if user_id else 'system',
                        media_type='audio',
                        record_id=str(_uuid_mod.uuid4()),
                        extension='mp3',
                    )
                    persisted_url = await storage.persist_from_url(audio_url, s3_path, content_type='audio/mpeg')
                    logger.info(f"[KAN-150] Persisted narration audio to S3: {s3_path}")
                    return persisted_url
                except Exception as persist_err:
                    logger.error(f"[KAN-150] Failed to persist narration to S3: {persist_err}")
                    # Return the original URL as fallback
                    return audio_url

            logger.warning(f"[KAN-150] ElevenLabs returned no audio URL")
            return None

        except Exception as e:
            logger.error(f"[KAN-150] Narration audio generation failed: {e}")
            return None

    @staticmethod
    def _tone_narration_style(tone: str) -> str:
        """Return narration style guidance for the given tone."""
        styles = {
            "epic": "grand, sweeping, building intensity — like a movie trailer voiceover",
            "dramatic": "intense, emotional, with pauses for impact — think Oscar-bait trailer",
            "action": "fast-paced, punchy, building momentum — quick cuts feel",
            "romantic": "tender, intimate, warm — soft and inviting",
            "mysterious": "enigmatic, slow-burn, with questions — draw the viewer in",
            "default": "engaging and compelling, balancing energy with clarity",
        }
        return styles.get(tone, styles["default"])