from typing import Dict, Any, Optional, List
import aiohttp
import asyncio
from app.core.config import settings
from app.core.model_config import get_model_config
from app.core.services.model_fallback import fallback_manager
import logging

logger = logging.getLogger(__name__)


class ModelsLabV7VideoService:
    """ModelsLab V7 Video Service for Veo 2 Video Generation and Lip Sync"""

    def __init__(self):
        if not settings.MODELSLAB_API_KEY:
            raise ValueError("MODELSLAB_API_KEY is required")

        self.api_key = settings.MODELSLAB_API_KEY
        self.base_url = settings.MODELSLAB_BASE_URL  # v7 URL
        self.headers = {"Content-Type": "application/json"}

        # ✅ V7 Video API Endpoints
        self.image_to_video_endpoint = f"{self.base_url}/video-fusion/image-to-video"
        self.lip_sync_endpoint = f"{self.base_url}/video-fusion/lip-sync"

        # ✅ Available video models
        self.video_models = {
            "veo2": "veo2",  # Primary Veo 2 model
            "veo-3.1-fast": "veo-3.1-fast",
            "omni-human": "omni-human",
            "omni-human-1.5": "omni-human-1.5",
            "wan2.5-i2v": "wan2.5-i2v",
            "seedance-1-5-pro": "seedance-1-5-pro",
        }

        # ✅ Available lip sync models
        self.lipsync_models = {
            "lipsync-2": "lipsync-2",  # Latest lip sync model
            "lipsync-1": "lipsync-1",  # Previous version
            "lipsync-hd": "lipsync-2",  # HD quality mapping
        }

    async def generate_image_to_video(
        self,
        image_url: str,
        prompt: str,
        model_id: str = "veo-3.1-fast",
        negative_prompt: str = "",
        duration: float = 5.0,
        fps: int = 24,
        motion_strength: float = 0.8,
        init_audio: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate video from image using ModelsLab V7 API (Strict I2V)"""

        attempts = [
            {"model_id": model_id, "description": f"primary model {model_id}"},
        ]

        # Add a smart fallback based on the primary model
        if "veo" in model_id or "omni" in model_id:
            attempts.append(
                {
                    "model_id": "omni-human-1.5",
                    "description": "fallback model omni-human-1.5",
                }
            )
        elif "wan" in model_id:
            attempts.append(
                {
                    "model_id": "seedance-1-5-pro",
                    "description": "fallback model seedance",
                }
            )

        last_error = None

        for attempt in attempts:
            current_model_id = attempt["model_id"]
            current_description = attempt["description"]

            try:
                payload = {
                    "model_id": current_model_id,
                    "init_image": image_url,
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "key": self.api_key,
                }

                # Add optional parameters if they're supported
                if duration != 5.0:
                    payload["duration"] = duration
                if fps != 24:
                    payload["fps"] = fps
                if motion_strength != 0.8:
                    payload["motion_strength"] = motion_strength

                # Add new I2V parameters
                if init_audio:
                    payload["init_audio"] = init_audio
                    logger.info(
                        f"[MODELSLAB V7 VIDEO] Including init_audio for audio-reactive/lip-sync"
                    )

                if resolution:
                    payload["resolution"] = resolution

                if current_model_id != model_id:
                    logger.info(
                        f"[MODELSLAB V7 VIDEO] Primary model unavailable, falling back to {current_model_id}"
                    )
                    logger.info(
                        f"[MODELSLAB V7 VIDEO] Retrying with same parameters: image={image_url}, prompt={prompt[:100]}..."
                    )

                logger.info(
                    f"[MODELSLAB V7 VIDEO] Generating video with {current_description}"
                )
                logger.info(f"[MODELSLAB V7 VIDEO] Model: {current_model_id}")
                logger.info(f"[MODELSLAB V7 VIDEO] Image: {image_url}")
                logger.info(f"[MODELSLAB V7 VIDEO] Prompt: {prompt[:100]}...")

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.image_to_video_endpoint,
                        json=payload,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=120),  # 2 minute timeout
                    ) as response:

                        if response.status != 200:
                            error_text = await response.text()
                            raise Exception(f"HTTP {response.status}: {error_text}")

                        result = await response.json()

                        logger.info(
                            f"[MODELSLAB V7 VIDEO] Response status: {response.status}"
                        )
                        logger.info(f"[MODELSLAB V7 VIDEO] Response: {result}")

                        # Check for specific veo2 error message
                        if result.get(
                            "status"
                        ) == "error" and "Video cannot be generated at the moment, try use another model" in result.get(
                            "message", ""
                        ):
                            logger.warning(
                                f"[MODELSLAB V7 VIDEO] Veo2 model unavailable: {result.get('message')}"
                            )
                            last_error = Exception(
                                f"Veo2 model unavailable: {result.get('message')}"
                            )
                            continue  # Try next model

                        processed_response = self._process_video_response(
                            result, "image_to_video"
                        )

                        # If status is processing, start polling
                        if processed_response.get("status") == "processing":
                            fetch_result = processed_response.get("fetch_result")
                            future_links = processed_response.get("future_links", [])
                            if fetch_result:
                                logger.info(
                                    f"[MODELSLAB V7 VIDEO] Starting polling for image-to-video completion"
                                )
                                poll_result = await self._poll_for_video_completion(
                                    fetch_result, future_links
                                )
                                return poll_result

                        return processed_response

            except Exception as e:
                logger.error(
                    f"[MODELSLAB V7 VIDEO ERROR] with {current_description}: {str(e)}"
                )
                last_error = e

                # If this was the last attempt, break and raise the error
                if attempt == attempts[-1]:
                    break
                # Otherwise, continue to fallback
                continue

        # If we get here, both attempts failed
        error_msg = (
            f"Both veo2 and seedance-i2v models failed. Last error: {str(last_error)}"
        )
        logger.error(f"[MODELSLAB V7 VIDEO] {error_msg}")
        raise Exception(error_msg)

    async def generate_lip_sync(
        self, video_url: str, audio_url: str, model_id: str = "lipsync-2"
    ) -> Dict[str, Any]:
        """Generate lip sync using ModelsLab V7 API"""

        try:
            payload = {
                "model_id": model_id,
                "init_video": video_url,
                "init_audio": audio_url,
                "key": self.api_key,
            }

            logger.info(f"[MODELSLAB V7 LIPSYNC] Generating lip sync")
            logger.info(f"[MODELSLAB V7 LIPSYNC] Model: {model_id}")
            logger.info(f"[MODELSLAB V7 LIPSYNC] Video: {video_url}")
            logger.info(f"[MODELSLAB V7 LIPSYNC] Audio: {audio_url}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.lip_sync_endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=300),  # 5 minute timeout
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"HTTP {response.status}: {error_text}")

                    result = await response.json()

                    logger.info(
                        f"[MODELSLAB V7 LIPSYNC] Response status: {response.status}"
                    )
                    logger.info(f"[MODELSLAB V7 LIPSYNC] Response: {result}")

                    processed_response = self._process_video_response(
                        result, "lip_sync"
                    )

                    # If status is processing, start polling
                    if processed_response.get("status") == "processing":
                        fetch_result = processed_response.get("fetch_result")
                        future_links = processed_response.get("future_links", [])
                        if fetch_result:
                            logger.info(
                                f"[MODELSLAB V7 VIDEO] Starting polling for lip sync completion"
                            )
                            poll_result = await self._poll_for_video_completion(
                                fetch_result, future_links
                            )
                            return poll_result

                    return processed_response

        except Exception as e:
            logger.error(f"[MODELSLAB V7 LIPSYNC ERROR]: {str(e)}")
            raise e

    async def enhance_video_for_scene(
        self,
        scene_description: str,
        image_url: str,
        audio_url: Optional[str] = None,
        dialogue_audio: Optional[List[Dict[str, Any]]] = None,
        style: str = "cinematic",
        include_lipsync: bool = True,
        script_style: str = None,
        script_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate and enhance video for a complete scene with enhanced prompt structure"""

        try:
            logger.info(f"[SCENE VIDEO] Enhancing scene: {scene_description[:50]}...")

            # If we have dialogue audio, generate separate video scenes per dialogue
            if dialogue_audio and len(dialogue_audio) > 0:
                logger.info(
                    f"[SCENE VIDEO] Generating {len(dialogue_audio)} separate video scenes for dialogues"
                )
                return await self._generate_per_dialogue_videos(
                    scene_description,
                    image_url,
                    dialogue_audio,
                    style,
                    include_lipsync,
                    script_style,
                    script_data,
                )

            # Original logic for scenes without dialogue or with background audio only
            video_prompt = self._create_enhanced_video_prompt_from_script(
                scene_description, style, dialogue_audio, script_style, script_data
            )

            video_result = await self.generate_image_to_video(
                image_url=image_url,
                prompt=video_prompt,
                model_id="veo2",
                negative_prompt=self._get_negative_prompt_for_style(style),
            )

            if video_result.get("status") != "success":
                raise Exception(
                    f"Video generation failed: {video_result.get('error', 'Unknown error')}"
                )

            video_url = video_result.get("video_url")
            if not video_url:
                raise Exception("No video URL in response")

            enhanced_result = {
                "original_video": video_result,
                "video_url": video_url,
                "has_lipsync": False,
                "dialogue_audio": dialogue_audio or [],
            }

            # Apply lip sync for background audio if provided
            if include_lipsync and audio_url and not dialogue_audio:
                logger.info(f"[SCENE VIDEO] Applying lip sync for background audio...")

                lipsync_result = await self.generate_lip_sync(
                    video_url=video_url, audio_url=audio_url, model_id="lipsync-2"
                )

                if lipsync_result.get("status") == "success":
                    lipsync_video_url = lipsync_result.get("video_url")
                    if lipsync_video_url:
                        enhanced_result["lipsync_video"] = lipsync_result
                        enhanced_result["video_url"] = (
                            lipsync_video_url  # Use lip-synced version
                        )
                        enhanced_result["has_lipsync"] = True
                        logger.info(
                            f"[SCENE VIDEO] ✅ Background audio lip sync applied successfully"
                        )
                    else:
                        logger.warning(
                            f"[SCENE VIDEO] ⚠️ Background audio lip sync completed but no video URL"
                        )
                else:
                    logger.warning(
                        f"[SCENE VIDEO] ⚠️ Background audio lip sync failed: {lipsync_result.get('error', 'Unknown error')}"
                    )

            return {
                "status": "success",
                "scene_description": scene_description,
                "enhanced_video": enhanced_result,
                "processing_steps": ["image_to_video"]
                + (["lip_sync"] if enhanced_result["has_lipsync"] else []),
                "character_dialogue_count": (
                    len(dialogue_audio) if dialogue_audio else 0
                ),
            }

        except Exception as e:
            logger.error(f"[SCENE VIDEO] Enhancement failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "scene_description": scene_description,
            }

    async def _generate_per_dialogue_videos(
        self,
        scene_description: str,
        image_url: str,
        dialogue_audio: List[Dict[str, Any]],
        style: str = "cinematic",
        include_lipsync: bool = True,
        script_style: str = None,
        script_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate separate video scenes for each dialogue line with proper lip sync"""

        logger.info(
            f"[PER-DIALOGUE VIDEO] Generating {len(dialogue_audio)} separate video scenes"
        )

        dialogue_videos = []
        processing_steps = []

        for i, dialogue in enumerate(dialogue_audio):
            character_name = dialogue.get("character", "Unknown")
            dialogue_text = dialogue.get("text", "").strip()
            dialogue_audio_url = dialogue.get("audio_url")

            logger.info(
                f"[PER-DIALOGUE VIDEO] Processing dialogue {i+1}: {character_name}"
            )

            # Create a focused prompt for this specific dialogue
            dialogue_prompt = self._create_dialogue_specific_prompt(
                scene_description, character_name, dialogue_text, style, script_style
            )

            # Generate video for this dialogue
            video_result = await self.generate_image_to_video(
                image_url=image_url,
                prompt=dialogue_prompt,
                model_id="veo2",
                negative_prompt=self._get_negative_prompt_for_style(style),
            )

            if video_result.get("status") != "success":
                logger.error(
                    f"[PER-DIALOGUE VIDEO] Video generation failed for dialogue {i+1}: {video_result.get('error')}"
                )
                continue

            video_url = video_result.get("video_url")
            if not video_url:
                logger.warning(f"[PER-DIALOGUE VIDEO] No video URL for dialogue {i+1}")
                continue

            # Apply lip sync for this dialogue if audio is available
            if include_lipsync and dialogue_audio_url:
                logger.info(
                    f"[PER-DIALOGUE VIDEO] Applying lip sync for {character_name}"
                )

                lipsync_result = await self.generate_lip_sync(
                    video_url=video_url,
                    audio_url=dialogue_audio_url,
                    model_id="lipsync-2",
                )

                if lipsync_result.get("status") == "success":
                    lipsync_video_url = lipsync_result.get("video_url")
                    if lipsync_video_url:
                        video_url = lipsync_video_url
                        processing_steps.append("lip_sync")
                        logger.info(
                            f"[PER-DIALOGUE VIDEO] ✅ Lip sync applied for {character_name}"
                        )
                    else:
                        logger.warning(
                            f"[PER-DIALOGUE VIDEO] ⚠️ Lip sync completed but no video URL for {character_name}"
                        )
                else:
                    logger.warning(
                        f"[PER-DIALOGUE VIDEO] ⚠️ Lip sync failed for {character_name}: {lipsync_result.get('error')}"
                    )

            dialogue_videos.append(
                {
                    "character": character_name,
                    "dialogue_text": dialogue_text,
                    "video_url": video_url,
                    "dialogue_index": i,
                    "has_lipsync": include_lipsync and dialogue_audio_url,
                }
            )

            logger.info(
                f"[PER-DIALOGUE VIDEO] ✅ Dialogue {i+1} video generated successfully"
            )

        if not dialogue_videos:
            raise Exception("No dialogue videos were successfully generated")

        return {
            "status": "success",
            "scene_description": scene_description,
            "dialogue_videos": dialogue_videos,
            "processing_steps": ["image_to_video"] + processing_steps,
            "character_dialogue_count": len(dialogue_audio),
            "successful_dialogues": len(dialogue_videos),
            "video_generation_method": "per_dialogue",
        }

    def _create_dialogue_specific_prompt(
        self,
        scene_description: str,
        character_name: str,
        dialogue_text: str,
        style: str = "cinematic",
        script_style: str = None,
    ) -> str:
        """Create a focused video prompt for a specific character's dialogue"""

        base_prompt = self._create_scene_video_prompt(scene_description, style)

        # Special handling for cinematic scripts
        is_cinematic = script_style and "cinematic" in script_style.lower()

        # Focus on the specific character and dialogue
        character_focus = f'Focus on {character_name} speaking: "{dialogue_text}"'

        if is_cinematic:
            # For cinematic scripts, emphasize character performance
            enhanced_prompt = f"""
{character_focus}

{base_prompt}

CRITICAL: Generate a cinematic close-up scene showing {character_name} speaking this specific dialogue naturally.
Focus on {character_name}'s facial expressions, mouth movements, and emotional delivery.
Use cinematic camera angles and lighting to enhance the dramatic effect of this specific dialogue moment.
Ensure {character_name} is clearly visible and properly positioned for dialogue delivery.
"""
        else:
            # For other scripts, standard character visibility
            enhanced_prompt = f"""
{character_focus}

{base_prompt}

Show {character_name} speaking this dialogue naturally.
Ensure {character_name} is clearly visible with proper facial expressions and mouth movements.
"""

        logger.info(
            f"[DIALOGUE PROMPT] Created focused prompt for {character_name}: {enhanced_prompt[:200]}..."
        )
        return enhanced_prompt.strip()

    async def batch_generate_scene_videos(
        self,
        scenes: List[Dict[str, Any]],
        max_concurrent: int = 2,  # Lower for video generation
    ) -> List[Dict[str, Any]]:
        """Generate videos for multiple scenes with controlled concurrency"""

        logger.info(
            f"[BATCH VIDEO] Processing {len(scenes)} scenes (max {max_concurrent} concurrent)"
        )

        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def generate_single_scene_video(
            scene: Dict[str, Any], index: int
        ) -> Dict[str, Any]:
            async with semaphore:
                try:
                    scene_description = scene.get("description", "")
                    image_url = scene.get("image_url", "")
                    audio_url = scene.get("audio_url")
                    style = scene.get("style", "cinematic")

                    if not image_url:
                        raise Exception("No image URL provided for scene")

                    result = await self.enhance_video_for_scene(
                        scene_description=scene_description,
                        image_url=image_url,
                        audio_url=audio_url,
                        style=style,
                        include_lipsync=bool(audio_url),
                    )

                    result["batch_index"] = index
                    result["scene_id"] = scene.get("scene_id", f"scene_{index + 1}")

                    # Delay to prevent rate limiting
                    await asyncio.sleep(2.0)  # 2 second delay between requests

                    return result

                except Exception as e:
                    logger.error(f"[BATCH VIDEO] Failed to generate scene {index}: {e}")
                    return {
                        "status": "error",
                        "error": str(e),
                        "batch_index": index,
                        "scene_id": scene.get("scene_id", f"scene_{index + 1}"),
                    }

        # Process all scenes
        tasks = [
            generate_single_scene_video(scene, i) for i, scene in enumerate(scenes)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "status": "error",
                        "error": str(result),
                        "batch_index": i,
                        "scene_id": scenes[i].get("scene_id", f"scene_{i + 1}"),
                    }
                )
            else:
                processed_results.append(result)

        successful_count = sum(
            1 for r in processed_results if r.get("status") == "success"
        )
        logger.info(
            f"[BATCH VIDEO] Completed: {successful_count}/{len(scenes)} successful"
        )

        return processed_results

    def get_video_model_for_style(self, style: str) -> str:
        """Get appropriate Veo 2 model based on style"""

        # For now, all styles use the main veo2 model
        # This could be expanded if different Veo 2 variants become available
        return "veo2"

    def get_lipsync_model_for_quality(self, quality_tier: str) -> str:
        """Get appropriate lip sync model based on quality tier"""

        model_map = {
            "basic": "lipsync-1",
            "standard": "lipsync-2",
            "premium": "lipsync-2",
            "professional": "lipsync-2",
        }
        return model_map.get(quality_tier.lower(), "lipsync-2")

    def calculate_video_duration_from_audio(
        self, audio_files: List[Dict], scene_id: str
    ) -> float:
        """Calculate video duration based on audio files for a scene"""

        total_duration = 0.0
        scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1

        # Find audio files for this scene
        for audio in audio_files:
            audio_scene = audio.get("scene", 1)
            if audio_scene == scene_number:
                total_duration += audio.get("duration", 3.0)

        # Ensure minimum duration of 3 seconds, maximum of 30 seconds (Veo 2 limits)
        return max(3.0, min(total_duration, 30.0))

    def _create_scene_video_prompt(self, scene_description: str, style: str) -> str:
        """Create optimized prompt for Veo 2 video generation"""

        style_modifiers = {
            "realistic": "cinematic realism, natural movement, photorealistic details, smooth camera motion",
            "cinematic": "epic cinematic style, dramatic lighting, professional cinematography, dynamic camera angles",
            "animated": "animated style, expressive movement, stylized animation, fluid motion",
            "fantasy": "fantasy cinematography, magical atmosphere, ethereal movements, mystical lighting",
            "comic": "comic book style, dynamic action, bold movements, superhero cinematography",
            "artistic": "artistic cinematography, creative movement, unique visual style, artistic flair",
        }

        style_prompt = style_modifiers.get(style.lower(), style_modifiers["cinematic"])

        # Enhanced prompt for Veo 2
        full_prompt = f"""
{scene_description}

{style_prompt}.
High quality video production, smooth motion, professional videography,
engaging visual storytelling, seamless transitions, cinematic composition.
""".strip()

        return full_prompt

    def _create_enhanced_video_prompt(
        self,
        scene_description: str,
        style: str,
        camera_movements: List[str] = None,
        character_actions: List[Dict[str, Any]] = None,
        character_dialogues: List[Dict[str, Any]] = None,
        scene_transitions: List[str] = None,
    ) -> str:
        """Create enhanced video prompt with camera movements, character actions, and dialogue attribution"""

        logger.info(
            f"[ENHANCED PROMPT] Creating enhanced prompt for scene: {scene_description[:50]}..."
        )

        # Base scene description
        prompt_parts = [f"Scene: {scene_description}"]

        # Add camera movements
        if camera_movements:
            camera_text = "Camera movements: " + ", ".join(camera_movements)
            prompt_parts.append(camera_text)
            logger.info(
                f"[ENHANCED PROMPT] Added {len(camera_movements)} camera movements"
            )

        # Add character actions
        if character_actions:
            actions_by_character = {}
            for action in character_actions:
                character = action.get("character", "Unknown")
                action_text = action.get("action", "")
                if character not in actions_by_character:
                    actions_by_character[character] = []
                actions_by_character[character].append(action_text)

            for character, actions in actions_by_character.items():
                actions_text = f"{character} ({', '.join(actions)})"
                prompt_parts.append(actions_text)
            logger.info(
                f"[ENHANCED PROMPT] Added {len(character_actions)} character actions"
            )

        # Add character dialogues with attribution
        if character_dialogues:
            for dialogue in character_dialogues:
                attributed_dialogue = dialogue.get("attributed_dialogue", "")
                if attributed_dialogue:
                    prompt_parts.append(attributed_dialogue)
            logger.info(
                f"[ENHANCED PROMPT] Added {len(character_dialogues)} character dialogues"
            )

        # Add scene transitions
        if scene_transitions:
            transitions_text = "Scene transitions: " + ", ".join(scene_transitions)
            prompt_parts.append(transitions_text)
            logger.info(
                f"[ENHANCED PROMPT] Added {len(scene_transitions)} scene transitions"
            )

        # Add style modifiers
        style_modifiers = {
            "realistic": "cinematic realism, natural movement, photorealistic details, smooth camera motion",
            "cinematic": "epic cinematic style, dramatic lighting, professional cinematography, dynamic camera angles",
            "animated": "animated style, expressive movement, stylized animation, fluid motion",
            "fantasy": "fantasy cinematography, magical atmosphere, ethereal movements, mystical lighting",
            "comic": "comic book style, dynamic action, bold movements, superhero cinematography",
            "artistic": "artistic cinematography, creative movement, unique visual style, artistic flair",
        }

        style_prompt = style_modifiers.get(style.lower(), style_modifiers["cinematic"])
        prompt_parts.append(style_prompt)

        # Add quality modifiers
        quality_modifiers = [
            "High quality video production, smooth motion, professional videography",
            "engaging visual storytelling, seamless transitions, cinematic composition",
            "natural movement, photorealistic details, smooth camera motion",
        ]
        prompt_parts.extend(quality_modifiers)

        # Combine all parts
        enhanced_prompt = "\n".join(prompt_parts)

        logger.info(
            f"[ENHANCED PROMPT] Final prompt length: {len(enhanced_prompt)} characters"
        )
        logger.info(f"[ENHANCED PROMPT] Preview: {enhanced_prompt[:200]}...")

        return enhanced_prompt

    def _create_enhanced_video_prompt_from_script(
        self,
        scene_description: str,
        style: str,
        dialogue_audio: Optional[List[Dict[str, Any]]] = None,
        script_style: str = None,
        script_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create enhanced video prompt using script parser for camera movements, character actions, and dialogue attribution"""

        logger.info(f"[ENHANCED PROMPT] Creating enhanced prompt from script data")

        # If we have script data with parsed components, use them
        if script_data and script_data.get("parsed_components"):
            parsed_components = script_data["parsed_components"]

            # Extract components for this specific scene
            scene_camera_movements = []
            scene_character_actions = []
            scene_character_dialogues = []
            scene_transitions = []

            # Filter components for the current scene (if scene-specific data is available)
            # For now, we'll use all components since scene matching is complex
            scene_camera_movements = parsed_components.get("camera_movements", [])
            scene_character_actions = parsed_components.get("character_actions", [])
            scene_character_dialogues = parsed_components.get("character_dialogues", [])
            scene_transitions = parsed_components.get("scene_transitions", [])

            logger.info(f"[ENHANCED PROMPT] Using parsed components:")
            logger.info(f"- Camera movements: {len(scene_camera_movements)}")
            logger.info(f"- Character actions: {len(scene_character_actions)}")
            logger.info(f"- Character dialogues: {len(scene_character_dialogues)}")
            logger.info(f"- Scene transitions: {len(scene_transitions)}")

            # Create enhanced prompt with parsed components
            enhanced_prompt = self._create_enhanced_video_prompt(
                scene_description=scene_description,
                style=style,
                camera_movements=scene_camera_movements,
                character_actions=scene_character_actions,
                character_dialogues=scene_character_dialogues,
                scene_transitions=scene_transitions,
            )

            return enhanced_prompt

        # Fallback to original method if no parsed components available
        logger.info(
            f"[ENHANCED PROMPT] No parsed components available, using fallback method"
        )
        return self._create_scene_video_prompt_with_characters(
            scene_description, style, dialogue_audio, script_style
        )

    def _create_scene_video_prompt_with_characters(
        self,
        scene_description: str,
        style: str,
        dialogue_audio: Optional[List[Dict[str, Any]]] = None,
        script_style: str = None,
    ) -> str:
        """Create optimized prompt for Veo 2 video generation with character information and dialogue"""

        base_prompt = self._create_scene_video_prompt(scene_description, style)

        # Special handling for cinematic scripts
        is_cinematic = script_style and "cinematic" in script_style.lower()

        # Add character information and dialogue if provided
        if dialogue_audio:
            character_info = []
            dialogue_lines = []

            for dialogue in dialogue_audio:
                character_name = dialogue.get("character", "Character")
                dialogue_text = dialogue.get("text", "").strip()
                character_profile = dialogue.get("character_profile", {})

                # Build character description
                char_desc = f"{character_name}"
                if character_profile.get("age"):
                    char_desc += f" ({character_profile['age']})"
                if (
                    character_profile.get("gender")
                    and character_profile["gender"] != "neutral"
                ):
                    char_desc += f" {character_profile['gender']}"
                if character_profile.get("personality"):
                    char_desc += f", {character_profile['personality']}"

                character_info.append(char_desc)

                # Include dialogue text for cinematic scripts - but only for the current dialogue
                # This prevents including ALL dialogues in one prompt
                if dialogue_text and is_cinematic:
                    # For cinematic scripts, focus on the current character's dialogue
                    dialogue_lines.append(f'{character_name}: "{dialogue_text}"')

            if character_info:
                characters_text = "Characters present: " + ", ".join(character_info)
                base_prompt = f"{characters_text}\n\n{base_prompt}"

                # Add dialogue information - prioritize for cinematic scripts but only current dialogue
                if dialogue_lines:
                    if is_cinematic:
                        # For cinematic scripts, put dialogue first and emphasize character interaction
                        # But only include the current character's dialogue, not all dialogues
                        dialogue_text = "Key dialogue scene:\n" + "\n".join(
                            dialogue_lines
                        )
                        base_prompt = f"{dialogue_text}\n\nScene context: {base_prompt}"

                        # Enhanced instructions for cinematic dialogue delivery
                        base_prompt += "\n\nCRITICAL: Generate a cinematic dialogue scene showing characters speaking their lines naturally. Characters must be clearly visible with proper facial expressions, mouth movements, and body language. Focus on character interactions and emotional delivery of the dialogue. Use cinematic camera angles and lighting to enhance the dramatic effect."
                    else:
                        # For other scripts, include dialogue but with less emphasis
                        dialogue_text = "Dialogue in this scene:\n" + "\n".join(
                            dialogue_lines
                        )
                        base_prompt = f"{base_prompt}\n\n{dialogue_text}"

                        # Standard instruction for character visibility
                        base_prompt += "\n\nShow characters speaking their dialogue naturally. Ensure characters are clearly visible and appropriately positioned for dialogue delivery with proper facial expressions and mouth movements."

        return base_prompt

    def _get_negative_prompt_for_style(self, style: str) -> str:
        """Get negative prompt to avoid unwanted elements"""

        base_negative = "blurry, low quality, distorted, pixelated, artifacts, glitches, stuttering motion"

        style_negatives = {
            "realistic": f"{base_negative}, cartoon, animated, artificial looking, fake",
            "cinematic": f"{base_negative}, amateur, poor lighting, shaky camera",
            "animated": f"{base_negative}, photorealistic, real people",
            "fantasy": f"{base_negative}, modern elements, technology, realistic",
            "comic": f"{base_negative}, photorealistic, dull colors",
            "artistic": f"{base_negative}, generic, boring, conventional",
        }

        return style_negatives.get(style.lower(), base_negative)

    def _extract_video_url(self, response: Dict[str, Any]) -> Optional[str]:
        """Extract video URL from response fields (future_links, links, proxy_links)"""

        # Priority order for video URL extraction
        url_fields = [
            "future_links",  # Processing videos
            "links",  # Completed videos
            "proxy_links",  # Alternative format
            "output",  # Standard output
        ]

        for field in url_fields:
            urls = response.get(field, [])
            if urls and len(urls) > 0:
                video_url = urls[0]
                # Handle different URL formats
                if isinstance(video_url, dict):
                    video_url = video_url.get("url") or video_url.get("video_url")
                if video_url and isinstance(video_url, str):
                    logger.info(
                        f"[MODELSLAB V7 VIDEO] Extracted video URL from {field}: {video_url}"
                    )
                    return video_url

        logger.warning(
            f"[MODELSLAB V7 VIDEO] No video URL found in response fields: {list(response.keys())}"
        )
        return None

    async def _try_fallback_retrieval(
        self, future_links: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Attempt fallback video retrieval using future_links URLs"""

        if not future_links:
            return None

        logger.info(
            f"[MODELSLAB V7 VIDEO] Attempting fallback retrieval from {len(future_links)} future_links"
        )

        for video_url in future_links:
            try:
                logger.info(f"[MODELSLAB V7 VIDEO] Checking fallback URL: {video_url}")

                # Validate that the video file exists at the URL
                async with aiohttp.ClientSession() as session:
                    async with session.head(
                        video_url, timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:

                        if response.status == 200:
                            content_type = response.headers.get("content-type", "")
                            content_length = response.headers.get("content-length", "0")

                            # Check if it's a video file
                            if (
                                "video" in content_type.lower()
                                or "mp4" in video_url.lower()
                            ):
                                logger.info(
                                    f"[MODELSLAB V7 VIDEO] ✅ Fallback video found: {video_url} (size: {content_length} bytes)"
                                )
                                return {
                                    "status": "success",
                                    "video_url": video_url,
                                    "retrieval_method": "fallback",
                                    "content_type": content_type,
                                    "content_length": content_length,
                                }
                            else:
                                logger.warning(
                                    f"[MODELSLAB V7 VIDEO] Fallback URL not a video: {content_type}"
                                )
                        else:
                            logger.warning(
                                f"[MODELSLAB V7 VIDEO] Fallback URL unavailable: HTTP {response.status}"
                            )

            except Exception as e:
                logger.warning(
                    f"[MODELSLAB V7 VIDEO] Fallback retrieval failed for {video_url}: {str(e)}"
                )
                continue

        logger.warning(f"[MODELSLAB V7 VIDEO] All fallback retrieval attempts failed")
        return None

    async def _poll_for_video_completion(
        self,
        fetch_result_url: str,
        future_links: Optional[List[str]] = None,
        max_poll_time: int = 120,  # 2 minutes maximum
        initial_delay: int = 5,
    ) -> Dict[str, Any]:
        """Poll the fetch_result URL until video is ready with fallback retrieval"""

        logger.info(
            f"[MODELSLAB V7 VIDEO] Starting polling for video completion: {fetch_result_url}"
        )

        current_delay = initial_delay
        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        while (asyncio.get_event_loop().time() - start_time) < max_poll_time:
            poll_count += 1
            logger.info(
                f"[MODELSLAB V7 VIDEO] Poll attempt {poll_count}, delay: {current_delay}s"
            )

            try:
                async with aiohttp.ClientSession() as session:
                    # ✅ FIX: Use POST instead of GET with API key payload
                    fetch_payload = {"key": self.api_key}

                    async with session.post(
                        fetch_result_url,
                        json=fetch_payload,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:

                        if response.status == 200:
                            result = await response.json()
                            status = result.get("status")

                            logger.info(
                                f"[MODELSLAB V7 VIDEO] Poll response status: {status}"
                            )

                            if status == "success":
                                video_url = self._extract_video_url(result)
                                if video_url:
                                    logger.info(
                                        f"[MODELSLAB V7 VIDEO] ✅ Video generation completed successfully"
                                    )
                                    return {
                                        "status": "success",
                                        "video_url": video_url,
                                        "poll_count": poll_count,
                                        "total_time": asyncio.get_event_loop().time()
                                        - start_time,
                                    }
                                else:
                                    logger.warning(
                                        f"[MODELSLAB V7 VIDEO] Success status but no video URL found"
                                    )
                                    # Try fallback retrieval if available
                                    if future_links:
                                        fallback_result = (
                                            await self._try_fallback_retrieval(
                                                future_links
                                            )
                                        )
                                        if fallback_result:
                                            return fallback_result

                            elif status == "processing":
                                # Continue polling with exponential backoff
                                eta = result.get("eta", 10)
                                logger.info(
                                    f"[MODELSLAB V7 VIDEO] Still processing, ETA: {eta}s"
                                )

                                # Use exponential backoff with max 10 seconds
                                current_delay = min(current_delay * 1.5, 10)
                                await asyncio.sleep(current_delay)
                                continue

                            else:
                                error_msg = result.get(
                                    "message",
                                    result.get("error", "Unknown error during polling"),
                                )
                                logger.error(
                                    f"[MODELSLAB V7 VIDEO] Polling error: {error_msg}"
                                )
                                # Try fallback retrieval if available
                                if future_links:
                                    fallback_result = (
                                        await self._try_fallback_retrieval(future_links)
                                    )
                                    if fallback_result:
                                        return fallback_result

                                return {
                                    "status": "error",
                                    "error": f"API generation failed: {error_msg}",
                                    "poll_count": poll_count,
                                    "error_type": "generation_failed",
                                }

                        else:
                            error_text = await response.text()
                            logger.error(
                                f"[MODELSLAB V7 VIDEO] HTTP {response.status} during polling: {error_text}"
                            )

                            # Try fallback retrieval if available
                            if future_links:
                                fallback_result = await self._try_fallback_retrieval(
                                    future_links
                                )
                                if fallback_result:
                                    return fallback_result

                            # For non-200 responses, wait longer before retry
                            await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"[MODELSLAB V7 VIDEO] Polling exception: {str(e)}")
                # Try fallback retrieval if available
                if future_links:
                    fallback_result = await self._try_fallback_retrieval(future_links)
                    if fallback_result:
                        return fallback_result
                await asyncio.sleep(current_delay)

        # Timeout reached
        timeout_msg = f"Video generation polling timed out after {max_poll_time} seconds ({poll_count} attempts)"
        logger.error(f"[MODELSLAB V7 VIDEO] {timeout_msg}")

        # Try fallback retrieval if available
        if future_links:
            fallback_result = await self._try_fallback_retrieval(future_links)
            if fallback_result:
                return fallback_result

        return {
            "status": "error",
            "error": timeout_msg,
            "poll_count": poll_count,
            "error_type": "timeout",
        }

    def _process_video_response(
        self, response: Dict[str, Any], operation_type: str
    ) -> Dict[str, Any]:
        """Process and standardize video API response"""

        try:
            response_status = response.get("status")

            # ✅ Handle "processing" status - this is a valid status, not an error
            if response_status == "processing":
                logger.info(
                    f"[MODELSLAB V7 VIDEO] Video generation in progress, status: processing"
                )

                # Extract video URL from available fields
                video_url = self._extract_video_url(response)
                fetch_result = response.get("fetch_result")
                eta = response.get("eta", 10)
                future_links = response.get("future_links", [])

                return {
                    "status": "processing",
                    "video_url": video_url,
                    "fetch_result": fetch_result,
                    "future_links": future_links,
                    "eta": eta,
                    "operation_type": operation_type,
                    "message": "Video generation in progress",
                }

            # ✅ Handle "success" status
            elif response_status == "success" or "output" in response:
                output_urls = response.get("output", [])

                if output_urls and len(output_urls) > 0:
                    video_url = output_urls[0]

                    # Handle different URL formats
                    if isinstance(video_url, dict):
                        video_url = video_url.get("url") or video_url.get("video_url")

                    # Extract metadata
                    meta = response.get("meta", {})

                    return {
                        "status": "success",
                        "output": output_urls,
                        "video_url": video_url,
                        "meta": meta,
                        "generation_time": response.get("generation_time", 0),
                        "model_used": response.get("model_id", "veo2"),
                        "operation_type": operation_type,
                    }
                else:
                    # Check if it's an async operation
                    request_id = response.get("id")
                    future_links = response.get("future_links", [])
                    if request_id:
                        return {
                            "status": "processing",
                            "request_id": request_id,
                            "future_links": future_links,
                            "operation_type": operation_type,
                            "message": "Video generation in progress",
                        }
                    else:
                        raise Exception("No video URL or request ID in response output")
            else:
                # Handle error response
                error_message = response.get(
                    "message", response.get("error", "Unknown error")
                )
                raise Exception(f"{operation_type} failed: {error_message}")

        except Exception as e:
            logger.error(f"[MODELSLAB V7 VIDEO] Response processing error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "operation_type": operation_type,
                "raw_response": response,
            }

    async def wait_for_completion(
        self,
        request_id: str,
        max_wait_time: int = 600,  # 10 minutes for video generation
        check_interval: int = 30,
    ) -> Dict[str, Any]:
        """Wait for async video generation to complete"""

        # ✅ V7 APIs might be synchronous, but keeping this for compatibility
        logger.info(
            f"[MODELSLAB V7 VIDEO] Waiting for completion of request: {request_id}"
        )

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
            try:
                # For V7, you might need to poll a status endpoint
                # This is a placeholder - adjust based on actual V7 API documentation
                await asyncio.sleep(check_interval)

                # If V7 APIs are synchronous, return immediately
                return {
                    "status": "completed",
                    "message": "V7 APIs appear to be synchronous",
                }

            except Exception as e:
                logger.error(f"[MODELSLAB V7 VIDEO] Error checking status: {e}")
                await asyncio.sleep(check_interval)

        raise Exception(f"Video generation timed out after {max_wait_time} seconds")

    def get_available_models(self) -> Dict[str, Dict[str, str]]:
        """Get available models for different video operations"""

        return {
            "video_generation": {
                "veo2": "Veo 2 (Recommended)",
                "veo2_pro": "Veo 2 Pro (Enhanced)",
                "seedance-i2v": "Seedance I2V (Fallback)",
            },
            "lip_sync": {
                "lipsync-2": "Lip Sync V2 (Latest)",
                "lipsync-1": "Lip Sync V1 (Legacy)",
            },
        }

    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get supported input/output formats"""

        return {
            "input_images": ["jpg", "jpeg", "png", "webp"],
            "input_videos": ["mp4", "mov", "avi"],
            "input_audio": ["mp3", "wav", "aac"],
            "output_videos": ["mp4"],
        }

    async def validate_inputs(
        self,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
        audio_url: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Validate input URLs and formats"""

        validation_results = {
            "image_valid": True,
            "video_valid": True,
            "audio_valid": True,
            "all_valid": True,
        }

        try:
            # Basic URL validation (could be enhanced with actual file checking)
            if image_url:
                if not any(
                    ext in image_url.lower()
                    for ext in [".jpg", ".jpeg", ".png", ".webp"]
                ):
                    validation_results["image_valid"] = False

            if video_url:
                if not any(
                    ext in video_url.lower() for ext in [".mp4", ".mov", ".avi"]
                ):
                    validation_results["video_valid"] = False

            if audio_url:
                if not any(
                    ext in audio_url.lower() for ext in [".mp3", ".wav", ".aac"]
                ):
                    validation_results["audio_valid"] = False

            validation_results["all_valid"] = all(
                [
                    validation_results["image_valid"],
                    validation_results["video_valid"],
                    validation_results["audio_valid"],
                ]
            )

        except Exception as e:
            logger.error(f"[VALIDATION] Error validating inputs: {e}")
            validation_results["all_valid"] = False

        return validation_results

    async def retry_video_retrieval(self, video_url: str) -> Dict[str, Any]:
        """Retry video retrieval from a URL with validation and error handling"""
        try:
            logger.info(
                f"[VIDEO RETRY] Attempting video retrieval from URL: {video_url}"
            )

            # Validate the URL format
            if not video_url or not isinstance(video_url, str):
                return {
                    "success": False,
                    "error": "Invalid video URL provided",
                    "retry_method": "validation_failed",
                }

            # Check if URL is accessible and contains a valid video
            async with aiohttp.ClientSession() as session:
                # First, try HEAD request to check availability
                try:
                    async with session.head(
                        video_url, timeout=aiohttp.ClientTimeout(total=30)
                    ) as head_response:

                        if head_response.status != 200:
                            return {
                                "success": False,
                                "error": f"Video URL not accessible (HTTP {head_response.status})",
                                "retry_method": "head_request_failed",
                            }

                        # Check content type
                        content_type = head_response.headers.get(
                            "content-type", ""
                        ).lower()
                        content_length = head_response.headers.get(
                            "content-length", "0"
                        )

                        # Validate it's a video file
                        if not any(
                            video_type in content_type
                            for video_type in ["video", "mp4", "mov", "avi"]
                        ):
                            logger.warning(
                                f"[VIDEO RETRY] Content type may not be video: {content_type}"
                            )
                            # Continue anyway as some video URLs might not have proper content-type

                except Exception as head_error:
                    logger.warning(
                        f"[VIDEO RETRY] HEAD request failed: {str(head_error)}"
                    )
                    # Continue with GET request as some servers don't support HEAD

                # Now try to download a small portion to validate it's actually a video
                try:
                    logger.info(f"[VIDEO RETRY] Validating video file content...")

                    async with session.get(
                        video_url,
                        timeout=aiohttp.ClientTimeout(total=60),
                        headers={
                            "Range": "bytes=0-1024"
                        },  # Download first 1KB to validate
                    ) as get_response:

                        if get_response.status not in [
                            200,
                            206,
                        ]:  # 206 is partial content
                            return {
                                "success": False,
                                "error": f"Video download failed (HTTP {get_response.status})",
                                "retry_method": "partial_download_failed",
                            }

                        # Read first few bytes to check for video file signature
                        video_data = await get_response.read()

                        # Check for common video file signatures
                        video_signatures = [
                            b"\x00\x00\x00\x18ftyp",  # MP4 signature
                            b"\x00\x00\x00\x1cftyp",  # MP4 signature variant
                            b"RIFF",  # AVI signature
                            b"\x1a\x45\xdf\xa3",  # WebM signature
                        ]

                        is_video_file = any(
                            video_data.startswith(sig) for sig in video_signatures
                        )

                        if not is_video_file:
                            logger.warning(
                                f"[VIDEO RETRY] File doesn't appear to be a video (no recognized signature)"
                            )
                            # Continue anyway as some video files might not have standard signatures

                except Exception as validation_error:
                    logger.warning(
                        f"[VIDEO RETRY] Video validation failed: {str(validation_error)}"
                    )
                    # Continue with full download attempt

                # Finally, attempt full download to get video duration
                try:
                    logger.info(f"[VIDEO RETRY] Attempting full video download...")

                    # Use a larger timeout for full video download
                    async with session.get(
                        video_url,
                        timeout=aiohttp.ClientTimeout(
                            total=300
                        ),  # 5 minutes for full download
                    ) as full_response:

                        if full_response.status != 200:
                            return {
                                "success": False,
                                "error": f"Full video download failed (HTTP {full_response.status})",
                                "retry_method": "full_download_failed",
                            }

                        # Get video metadata from headers
                        content_length = full_response.headers.get(
                            "content-length", "0"
                        )
                        content_type = full_response.headers.get("content-type", "")

                        # For now, we'll assume the video is valid if we can download it
                        # In a production system, you might want to use a video processing library
                        # to extract actual duration and validate the video file

                        logger.info(f"[VIDEO RETRY] ✅ Video retrieval successful")
                        logger.info(f"[VIDEO RETRY] Content-Type: {content_type}")
                        logger.info(
                            f"[VIDEO RETRY] Content-Length: {content_length} bytes"
                        )

                        return {
                            "success": True,
                            "video_url": video_url,
                            "content_type": content_type,
                            "content_length": content_length,
                            "duration": 0,  # Would need video processing to get actual duration
                            "retry_method": "direct_download",
                        }

                except Exception as download_error:
                    logger.error(
                        f"[VIDEO RETRY] Full video download failed: {str(download_error)}"
                    )
                    return {
                        "success": False,
                        "error": f"Video download failed: {str(download_error)}",
                        "retry_method": "download_exception",
                    }

        except Exception as e:
            logger.error(
                f"[VIDEO RETRY] Unexpected error during video retrieval: {str(e)}"
            )
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "retry_method": "unexpected_error",
            }
