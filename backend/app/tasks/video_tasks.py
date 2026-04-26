from app.tasks.celery_app import celery_app
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from celery.utils.log import get_task_logger

from app.api.services.video import VideoService
from app.core.database import async_session, engine
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import bindparam, text
from app.videos.models import VideoGeneration, VideoSegment
from app.subscriptions.models import UserSubscription
from app.core.model_config import get_model_config, ModelConfig
import json
import subprocess
import os
import requests
import tempfile
import uuid
import ipaddress
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlunparse
from app.core.services.file import FileService
from app.core.config import settings

from app.core.services.modelslab_v7_video import ModelsLabV7VideoService
from app.videos.association_integrity import (
    extract_shot_selections,
    dedupe_scene_videos,
    resolve_scene_identity,
)

logger = get_task_logger(__name__)


_LOCAL_MINIO_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "minio", "host.docker.internal"}
_PROVIDER_MEDIA_PUBLIC_URL_ENV_NAMES = (
    "MODELSLAB_MEDIA_PUBLIC_URL",
    "MINIO_PROVIDER_PUBLIC_URL",
    "PUBLIC_MINIO_URL",
    "MINIO_EXTERNAL_URL",
    "MEDIA_PUBLIC_URL",
    "PUBLIC_MEDIA_URL",
    "S3_PUBLIC_URL",
    "CDN_BASE_URL",
)


class ProviderMediaUrlConfigurationError(ValueError):
    """Raised before provider calls when media URLs are not externally fetchable."""


def _replace_url_origin(url: str, target_origin: Optional[str]) -> str:
    """Return url with scheme/netloc from target_origin, preserving path/params/query."""
    if not url or not target_origin:
        return url

    parsed_url = urlparse(url)
    parsed_target = urlparse(target_origin)
    if not parsed_url.scheme or not parsed_url.netloc or not parsed_target.scheme or not parsed_target.netloc:
        return url

    return urlunparse(
        parsed_url._replace(scheme=parsed_target.scheme, netloc=parsed_target.netloc)
    )


def _is_provider_unsafe_host(host: Optional[str]) -> bool:
    """Return True for hosts external providers cannot fetch (local/docker/private IPs)."""
    if not host:
        return True

    host = host.lower()
    if host in _LOCAL_MINIO_HOSTS or host.endswith(".local"):
        return True

    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified
    except ValueError:
        return False


def _is_ip_literal(host: Optional[str]) -> bool:
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_provider_unsafe_url(url: Optional[str]) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    # ModelsLab may return "invalid accessible without redirect/auth" for raw
    # IP-origin media even when the IP is publicly reachable from our network.
    if _is_ip_literal(parsed.hostname):
        return True
    return _is_provider_unsafe_host(parsed.hostname)


def _is_local_minio_url(url: str) -> bool:
    """Detect MinIO URLs that are only reachable from browser/dev/container context."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False

    host = parsed.hostname.lower()
    if _is_provider_unsafe_host(host):
        return True

    for configured in (settings.MINIO_PUBLIC_URL, settings.MINIO_ENDPOINT):
        configured_host = urlparse(configured or "").hostname
        if configured_host and host == configured_host.lower() and _is_provider_unsafe_host(configured_host):
            return True
    return False


def _redact_media_url_for_log(url: Optional[str]) -> Optional[str]:
    """Log media URL origin/path only; drop query strings that may contain signatures."""
    if not url:
        return url
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    return urlunparse(parsed._replace(query="", fragment=""))


def _replace_url_base(url: str, target_base: Optional[str]) -> str:
    """Rewrite a media URL to target_base, preserving bucket/object path and query."""
    if not url or not target_base:
        return url

    parsed_url = urlparse(url)
    parsed_target = urlparse(target_base)
    if not parsed_url.scheme or not parsed_url.netloc or not parsed_target.scheme or not parsed_target.netloc:
        return url

    target_prefix = (parsed_target.path or "").rstrip("/")
    source_path = parsed_url.path if parsed_url.path.startswith("/") else f"/{parsed_url.path}"
    new_path = f"{target_prefix}{source_path}" if target_prefix else source_path
    return urlunparse(
        parsed_url._replace(scheme=parsed_target.scheme, netloc=parsed_target.netloc, path=new_path)
    )


def _valid_external_media_base(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    if _is_provider_unsafe_url(value):
        return None
    return value.rstrip("/")


def _provider_media_public_base() -> Optional[str]:
    """Resolve an externally reachable base URL for provider-bound MinIO media."""
    for configured in (
        getattr(settings, "MODELSLAB_MEDIA_PUBLIC_URL", None),
        getattr(settings, "MINIO_PROVIDER_PUBLIC_URL", None),
    ):
        valid = _valid_external_media_base(configured)
        if valid:
            return valid

    minio_public = getattr(settings, "MINIO_PUBLIC_URL", None)
    if minio_public and not _is_provider_unsafe_url(minio_public):
        valid = _valid_external_media_base(minio_public)
        if valid:
            return valid

    # Last-resort compatibility for deployments that already expose a generic
    # media/CDN env var but have not yet moved it into typed settings.
    for env_name in _PROVIDER_MEDIA_PUBLIC_URL_ENV_NAMES:
        valid = _valid_external_media_base(os.getenv(env_name))
        if valid:
            return valid
    return None


def normalize_media_url_for_provider(url: Optional[str]) -> Optional[str]:
    """Normalize stored media URLs before sending them to external providers.

    Celery often stores MinIO objects as http://localhost:9000/... URLs. Those
    work from the dev browser/container network, but ModelsLab cannot fetch
    localhost/minio/private URLs from its infrastructure. Provider-bound media
    must therefore be rewritten to an explicitly configured external base, or
    fail before spending provider credits.
    """
    if not url:
        return url
    if not _is_provider_unsafe_url(url):
        return url

    provider_base = _provider_media_public_base()
    if not provider_base:
        raise ProviderMediaUrlConfigurationError(
            "Provider media URL is not externally reachable. Configure MODELSLAB_MEDIA_PUBLIC_URL "
            "or MINIO_PROVIDER_PUBLIC_URL to an HTTPS public/CDN/R2/S3 base (without bucket name); "
            "raw http IP, localhost, minio, and private media URLs are refused before ModelsLab calls: "
            f"{_redact_media_url_for_log(url)}"
        )

    provider_url = _replace_url_base(url, provider_base)
    if _is_provider_unsafe_url(provider_url):
        raise ProviderMediaUrlConfigurationError(
            "Resolved provider media URL is still local/private; refusing to send media to ModelsLab: "
            f"{_redact_media_url_for_log(provider_url)}"
        )
    return provider_url


def normalize_media_url_for_internal_access(url: Optional[str]) -> Optional[str]:
    """Normalize media URLs for backend/container probes and downloads.

    Internal probes (ffmpeg/requests from Celery) should use MINIO_ENDPOINT when
    a URL is a local MinIO public URL, because localhost points at the worker
    container rather than the MinIO service.
    """
    if not url or not _is_local_minio_url(url):
        return url
    return _replace_url_origin(url, settings.MINIO_ENDPOINT)


def log_provider_media_url_normalization(kind: str, original_url: Optional[str], provider_url: Optional[str]) -> None:
    """Diagnostic log for provider media URLs without leaking signed query data."""
    if original_url != provider_url:
        msg = (
            f"[MEDIA URL NORMALIZE] {kind}: original={_redact_media_url_for_log(original_url)} "
            f"provider={_redact_media_url_for_log(provider_url)}"
        )
        logger.warning(msg)
        print(msg)


_PROVIDER_CDN_METADATA_KEYS = (
    "provider_image_url",
    "provider_audio_url",
    "provider_cdn_url",
    "provider_url",
    "modelslab_cdn_url",
    "modelslab_url",
    "original_cdn_url",
    "cdn_url",
)
_PROVIDER_CDN_TIMESTAMP_KEYS = (
    "provider_url_created_at",
    "provider_image_url_created_at",
    "provider_audio_url_created_at",
    "original_cdn_url_created_at",
    "cdn_created_at",
    "created_at",
)
_PROVIDER_CDN_MAX_AGE = timedelta(days=13)


def _metadata_dict(value: Any) -> Dict[str, Any]:
    """Return metadata as a dict, tolerating legacy JSON-string metadata."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return {}


def _parse_provider_timestamp(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fresh_provider_timestamp(container: Dict[str, Any]) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    for key in _PROVIDER_CDN_TIMESTAMP_KEYS:
        parsed = _parse_provider_timestamp(container.get(key))
        if parsed and now - parsed < _PROVIDER_CDN_MAX_AGE:
            return parsed
    return None


def _candidate_provider_cdn_urls(media_item: Optional[Dict[str, Any]]) -> List[Tuple[str, datetime]]:
    """Extract fresh preserved provider/CDN media URLs from an image/audio/video item."""
    if not media_item:
        return []

    containers: List[Dict[str, Any]] = [media_item]
    for meta_key in ("meta", "metadata", "image_metadata", "video_metadata", "audio_metadata"):
        meta = _metadata_dict(media_item.get(meta_key))
        if meta:
            containers.append(meta)

    urls: List[Tuple[str, datetime]] = []
    seen = set()
    for container in containers:
        fresh_at = _fresh_provider_timestamp(container)
        if not fresh_at:
            continue
        for key in _PROVIDER_CDN_METADATA_KEYS:
            value = container.get(key)
            if isinstance(value, str) and value.strip() and value.strip() not in seen:
                seen.add(value.strip())
                urls.append((value.strip(), fresh_at))
    return urls


def select_provider_media_source(
    canonical_url: Optional[str],
    media_item: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Prefer a preserved fresh provider CDN URL, then fall back to canonical URL.

    Provider CDN links expire; only reuse preserved links with a creation
    timestamp newer than roughly 13 days. Unsafe/raw-IP candidates are skipped
    so the canonical fallback can still go through existing normalization and
    blocker handling.
    """
    for candidate, _created_at in _candidate_provider_cdn_urls(media_item):
        if not _is_provider_unsafe_url(candidate):
            return candidate
    return canonical_url


def _provider_metadata_subset(metadata: Any) -> Dict[str, Any]:
    """Return only provider/CDN URL metadata needed at the ModelsLab boundary."""
    meta = _metadata_dict(metadata)
    return {
        key: value
        for key, value in meta.items()
        if key in _PROVIDER_CDN_METADATA_KEYS or key in _PROVIDER_CDN_TIMESTAMP_KEYS
    }


def _merge_provider_metadata(media_item: Dict[str, Any], metadata: Any, metadata_key: str) -> bool:
    """Promote persisted provider CDN metadata onto a task media snapshot.

    The product path can snapshot selected audio/image rows with canonical
    localhost MinIO URLs while omitting audio_metadata/meta. Rehydrating only
    provider/CDN fields preserves fail-closed canonical fallback behavior while
    allowing verified CDN URLs to be selected before provider normalization.
    """
    if not isinstance(media_item, dict):
        return False
    provider_meta = _provider_metadata_subset(metadata)
    if not provider_meta:
        return False

    nested = _metadata_dict(media_item.get(metadata_key))
    changed = False
    for key, value in provider_meta.items():
        if value is None or value == "":
            continue
        if nested.get(key) != value:
            nested[key] = value
            changed = True
        if media_item.get(key) in (None, ""):
            media_item[key] = value
            changed = True
    if changed:
        media_item[metadata_key] = nested
    return changed


def _result_mappings(result: Any) -> List[Dict[str, Any]]:
    try:
        mappings = result.mappings()
        return [dict(row) for row in mappings.all()]
    except Exception:
        pass
    try:
        rows = result.fetchall()
    except Exception:
        rows = []
    mapped = []
    for row in rows:
        if isinstance(row, dict):
            mapped.append(row)
        elif hasattr(row, "_mapping"):
            mapped.append(dict(row._mapping))
    return mapped


async def rehydrate_media_provider_metadata(
    session: Optional[AsyncSession],
    *,
    audio_files: Optional[Dict[str, Any]] = None,
    image_data: Optional[Dict[str, Any]] = None,
    selected_audio_ids: Optional[List[str]] = None,
) -> None:
    """Rehydrate provider CDN metadata for selected/snapshotted media rows.

    This intentionally does not replace canonical audio_url/image_url values.
    Provider URLs are consumed later by select_provider_media_source(), where
    unsafe localhost/raw-IP fallbacks still fail closed before ModelsLab.
    """
    if not session:
        return

    audio_items_by_id: Dict[str, List[Dict[str, Any]]] = {}
    if audio_files:
        selected_set = {str(value) for value in (selected_audio_ids or []) if value}
        for audio_type in ("characters", "narrator", "sound_effects", "background_music"):
            for item in audio_files.get(audio_type, []) or []:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                item_id = str(item.get("id"))
                if selected_set and item_id not in selected_set:
                    continue
                audio_items_by_id.setdefault(item_id, []).append(item)

    image_items_by_id: Dict[str, List[Dict[str, Any]]] = {}
    if image_data:
        candidate_images = list(image_data.get("scene_images", []) or [])
        images_container = image_data.get("images", {}) or {}
        candidate_images.extend(images_container.get("scene_images", []) or [])
        for item in candidate_images:
            if isinstance(item, dict) and item.get("id"):
                image_items_by_id.setdefault(str(item.get("id")), []).append(item)

    try:
        if audio_items_by_id:
            result = await session.execute(
                text(
                    """
                    SELECT id::text AS id, audio_metadata
                    FROM audio_generations
                    WHERE id::text IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": list(audio_items_by_id.keys())},
            )
            for row in _result_mappings(result):
                for item in audio_items_by_id.get(str(row.get("id")), []):
                    if _merge_provider_metadata(item, row.get("audio_metadata"), "audio_metadata"):
                        logger.warning(
                            "[KAN-86] Rehydrated provider audio metadata for selected audio id=%s",
                            row.get("id"),
                        )

        if image_items_by_id:
            result = await session.execute(
                text(
                    """
                    SELECT id::text AS id, meta
                    FROM image_generations
                    WHERE id::text IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": list(image_items_by_id.keys())},
            )
            for row in _result_mappings(result):
                for item in image_items_by_id.get(str(row.get("id")), []):
                    if _merge_provider_metadata(item, row.get("meta"), "meta"):
                        logger.warning(
                            "[KAN-86] Rehydrated provider image metadata for image id=%s",
                            row.get("id"),
                        )
    except Exception as exc:
        logger.warning("[KAN-86] Provider media metadata rehydrate skipped: %s", exc)


def _safe_uuid_string(value: Optional[str]) -> Optional[str]:
    """Return a DB-safe UUID string or None for optional UUID FK columns."""
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _build_provider_attempt_diagnostic(
    *,
    scene_id: str,
    scene_number: int,
    original_image_url: Optional[str],
    provider_image_url: Optional[str],
    original_audio_url: Optional[str],
    provider_audio_url: Optional[str],
    model: str,
    status: str,
    provider_error: Optional[str] = None,
    exception: Optional[str] = None,
    canonical_image_url: Optional[str] = None,
    canonical_audio_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Concise non-secret provider boundary diagnostics for DB/task metadata."""
    diagnostic = {
        "scene_id": scene_id,
        "scene_number": scene_number,
        "original_image_url": _redact_media_url_for_log(original_image_url),
        "provider_image_url": _redact_media_url_for_log(provider_image_url),
        "original_audio_url": _redact_media_url_for_log(original_audio_url),
        "provider_audio_url": _redact_media_url_for_log(provider_audio_url),
        "canonical_image_url": _redact_media_url_for_log(canonical_image_url),
        "canonical_audio_url": _redact_media_url_for_log(canonical_audio_url),
        "model": model,
        "status": status,
    }
    if provider_error:
        diagnostic["provider_error"] = str(provider_error)[:500]
    if exception:
        diagnostic["exception"] = str(exception)[:500]
    return diagnostic


async def _persist_provider_attempt_diagnostic(
    session: AsyncSession,
    video_gen_id: str,
    diagnostic: Dict[str, Any],
) -> None:
    """Append provider attempt diagnostics to task_meta without breaking generation flow."""
    if not session or not diagnostic:
        return
    try:
        await session.execute(
            text(
                """
                UPDATE video_generations
                SET task_meta = COALESCE(task_meta, '{}'::jsonb) || jsonb_build_object(
                    'provider_attempts',
                    COALESCE(task_meta->'provider_attempts', '[]'::jsonb) || CAST(:diagnostic AS jsonb)
                )
                WHERE id = :id
                """
            ),
            {"id": video_gen_id, "diagnostic": json.dumps([diagnostic])},
        )
        await session.commit()
    except Exception as diag_err:
        logger.error(
            "[SCENE VIDEOS V7] Failed to persist provider diagnostics for %s: %s",
            video_gen_id,
            diag_err,
        )
        try:
            await session.rollback()
        except Exception:
            pass


# Removed image generation logic


# Removed scene image generation logic


async def extract_scene_dialogue_and_generate_audio(
    video_gen_id: str,
    scene_id: str,
    scene_description: str,
    script_data: Dict[str, Any],
    user_id: str = None,
    session: AsyncSession = None,
) -> Dict[str, Any]:
    """Extract dialogue for a specific scene and generate audio"""

    try:
        # Get the full script from script_data
        script = script_data.get("script", "")
        if not script:
            print(
                f"[DIALOGUE EXTRACTION] No script found for video generation {video_gen_id}"
            )
            return {"dialogue_audio": []}

        # Get scene descriptions for context
        scene_descriptions = script_data.get("scene_descriptions", [])

        # Initialize video service for dialogue extraction
        if not session:
            raise Exception(
                "Session required for extract_scene_dialogue_and_generate_audio"
            )
        video_service = VideoService(session)

        # Extract dialogue per scene
        dialogue_data = await video_service.extract_dialogue_per_scene(
            script=script, scene_descriptions=scene_descriptions, user_id=user_id
        )

        # Get dialogue for this specific scene
        scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1
        scene_dialogues = dialogue_data.get("scene_dialogues", {}).get(scene_number, [])
        scene_audio_files = dialogue_data.get("scene_audio_files", {}).get(
            scene_number, []
        )

        print(
            f"[DIALOGUE EXTRACTION] Scene {scene_number}: {len(scene_dialogues)} dialogues, {len(scene_audio_files)} audio files"
        )

        # Store dialogue audio in database for tracking
        # Store dialogue audio in database for tracking
        for audio_file in scene_audio_files:
            try:
                # Using raw SQL for insert if VideoSegment model usage is complex or to match existing pattern
                # But better to use model if possible.
                # Let's use raw SQL insert for now to be safe with existing schema

                insert_query = text(
                    """
                    INSERT INTO video_segments (
                        video_generation_id, scene_id, segment_index, scene_description,
                        audio_url, character_name, dialogue_text, generation_method,
                        status, processing_service, metadata
                    ) VALUES (
                        :video_generation_id, :scene_id, :segment_index, :scene_description,
                        :audio_url, :character_name, :dialogue_text, :generation_method,
                        :status, :processing_service, :metadata
                    )
                """
                )

                await session.execute(
                    insert_query,
                    {
                        "video_generation_id": video_gen_id,
                        "scene_id": scene_id,
                        "segment_index": scene_number,
                        "scene_description": scene_description,
                        "audio_url": audio_file.get("audio_url"),
                        "character_name": audio_file.get("character"),
                        "dialogue_text": audio_file.get("text"),
                        "generation_method": "character_dialogue_audio",
                        "status": "completed",
                        "processing_service": "elevenlabs",
                        "metadata": json.dumps(
                            {
                                "character_profile": audio_file.get(
                                    "character_profile", {}
                                ),
                                "scene_number": scene_number,
                                "dialogue_type": "character_voice",
                            }
                        ),
                    },
                )
                await session.commit()
            except Exception as db_error:
                print(f"[DIALOGUE EXTRACTION] Error storing dialogue audio: {db_error}")

        return {
            "dialogue_audio": scene_audio_files,
            "dialogue_count": len(scene_dialogues),
            "audio_count": len(scene_audio_files),
            "scene_number": scene_number,
        }

    except Exception as e:
        print(
            f"[DIALOGUE EXTRACTION] Error extracting dialogue for scene {scene_id}: {e}"
        )
        return {"dialogue_audio": [], "error": str(e)}


async def extract_last_frame(
    video_url: str, user_id: Optional[str] = None
) -> Optional[str]:
    """
    Extract the last frame from a video for use as the starting image of the next scene.
    This helps maintain visual continuity between scenes.

    Args:
        video_url: URL of the video to extract frame from
        user_id: Optional user ID for storage organization

    Returns:
        URL of the extracted frame image, or None if extraction fails
    """
    import tempfile
    import subprocess
    import os
    import httpx
    from app.core.services.storage import get_storage_service

    try:
        print(f"[LAST FRAME] Extracting last frame from video: {video_url[:50]}...")

        # Download video to temp file
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(video_url)
            if response.status_code != 200:
                print(f"[LAST FRAME] Failed to download video: {response.status_code}")
                return None

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as video_file:
            video_file.write(response.content)
            video_path = video_file.name

        frame_path = video_path.replace(".mp4", "_last_frame.jpg")

        try:
            # Extract last frame using ffmpeg
            # First, get video duration
            probe_cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                video_path,
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.stdout.strip() else 5.0

            # Extract frame at last second
            seek_time = max(0, duration - 0.1)  # 0.1 seconds before end
            extract_cmd = [
                "ffmpeg",
                "-y",
                "-ss",
                str(seek_time),
                "-i",
                video_path,
                "-vframes",
                "1",
                "-q:v",
                "2",
                frame_path,
            ]
            subprocess.run(extract_cmd, capture_output=True, check=True)

            if not os.path.exists(frame_path):
                print("[LAST FRAME] Frame extraction failed - no output file")
                return None

            # Upload to storage
            storage_service = get_storage_service()

            # Generate unique filename
            import uuid as uuid_lib

            frame_filename = f"frames/{user_id or 'system'}/last_frame_{uuid_lib.uuid4().hex[:8]}.jpg"

            # S3StorageService.upload expects a file path, not in-memory bytes
            frame_url = await storage_service.upload(
                frame_path,
                file_path=frame_filename,
                content_type="image/jpeg",
            )

            print(f"[LAST FRAME] ✅ Extracted and uploaded frame: {frame_url[:50]}...")
            return frame_url

        finally:
            # Clean up temp files
            if os.path.exists(video_path):
                os.unlink(video_path)
            if os.path.exists(frame_path):
                os.unlink(frame_path)

    except Exception as e:
        print(f"[LAST FRAME] ❌ Error extracting frame: {e}")
        return None


async def upscale_frame(
    image_url: str, user_tier: str = "BASIC", user_id: Optional[str] = None
) -> str:
    """
    Upscale an extracted frame before using it as video input.
    Uses tier-based upscaling models from UPSCALE_MODEL_CONFIG.

    Args:
        image_url: URL of the image to upscale
        user_tier: User's subscription tier for model selection
        user_id: Optional user ID for storage organization

    Returns:
        URL of the upscaled image, or original URL if upscaling fails
    """
    from app.core.model_config import UPSCALE_MODEL_CONFIG, ModelTier

    try:
        print(f"[UPSCALE] Upscaling frame for tier: {user_tier}")

        # Get model config based on tier
        tier_enum = ModelTier[user_tier.upper()] if user_tier else ModelTier.BASIC
        upscale_config = UPSCALE_MODEL_CONFIG.get(
            tier_enum, UPSCALE_MODEL_CONFIG[ModelTier.BASIC]
        )
        model_id = upscale_config.primary

        # Use ModelsLab upscaling service
        from app.core.services.modelslab_upscale import ModelsLabUpscaleService

        upscale_service = ModelsLabUpscaleService()
        result = await upscale_service.upscale_image(
            image_url=image_url,
            model_id=model_id,
            scale=2,  # 2x upscaling is usually sufficient
        )

        if result.get("status") == "success" and result.get("upscaled_url"):
            print(f"[UPSCALE] ✅ Frame upscaled successfully")
            return result["upscaled_url"]
        else:
            print(
                f"[UPSCALE] ⚠️ Upscaling failed, using original: {result.get('error')}"
            )
            return image_url

    except Exception as e:
        print(f"[UPSCALE] ❌ Error upscaling frame: {e}, using original")
        return image_url


def find_scene_audio(
    scene_id: str,
    audio_files: Dict[str, Any],
    script_style: str = None,
    selected_audio_ids: List[str] = None,
) -> Optional[Dict[str, Any]]:
    """Find audio for a scene without cross-scene fallback.

    Priority: explicit selection for this scene > exact scene match (character > narrator > any type).
    KAN-86: never fall back to unrelated audio with a URL.
    """

    scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1

    def _audio_scene_values(audio: Dict[str, Any]) -> set[int]:
        values = set()
        for key in ("scene_number", "scene"):
            try:
                raw_scene = audio.get(key)
                if raw_scene is None:
                    continue
                numeric_scene = int(raw_scene)
            except (TypeError, ValueError):
                continue
            # Scene 0 is an invalid provider/task scene; legacy route payloads
            # used 0-based metadata for scene 1. Normalize that explicit value.
            values.add(1 if numeric_scene == 0 else numeric_scene)
        return values

    def _audio_matches_scene(audio: Dict[str, Any]) -> bool:
        return scene_number in _audio_scene_values(audio)

    # Collect all audio across all types
    all_audio = []
    for audio_type in ["characters", "narrator", "sound_effects", "background_music"]:
        all_audio.extend(audio_files.get(audio_type, []))

    print(
        f"[FIND AUDIO] Looking for audio for {scene_id} (scene_number={scene_number}), total audio files: {len(all_audio)}"
    )

    # Priority 0: Explicitly selected audio. If selected_audio_ids are supplied,
    # they are an allow-list for this render request; do not silently fall back to
    # any other audio when the selected IDs are wrong-scene or unusable.
    if selected_audio_ids:
        selected_id_set = {str(audio_id) for audio_id in selected_audio_ids}
        for audio in all_audio:
            if str(audio.get("id")) in selected_id_set and audio.get("audio_url"):
                if _audio_matches_scene(audio):
                    print(
                        f"[FIND AUDIO] Found EXPLICITLY selected audio for {scene_id}"
                    )
                    return audio
        print(
            f"[FIND AUDIO] Selected audio IDs did not include usable scene-matched audio for {scene_id}; refusing fallback"
        )
        return None

    # Priority 1: Exact scene match in character audio
    for audio in audio_files.get("characters", []):
        if _audio_matches_scene(audio) and audio.get("audio_url"):
            print(f"[FIND AUDIO] Found character audio for {scene_id}")
            return audio

    # Priority 2: Exact scene match in narrator audio
    for audio in audio_files.get("narrator", []):
        if _audio_matches_scene(audio) and audio.get("audio_url"):
            print(f"[FIND AUDIO] Found narrator audio for {scene_id}")
            return audio

    # Priority 3: Exact scene match in any type
    for audio in all_audio:
        if _audio_matches_scene(audio) and audio.get("audio_url"):
            print(
                f"[FIND AUDIO] Found audio (type={audio.get('audio_type')}) for {scene_id}"
            )
            return audio

    print(f"[FIND AUDIO] No usable scene-matched audio found for {scene_id}; refusing cross-scene fallback")
    return None


def normalize_target_scene_numbers(value: Any) -> List[int]:
    """Return a de-duped ordered list of positive 1-based scene numbers."""
    if value is None:
        return []
    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    scene_numbers: List[int] = []
    seen = set()
    for raw in raw_values:
        try:
            scene_number = int(raw)
        except (TypeError, ValueError):
            continue
        if scene_number <= 0 or scene_number in seen:
            continue
        scene_numbers.append(scene_number)
        seen.add(scene_number)
    return scene_numbers


def select_scene_assets_for_targets(
    *,
    target_scene_numbers: List[int],
    original_scene_descriptions: List[Any],
    scene_image_map: Dict[int, Dict[int, Dict[str, Any]]],
    pre_gen_scene_images: List[Dict[str, Any]],
    pre_gen_character_images: List[Dict[str, Any]],
    selected_shots: Optional[List[Any]] = None,
) -> tuple[List[Any], List[int], List[Optional[Dict[str, Any]]]]:
    """Select descriptions/images in the exact target scene order.

    KAN-86: persisted target_scene_numbers are the durable scope. If selected
    shot parsing is unavailable later, this helper still prevents falling back
    to all scenes and maps images by scene_number instead of raw DB order.
    """
    shot_by_scene: Dict[int, int] = {}
    for selection in selected_shots or []:
        if selection.scene_number not in shot_by_scene:
            shot_by_scene[selection.scene_number] = selection.shot_index

    target_descriptions: List[Any] = []
    final_scene_images: List[Optional[Dict[str, Any]]] = []

    for scene_num in target_scene_numbers:
        desc_index = scene_num - 1
        if 0 <= desc_index < len(original_scene_descriptions):
            target_descriptions.append(original_scene_descriptions[desc_index])
        else:
            target_descriptions.append(f"Scene {scene_num}")

        found_image = None
        shot_idx = shot_by_scene.get(scene_num, 0)
        if scene_num in scene_image_map:
            if shot_idx in scene_image_map[scene_num]:
                found_image = scene_image_map[scene_num][shot_idx]
            elif 0 in scene_image_map[scene_num]:
                found_image = scene_image_map[scene_num][0]
            elif scene_image_map[scene_num]:
                found_image = next(iter(scene_image_map[scene_num].values()))

        if found_image is None and not scene_image_map and pre_gen_scene_images:
            # Legacy fallback only when images have no usable scene_number map.
            fallback_index = desc_index if desc_index >= 0 else 0
            if fallback_index < len(pre_gen_scene_images):
                found_image = pre_gen_scene_images[fallback_index]

        if found_image is None and pre_gen_character_images:
            found_image = pre_gen_character_images[(scene_num - 1) % len(pre_gen_character_images)]

        final_scene_images.append(found_image)

    return target_descriptions, target_scene_numbers, final_scene_images


async def update_pipeline_step(
    video_generation_id: str,
    step_name: str,
    status: str,
    error_message: str = None,
    session: AsyncSession = None,
):
    """Update pipeline step status"""
    try:
        if not session:
            print(
                f"[PIPELINE ERROR] No session provided for update_pipeline_step {step_name}"
            )
            return

        update_data = {
            "status": status,
            "video_generation_id": video_generation_id,
            "step_name": step_name,
        }

        set_clauses = ["status = :status"]

        if status == "processing":
            set_clauses.append("started_at = NOW()")
        elif status in ["completed", "failed"]:
            set_clauses.append("completed_at = NOW()")

        if error_message:
            set_clauses.append("error_message = :error_message")
            update_data["error_message"] = error_message

        set_clause_str = ", ".join(set_clauses)

        update_query = text(
            f"""
            UPDATE pipeline_steps 
            SET {set_clause_str}
            WHERE video_generation_id = :video_generation_id AND step_name = :step_name
        """
        )

        await session.execute(update_query, update_data)
        await session.commit()

        print(f"[PIPELINE] Updated step {step_name} to {status}")

    except Exception as e:
        print(f"[PIPELINE] Error updating step {step_name}: {e}")
        if session:
            try:
                await session.rollback()
            except Exception:
                pass


@celery_app.task(bind=True)
def generate_all_videos_for_generation(self, video_generation_id: str):
    """Main task to generate all videos for a video generation with automatic retry"""
    return asyncio.run(async_generate_all_videos_for_generation(video_generation_id))


async def async_generate_all_videos_for_generation(video_generation_id: str):
    """Async implementation of video generation task"""
    async with async_session() as session:
        try:
            print(
                f"[VIDEO GENERATION] Starting video generation for: {video_generation_id}"
            )

            # ✅ Update pipeline step to processing
            await update_pipeline_step(
                video_generation_id, "video_generation", "processing", session=session
            )

            # Get video generation data
            # Using raw SQL
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            # Convert to dict for easier access (and compatibility with existing code)
            video_gen = dict(video_gen_record)
            user_id = video_gen.get("user_id")

            # Update status and initialize retry tracking
            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'generating_video',
                    retry_count = 0,
                    can_resume = true
                WHERE id = :id
            """
            )
            await session.execute(update_query, {"id": video_generation_id})
            await session.commit()

            # Get user subscription tier for model config
            user_tier = "free"
            async with session.begin_nested():  # Use nested transaction or just query
                # Re-using session within transaction is fine
                pass

            # Simple query for subscription
            sub_query = text(
                "SELECT tier FROM user_subscriptions WHERE user_id = :user_id"
            )
            sub_result = await session.execute(sub_query, {"user_id": user_id})
            sub_record = sub_result.first()
            if sub_record:
                user_tier = sub_record[0]

            # Get Video Model Config
            video_config = get_model_config("video", user_tier)
            print(f"[VIDEO CONFIG] Tier: {user_tier}, Config: {video_config}")

            # Get script data and generated assets
            script_data = video_gen.get("script_data", {})
            audio_files = video_gen.get("audio_files", {})
            image_data = video_gen.get("image_data", {})

            scene_descriptions = script_data.get("scene_descriptions", [])
            characters = script_data.get("characters", [])
            video_style = script_data.get("video_style", "realistic")

            # Read task_meta for selection filters
            task_meta = video_gen.get("task_meta", {}) or {}
            print(f"[VIDEO GENERATION] task_meta keys: {list(task_meta.keys())}")
            if task_meta.get("selected_shot_ids"):
                print(
                    f"[VIDEO GENERATION] selected_shot_ids: {task_meta['selected_shot_ids']}"
                )
            if task_meta.get("selected_audio_ids"):
                print(
                    f"[VIDEO GENERATION] selected_audio_ids: {task_meta['selected_audio_ids']}"
                )

            # Save original scene_descriptions for index-safe lookups
            original_scene_descriptions = list(scene_descriptions)

            print(f"[VIDEO GENERATION] Processing:")
            print(f"- Scenes: {len(scene_descriptions)}")
            print(f"- Characters: {len(characters)}")
            print(f"- Video Style: {video_style}")

            # Detailed audio logging
            narrator_count = len(audio_files.get("narrator", []))
            character_count = len(audio_files.get("characters", []))
            sfx_count = len(audio_files.get("sound_effects", []))
            music_count = len(audio_files.get("background_music", []))
            print(
                f"- Audio Files: narrator={narrator_count}, characters={character_count}, sfx={sfx_count}, music={music_count}"
            )
            for audio_type, items in audio_files.items():
                for item in items:
                    print(
                        f"  [{audio_type}] id={item.get('id', 'N/A')}, scene={item.get('scene_number', '?')}, url={'yes' if item.get('url') or item.get('audio_url') else 'NO'}"
                    )

            # Log image data and prompts
            img_images = image_data.get("images", {})
            scene_imgs = img_images.get(
                "scene_images", image_data.get("scene_images", [])
            )
            print(f"- Scene Images: {len(scene_imgs)}")
            for img in scene_imgs:
                prompt_preview = (img.get("prompt", "") or "")[:80]
                print(
                    f"  [scene] id={img.get('id', 'N/A')}, scene_num={img.get('scene_number', '?')}, prompt={prompt_preview!r}"
                )

            # Use pre-generated scene images directly from image_data
            # (images were already stored by routes.py from ImageGeneration records)
            img_images = image_data.get("images", {})
            pre_gen_scene_images = img_images.get("scene_images", [])
            pre_gen_character_images = img_images.get("character_images", [])

            print(
                f"[IMAGE SELECTION] Pre-generated scene images: {len(pre_gen_scene_images)}"
            )
            print(
                f"[IMAGE SELECTION] Pre-generated character images: {len(pre_gen_character_images)}"
            )

            # Build scene_images list from pre-generated images
            # Map by scene_number for deterministic lookup.
            # Structure: {scene_number: {shot_index: image_data}}
            scene_image_map: Dict[int, Dict[int, Dict[str, Any]]] = {}
            for img in pre_gen_scene_images:
                try:
                    scene_num = int(img.get("scene_number", 0) or 0)
                except (TypeError, ValueError):
                    scene_num = 0
                try:
                    shot_idx = int(img.get("shot_index", 0) or 0)
                except (TypeError, ValueError):
                    shot_idx = 0
                if scene_num <= 0:
                    continue

                if scene_num not in scene_image_map:
                    scene_image_map[scene_num] = {}

                # Store image by shot_index. If duplicates exist, last one wins.
                scene_image_map[scene_num][shot_idx] = img

            print(f"[IMAGE MAPPING] Map keys: {list(scene_image_map.keys())}")

            # Persisted target_scene_numbers are authoritative for KAN-86 selected
            # per-scene renders; selected_shot_ids only refine shot image choice.
            video_script_id = str(video_gen.get("script_id")) if video_gen.get("script_id") else None
            selected_shots = extract_shot_selections(
                task_meta.get("selected_shot_ids"), expected_script_id=video_script_id
            )
            persisted_target_scene_numbers = normalize_target_scene_numbers(
                task_meta.get("target_scene_numbers")
            )

            if persisted_target_scene_numbers:
                target_scene_numbers = persisted_target_scene_numbers
                print(
                    f"[SCENE VIDEOS] Using persisted target_scene_numbers: {target_scene_numbers}"
                )
            elif selected_shots:
                target_scene_numbers = [selection.scene_number for selection in selected_shots]
                print(
                    f"[SCENE VIDEOS] Derived target scenes from selected_shot_ids: {target_scene_numbers}"
                )
            else:
                target_scene_numbers = list(range(1, len(scene_descriptions) + 1))
                print(
                    f"[VIDEO GENERATION] No selected scene scope in task_meta; using all {len(scene_descriptions)} scenes"
                )

            target_scene_descriptions, target_scene_numbers, final_scene_images = (
                select_scene_assets_for_targets(
                    target_scene_numbers=target_scene_numbers,
                    original_scene_descriptions=original_scene_descriptions,
                    scene_image_map=scene_image_map,
                    pre_gen_scene_images=pre_gen_scene_images,
                    pre_gen_character_images=pre_gen_character_images,
                    selected_shots=selected_shots,
                )
            )
            image_data["scene_images"] = final_scene_images

            scene_count = len(
                [img for img in image_data.get("scene_images", []) if img is not None]
            )
            print(f"[IMAGE SELECTION SUMMARY]")
            print(
                f"- Total scene images assigned: {scene_count} / {len(target_scene_descriptions)} target scenes"
            )

            # Generate videos
            modelslab_service = ModelsLabV7VideoService()

            selected_audio_ids = task_meta.get("selected_audio_ids", [])

            # Generate scene videos sequentially with key scene shots
            video_results = await generate_scene_videos(
                modelslab_service,
                video_generation_id,
                target_scene_descriptions,
                audio_files,
                image_data,
                video_style,
                script_data,
                user_id,
                model_config=video_config,
                session=session,
                scene_numbers=target_scene_numbers,
                selected_audio_ids=selected_audio_ids,
            )

            # Compile results
            video_results = dedupe_scene_videos(video_results)
            successful_videos = len([r for r in video_results if r is not None])
            total_scenes = len(target_scene_descriptions)
            success_rate = (
                (successful_videos / total_scenes * 100) if total_scenes > 0 else 0
            )

            # Calculate total video duration
            total_duration = sum(
                [v.get("duration", 0) for v in video_results if v is not None]
            )

            # Get the first successful video URL for the video_url column
            first_video_url = None
            for vr in video_results:
                if vr is not None and vr.get("video_url"):
                    first_video_url = vr["video_url"]
                    break

            # Update video generation with video data
            video_data_result = {
                "scene_videos": video_results,
                "statistics": {
                    "total_scenes": total_scenes,
                    "videos_generated": successful_videos,
                    "total_duration": total_duration,
                    "success_rate": round(success_rate, 2),
                },
            }

            update_query = text(
                """
                UPDATE video_generations
                SET video_data = :video_data,
                    generation_status = :status,
                    error_message = :error_message,
                    video_url = :video_url
                WHERE id = :id
            """
            )

            # If 0 videos were generated, this is a failure — no video_url will be produced
            if successful_videos == 0:
                final_status = "failed"
                error_msg = f"Video generation failed: 0 out of {total_scenes} scene videos were created. Check image availability and ModelsLab API."
                print(f"[VIDEO GENERATION FAILED] {error_msg}")
            else:
                final_status = "video_completed"
                error_msg = None
                print(
                    f"[VIDEO URL] Saving video_url={first_video_url} to video_generation {video_generation_id}"
                )

            await session.execute(
                update_query,
                {
                    "video_data": json.dumps(video_data_result),
                    "status": final_status,
                    "error_message": error_msg,
                    "video_url": first_video_url,
                    "id": video_generation_id,
                },
            )
            await session.commit()

            # Confirm or release the API-level credit reservation based on actual duration
            credit_reservation_id = task_meta.get("credit_reservation_id")
            if user_id and credit_reservation_id:
                try:
                    from app.credits.service import CreditService, credits_for_video_duration
                    from app.credits.constants import OperationType
                    credit_svc = CreditService(session)
                    actual_cost = (
                        credits_for_video_duration(float(total_duration))
                        if successful_videos > 0 and total_duration > 0
                        else 0
                    )
                    confirmed = await credit_svc.confirm_deduction(
                        uuid.UUID(credit_reservation_id), actual_cost
                    )
                    if not confirmed:
                        logger.warning(
                            "[CREDITS] confirm_deduction returned False for reservation %s — "
                            "logging to credit_failures for reconciliation",
                            credit_reservation_id,
                        )
                        try:
                            await credit_svc.log_credit_failure(
                                user_id=uuid.UUID(str(user_id)),
                                reservation_id=uuid.UUID(credit_reservation_id),
                                amount=actual_cost,
                                operation_type=OperationType.VIDEO_GEN,
                                error_message="confirm_deduction returned False",
                            )
                        except Exception as log_err:
                            logger.warning("[CREDITS] Failed to log credit failure: %s", log_err)
                    await session.commit()
                except Exception as credit_err:
                    logger.warning("[CREDITS] Video credit confirmation failed: %s", credit_err)

            # Update pipeline step based on result
            if successful_videos > 0:
                await update_pipeline_step(
                    video_generation_id,
                    "video_generation",
                    "completed",
                    session=session,
                )
            else:
                await update_pipeline_step(
                    video_generation_id,
                    "video_generation",
                    "failed",
                    error_msg,
                    session=session,
                )

            success_message = f"Video generation completed! {successful_videos} videos created for {total_scenes} scenes"
            print(
                f"[VIDEO GENERATION {'SUCCESS' if successful_videos > 0 else 'FAILED'}] {success_message}"
            )

            # Log detailed breakdown
            print(f"[VIDEO STATISTICS]")
            print(
                f"- Scene-by-scene generation status: {successful_videos}/{total_scenes}"
            )
            print(f"- Total video duration: {total_duration:.1f} seconds")
            print(f"- Success rate: {success_rate:.1f}%")

            # Video generation complete — merging is handled separately in the Merge tab
            print(
                f"[PIPELINE] Video generation complete. User can merge in the Merge tab."
            )

            return {
                "status": final_status,
                "message": success_message
                + (" - Videos ready for review." if final_status != "failed" else ""),
                "statistics": video_data_result["statistics"],
                "video_results": video_results,
                "next_step": None,
            }

        except Exception as e:
            error_message = f"Video generation failed: {str(e)}"
            print(f"[VIDEO GENERATION ERROR] {error_message}")

            # Rollback any failed transaction before attempting error updates
            try:
                await session.rollback()
            except Exception:
                pass

            # Release the API-level credit reservation on task failure
            try:
                _task_meta = locals().get("task_meta") or {}
                _user_id = locals().get("user_id")
                _reservation_id = _task_meta.get("credit_reservation_id") if _task_meta else None
                if _reservation_id and _user_id:
                    from app.credits.service import CreditService
                    from app.credits.constants import OperationType
                    credit_svc = CreditService(session)
                    await credit_svc.release_reservation(uuid.UUID(_reservation_id))
                    await session.commit()
            except Exception as credit_err:
                logger.warning("[CREDITS] Failed to release reservation on video task failure: %s", credit_err)

            # ✅ Update pipeline step to failed
            await update_pipeline_step(
                video_generation_id,
                "video_generation",
                "failed",
                error_message,
                session=session,
            )

            # Check if this is a video retrieval failure that can be retried
            is_retrieval_failure = any(
                keyword in str(e).lower()
                for keyword in [
                    "retrieval",
                    "download",
                    "url",
                    "video_url",
                    "future_links",
                    "fetch_result",
                ]
            )

            if is_retrieval_failure:
                print(
                    f"[VIDEO GENERATION] Video retrieval failure detected, scheduling automatic retry"
                )

                # Update status to indicate retry will be attempted
                # Update status to indicate retry will be attempted
                try:
                    update_query = text(
                        """
                        UPDATE video_generations 
                        SET generation_status = 'retrieval_failed', 
                            error_message = :error_message, 
                            can_resume = true 
                        WHERE id = :id
                    """
                    )
                    await session.execute(
                        update_query,
                        {
                            "error_message": f"Video retrieval failed, automatic retry scheduled: {str(e)}",
                            "id": video_generation_id,
                        },
                    )
                    await session.commit()

                    # Schedule automatic retry with initial delay
                    automatic_video_retry_task.apply_async(
                        args=[video_generation_id],
                        countdown=30,  # 30 seconds initial delay
                    )

                    print(
                        f"[VIDEO GENERATION] ✅ Automatic retry scheduled for video generation {video_generation_id}"
                    )

                    return {
                        "status": "retry_scheduled",
                        "message": "Video retrieval failed, automatic retry scheduled",
                        "video_generation_id": video_generation_id,
                        "retry_delay": 30,
                    }

                except Exception as retry_error:
                    print(
                        f"[VIDEO GENERATION] Failed to schedule automatic retry: {retry_error}"
                    )
                    # Fall through to regular error handling

        # Regular error handling for non-retrieval failures
        try:
            await session.rollback()
            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'failed',
                    error_message = :error_message
                WHERE id = :id
            """
            )
            await session.execute(
                update_query,
                {"error_message": error_message, "id": video_generation_id},
            )
            await session.commit()
        except:
            pass

        raise Exception(error_message)


async def extract_last_frame(video_url: str, user_id: str) -> Optional[str]:
    """
    Extract the last frame from a video URL and upload it to storage.
    Returns the URL of the extracted image.
    """
    try:
        print(f"[FRAME EXTRACTION] Extracting last frame from {video_url}")

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            video_path = temp_video.name

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_image:
            image_path = temp_image.name

        # Download video
        response = requests.get(video_url, stream=True)
        response.raise_for_status()
        with open(video_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Extract last frame using ffmpeg
        # -sseof -3: seek to 3 seconds before end (to ensure we locate valid frames)
        # -update 1: overwrite output
        # -q:v 2: high quality
        cmd = [
            "ffmpeg",
            "-sseof",
            "-1",  # Look at the very end
            "-i",
            video_path,
            "-update",
            "1",
            "-q:v",
            "2",
            "-y",
            image_path,
        ]

        process = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )

        # Upload extracted frame
        file_service = FileService()
        result = await file_service.upload_file(
            file_path=image_path,
            file_name=f"last_frame_{uuid.uuid4()}.jpg",
            content_type="image/jpeg",
            user_id=user_id,
            folder="video_frames",
        )

        # Cleanup
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(image_path):
            os.remove(image_path)

        return result.get("url")

    except Exception as e:
        print(f"[FRAME EXTRACTION ERROR] {e}")
        # Cleanup on error
        if "video_path" in locals() and os.path.exists(video_path):
            os.remove(video_path)
        if "image_path" in locals() and os.path.exists(image_path):
            os.remove(image_path)
        return None


async def pad_audio_to_min_duration(
    audio_url: str, min_duration: float, user_id: str
) -> Optional[str]:
    """
    Pad audio with silence to reach minimum duration using ffmpeg.
    """
    try:
        if not audio_url:
            return None

        print(f"[AUDIO PADDING] Padding audio to {min_duration}s: {audio_url}")

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_input:
            input_path = temp_input.name

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_output:
            output_path = temp_output.name

        try:
            # Download audio
            response = requests.get(audio_url, stream=True)
            response.raise_for_status()
            with open(input_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Pad with silence using ffmpeg
            # -af apad: add silence indefinitely
            # -t min_duration: stop after reaching min duration
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-af",
                "apad",
                "-t",
                str(min_duration),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                output_path,
            ]

            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
            )

            # Upload padded audio
            file_service = FileService()
            result = await file_service.upload_file(
                file_path=output_path,
                file_name=f"padded_audio_{uuid.uuid4()}.mp3",
                content_type="audio/mpeg",
                user_id=user_id,
                folder="audio_uploads",
            )

            return result.get("url")

        finally:
            # Cleanup
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

    except Exception as e:
        print(f"[AUDIO PADDING ERROR] {e}")
        return None


async def generate_scene_videos(
    modelslab_service: ModelsLabV7VideoService,  # ✅ Updated type hint
    video_gen_id: str,
    scene_descriptions: List[str],
    audio_files: Dict[str, Any],
    image_data: Dict[str, Any],
    video_style: str,
    script_data: Dict[str, Any] = None,
    user_id: str = None,
    model_config: Optional[ModelConfig] = None,
    session: AsyncSession = None,
    scene_numbers: List[int] = None,
    selected_audio_ids: List[str] = None,
) -> List[Dict[str, Any]]:
    """Generate videos for each scene using V7 Veo 2 image-to-video with sequential processing and key scene shots"""

    print(
        f"[SCENE VIDEOS V7] Generating scene videos sequentially with key scene shots..."
    )
    video_results = []
    if not session:
        raise Exception("Session required for generate_scene_videos")

    await rehydrate_media_provider_metadata(
        session,
        audio_files=audio_files,
        image_data=image_data,
        selected_audio_ids=selected_audio_ids,
    )

    scene_images = image_data.get("scene_images", [])  # Fixed key mismatch

    # Determine Model ID from Config or fallback
    primary_model_id = "seedance-1-5-pro"  # Default fallback
    if model_config and model_config.primary:
        primary_model_id = model_config.primary

    print(f"[SCENE VIDEOS] Using Primary Model: {primary_model_id}")

    # Parse script for enhanced prompt generation if script data is available
    parsed_components = None
    if script_data and script_data.get("script"):
        try:
            from app.core.services.script_parser import ScriptParser

            script_parser = ScriptParser()
            characters = script_data.get("characters", [])
            parsed_components = script_parser.parse_script_for_video_prompt(
                script=script_data["script"], characters=characters
            )
            print(f"[SCENE VIDEOS V7] ✅ Parsed script for enhanced prompt generation:")
            print(
                f"- Camera movements: {len(parsed_components.get('camera_movements', []))}"
            )
            print(
                f"- Character actions: {len(parsed_components.get('character_actions', []))}"
            )
            print(
                f"- Character dialogues: {len(parsed_components.get('character_dialogues', []))}"
            )
        except Exception as e:
            print(
                f"[SCENE VIDEOS V7] ⚠️ Failed to parse script for enhanced prompts: {e}"
            )

    # Track the previous scene's key scene shot for continuity
    previous_key_scene_shot = None

    db_user_id = _safe_uuid_string(user_id)

    for i, scene_description in enumerate(scene_descriptions):
        scene_num = i + 1
        scene_id = f"scene_{scene_num}"
        provider_attempt = None
        provider_attempt_persisted = False
        try:
            scene_num, scene_id = resolve_scene_identity(i, scene_numbers)
            scene_image = scene_images[i] if i < len(scene_images) else None
            target_image_url = (
                scene_image.get("image_url")
                if scene_image and scene_image.get("image_url")
                else None
            )
            target_shot_index = scene_image.get("shot_index", 0) if scene_image else 0

            print(
                f"[SCENE VIDEOS V7] Processing {scene_id} ({i+1}/{len(scene_descriptions)})"
            )

            # Determine the starting image for this scene
            starting_image_url = None

            if i == 0:
                # First scene: use the original scene image
                if not scene_image or not scene_image.get("image_url"):
                    print(f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}")
                    video_results.append(None)
                    continue

                starting_image_url = scene_image["image_url"]
                print(f"[SCENE VIDEOS V7] Using original scene image for {scene_id}")
            else:
                # Subsequent scenes: use the previous scene's key scene shot
                if previous_key_scene_shot:
                    starting_image_url = previous_key_scene_shot
                    print(
                        f"[SCENE VIDEOS V7] Using previous key scene shot for {scene_id}: {starting_image_url}"
                    )
                else:
                    # Fallback to original scene image if no previous key scene shot
                    scene_image = None
                    if i < len(scene_images) and scene_images[i] is not None:
                        scene_image = scene_images[i]

                    if scene_image and scene_image.get("image_url"):
                        starting_image_url = scene_image["image_url"]
                        print(
                            f"[SCENE VIDEOS V7] Using fallback scene image for {scene_id} (no previous key scene shot)"
                        )
                    else:
                        print(
                            f"[SCENE VIDEOS V7] ⚠️ No valid image found for {scene_id}"
                        )
                        video_results.append(None)
                        continue

            # Determine model ID before audio check (needed for duration limits)
            current_model_id = primary_model_id
            min_audio = modelslab_service.get_min_audio_duration(current_model_id)

            # Find audio for lip sync / audio-reactive
            scene_audio = find_scene_audio(
                scene_id, audio_files, selected_audio_ids=selected_audio_ids
            )
            init_audio_url = None

            if scene_audio:
                audio_duration = scene_audio.get("duration", 0)
                max_audio = modelslab_service.get_max_audio_duration(current_model_id)

                # KAN-166: Fix duration validation — audio_duration <= 0 means unknown duration
                # Previously, `audio_duration > 0` guard caused audio with unknown duration to
                # bypass min/max validation entirely, passing 0s audio to the video API.
                if audio_duration <= 0:
                    audio_url_available = scene_audio.get("audio_url")
                    if audio_url_available:
                        # Unknown duration — probe the file to get actual duration
                        try:
                            from app.core.services.ffmpeg_utils import probe_audio_duration_from_url
                            probe_audio_url = normalize_media_url_for_internal_access(scene_audio.get("audio_url"))
                            probed = await probe_audio_duration_from_url(probe_audio_url)
                            if probed and probed > 0:
                                audio_duration = probed
                                print(f"[SCENE AUDIO] {scene_id}: KAN-166 probed duration={audio_duration}s")
                        except Exception as probe_err:
                            print(f"[SCENE AUDIO] {scene_id}: KAN-166 duration probe failed: {probe_err}")

                if max_audio and audio_duration > 0 and audio_duration > max_audio:
                    print(
                        f"[SCENE AUDIO] {scene_id}: duration ({audio_duration}s) exceeds max ({max_audio}s). Skipping audio."
                    )
                elif min_audio and audio_duration > 0 and audio_duration < min_audio:
                    print(
                        f"[SCENE AUDIO] {scene_id}: duration ({audio_duration}s) below min ({min_audio}s). Padding with silence..."
                    )

                    try:
                        # Attempt to pad audio
                        padded_url = await pad_audio_to_min_duration(
                            normalize_media_url_for_internal_access(scene_audio.get("audio_url")), min_audio, user_id
                        )

                        if padded_url:
                            init_audio_url = padded_url
                            print(
                                f"[SCENE AUDIO] {scene_id}: Usage padded audio: {padded_url}"
                            )
                        else:
                            print(
                                f"[SCENE AUDIO] {scene_id}: Failed to pad audio, skipping."
                            )
                            init_audio_url = None
                    except Exception as e:
                        print(f"[SCENE AUDIO] {scene_id}: Error padding audio: {e}")
                        init_audio_url = None
                elif audio_duration <= 0:
                    # KAN-166: Audio with duration <= 0 (even after probing) is effectively broken
                    print(
                        f"[SCENE AUDIO] {scene_id}: duration unknown/unproable ({audio_duration}s). Skipping audio."
                    )
                    init_audio_url = None
                else:
                    init_audio_url = scene_audio.get("audio_url")
                    print(
                        f"[SCENE AUDIO] {scene_id}: using audio id={scene_audio.get('id')}, "
                        f"type={scene_audio.get('audio_type')}, duration={audio_duration}s, "
                        f"model={current_model_id} (limit={max_audio}s)"
                    )
            else:
                print(
                    f"[SCENE AUDIO] {scene_id}: no audio selected, generating without init_audio"
                )

            # Decide on Model: Dialogue (Audio) vs Narration (Visual Only)
            # If we have init_audio, we MIGHT want to use a specific lip-sync capable model if the primary isn't one
            # But per plan, tiers like Standard+ use Omni/Wan which support it.
            # Free/Basic might use seedance (no lip sync) or wan2.5 (lip sync).

            logger_msg = f"[SCENE VIDEOS V7] Generating video for {scene_id} using {current_model_id}"
            if init_audio_url:
                logger_msg += " with Audio Reactive/Lip Sync"
            print(logger_msg)

            # Build enhanced video prompt using image generation prompt if available
            scene_image_for_prompt = None
            if i < len(scene_images) and scene_images[i] is not None:
                scene_image_for_prompt = scene_images[i]

            image_prompt = (
                scene_image_for_prompt.get("prompt", "")
                if scene_image_for_prompt
                else ""
            )

            if image_prompt and image_prompt.strip():
                # Combine scene description with image prompt for richer video generation
                enhanced_prompt = f"{scene_description}. Visual style: {image_prompt}"
                print(
                    f"[SCENE VIDEOS V7] Using enhanced prompt with image prompt for {scene_id}"
                )
            else:
                enhanced_prompt = scene_description
                print(
                    f"[SCENE VIDEOS V7] No image prompt available, using scene description for {scene_id}"
                )

            # Normalize media URLs at the provider boundary. Stored MinIO URLs can
            # be localhost/docker-internal URLs; ModelsLab needs externally
            # reachable URLs, while earlier probes/downloads use internal URLs.
            try:
                provider_source_image_url = select_provider_media_source(
                    starting_image_url,
                    scene_image_for_prompt or scene_image,
                )
                provider_source_audio_url = select_provider_media_source(
                    init_audio_url,
                    scene_audio,
                )
                provider_image_url = normalize_media_url_for_provider(provider_source_image_url)
                provider_init_audio_url = (
                    normalize_media_url_for_provider(provider_source_audio_url)
                    if provider_source_audio_url
                    else None
                )
            except ProviderMediaUrlConfigurationError as media_config_error:
                provider_attempt = _build_provider_attempt_diagnostic(
                    scene_id=scene_id,
                    scene_number=scene_num,
                    original_image_url=provider_source_image_url,
                    provider_image_url=None,
                    original_audio_url=provider_source_audio_url,
                    provider_audio_url=None,
                    model=current_model_id,
                    status="configuration_error",
                    exception=str(media_config_error),
                    canonical_image_url=starting_image_url,
                    canonical_audio_url=init_audio_url,
                )
                raise

            log_provider_media_url_normalization("image_url", provider_source_image_url, provider_image_url)
            log_provider_media_url_normalization("init_audio", provider_source_audio_url, provider_init_audio_url)

            provider_attempt = _build_provider_attempt_diagnostic(
                scene_id=scene_id,
                scene_number=scene_num,
                original_image_url=provider_source_image_url,
                provider_image_url=provider_image_url,
                original_audio_url=provider_source_audio_url,
                provider_audio_url=provider_init_audio_url,
                model=current_model_id,
                status="attempting",
                canonical_image_url=starting_image_url,
                canonical_audio_url=init_audio_url,
            )
            logger.warning(
                "[SCENE VIDEOS V7] Provider attempt scene_id=%s scene_number=%s model=%s image=%s audio=%s",
                scene_id,
                scene_num,
                current_model_id,
                provider_attempt.get("provider_image_url"),
                provider_attempt.get("provider_audio_url"),
            )

            # ✅ Generate video using ModelsLab Service
            provider_result = await modelslab_service.generate_image_to_video(
                image_url=provider_image_url,
                prompt=enhanced_prompt,
                model_id=current_model_id,
                negative_prompt="",
                init_audio=provider_init_audio_url if provider_init_audio_url else None,
            )

            provider_attempt["status"] = provider_result.get("status", "unknown")
            if provider_result.get("error"):
                provider_attempt["provider_error"] = str(provider_result.get("error"))[:500]
                provider_attempt["exception"] = (
                    f"V7 Video generation failed: {provider_result.get('error', 'Unknown error')}"
                )[:500]
            await _persist_provider_attempt_diagnostic(session, video_gen_id, provider_attempt)
            provider_attempt_persisted = True

            # Process result (Adapt old verify logic to new direct call result)
            # generate_image_to_video returns dict with status/video_url or error

            if provider_result.get("status") == "success":
                video_url = provider_result.get("video_url")
                has_lipsync = bool(init_audio_url)

                # Persist video from CDN to our own S3 storage
                if video_url:
                    original_cdn_url = video_url
                    try:
                        from app.core.services.storage import (
                            get_storage_service,
                            S3StorageService,
                        )
                        import uuid as _uuid_mod

                        storage = get_storage_service()
                        s3_path = S3StorageService.build_media_path(
                            user_id=str(user_id) if user_id else "system",
                            media_type="video",
                            record_id=str(_uuid_mod.uuid4()),
                            extension="mp4",
                        )
                        video_url = await storage.persist_from_url(
                            video_url,
                            s3_path,
                            content_type="video/mp4",
                            timeout_seconds=300,
                        )
                        logger.info(f"[VideoTask] Persisted video to S3: {s3_path}")
                    except Exception as persist_error:
                        logger.error(
                            f"[VideoTask] Failed to persist video to S3: {persist_error}"
                        )
                        raise Exception(
                            f"Video generated but failed to persist to storage: {persist_error}"
                        )

                if video_url:
                    # Extract the last frame as key scene shot for the next scene
                    key_scene_shot_url = None
                    try:
                        key_scene_shot_url = await extract_last_frame(
                            video_url, user_id
                        )

                        if key_scene_shot_url:
                            print(
                                f"[SCENE VIDEOS V7] ✅ Extracted key scene shot for {scene_id}: {key_scene_shot_url}"
                            )
                            previous_key_scene_shot = (
                                key_scene_shot_url  # Update for next scene
                            )
                        else:
                            print(
                                f"[SCENE VIDEOS V7] ⚠️ Failed to extract key scene shot for {scene_id}"
                            )
                    except Exception as frame_error:
                        print(
                            f"[SCENE VIDEOS V7] ⚠️ Error extracting key scene shot for {scene_id}: {frame_error}"
                        )

                    # Store in database
                    try:
                        insert_query = text(
                            """
                            INSERT INTO video_segments (
                                video_generation_id, user_id, scene_id, scene_number, scene_description,
                                video_url, status, target_duration,
                                character_count, dialogue_count, action_count
                            ) VALUES (
                                :video_generation_id, :user_id, :scene_id, :scene_number, :scene_description,
                                :video_url, :status, :target_duration,
                                :character_count, :dialogue_count, :action_count
                            ) RETURNING id
                        """
                        )

                        result = await session.execute(
                            insert_query,
                            {
                                "video_generation_id": video_gen_id,
                                "user_id": db_user_id,
                                "scene_id": scene_id,
                                "scene_number": scene_num,
                                "scene_description": scene_description,
                                "video_url": video_url,
                                "status": "completed",
                                "target_duration": 5.0,
                                "character_count": 0,
                                "dialogue_count": 0,
                                "action_count": 0,
                            },
                        )
                        await session.commit()
                        video_record_id = result.scalar()
                    except Exception as e:
                        print(f"[SCENE VIDEOS V7] Error inserting video segment: {e}")
                        await session.rollback()
                        video_record_id = None

                    video_results.append(
                        {
                            "id": video_record_id,
                            "scene_id": scene_id,
                            "scene_number": scene_num,
                            "shot_index": target_shot_index,
                            "video_url": video_url,
                            "original_cdn_url": original_cdn_url,
                            "provider_cdn_url": original_cdn_url,
                            "key_scene_shot_url": key_scene_shot_url,
                            "duration": 5.0,
                            "source_image": starting_image_url,
                            "target_image": target_image_url,
                            "method": "veo2_image_to_video_sequential",
                            "model": current_model_id,
                            "has_lipsync": has_lipsync,
                            "audio_id": scene_audio.get("id") if scene_audio else None,
                            "audio_url": scene_audio.get("audio_url") if scene_audio else None,
                            "audio_scene_number": scene_audio.get("scene_number") if scene_audio else None,
                            "audio_duration": audio_duration if scene_audio else None,
                            "scene_sequence": scene_num,
                        }
                    )

                    print(
                        f"[SCENE VIDEOS V7] ✅ Generated {scene_id} - Lip sync: {has_lipsync}, Key scene shot: {key_scene_shot_url is not None}"
                    )
                else:
                    raise Exception("No video URL in V7 response")
            else:
                logger.error(
                    "[SCENE VIDEOS V7] Provider failed scene_id=%s scene_number=%s model=%s error=%s",
                    scene_id,
                    scene_num,
                    current_model_id,
                    provider_result.get("error", "Unknown error"),
                )
                raise Exception(
                    f"V7 Video generation failed: {provider_result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            if provider_attempt and not provider_attempt_persisted:
                provider_attempt["status"] = provider_attempt.get("status") or "exception"
                provider_attempt["exception"] = str(e)[:500]
                logger.error(
                    "[SCENE VIDEOS V7] Provider/scene exception scene_id=%s scene_number=%s model=%s error=%s",
                    scene_id,
                    scene_num,
                    provider_attempt.get("model"),
                    str(e),
                )
                await _persist_provider_attempt_diagnostic(session, video_gen_id, provider_attempt)
            print(f"[SCENE VIDEOS V7] ❌ Failed {scene_id}: {str(e)}")

            # Store failed record

            try:
                fail_insert_query = text(
                    """
                    INSERT INTO video_segments (
                        video_generation_id, user_id, scene_id, scene_number, scene_description,
                        status, character_count, dialogue_count, action_count
                    ) VALUES (
                        :video_generation_id, :user_id, :scene_id, :scene_number, :scene_description,
                        :status, :character_count, :dialogue_count, :action_count
                    )
                """
                )

                await session.execute(
                    fail_insert_query,
                    {
                        "video_generation_id": video_gen_id,
                        "user_id": db_user_id,
                        "scene_id": scene_id,
                        "scene_number": scene_num,
                        "scene_description": scene_description,
                        "status": "failed",
                        "character_count": 0,
                        "dialogue_count": 0,
                        "action_count": 0,
                    },
                )
                await session.commit()
            except Exception as insert_err:
                print(f"[SCENE VIDEOS V7] Error inserting failed record: {insert_err}")
                await session.rollback()

            video_results.append(None)

    successful_videos = len([r for r in video_results if r is not None])
    print(
        f"[SCENE VIDEOS V7] Sequential generation completed: {successful_videos}/{len(scene_descriptions)} videos"
    )
    return video_results


@celery_app.task(bind=True)
def retry_video_retrieval_task(self, video_generation_id: str, video_url: str = None):
    """Celery task to retry video retrieval for a failed video generation"""
    return asyncio.run(async_retry_video_retrieval_task(video_generation_id, video_url))


async def async_retry_video_retrieval_task(
    video_generation_id: str, video_url: str = None
):
    """Async implementation of retry video retrieval task"""
    async with async_session() as session:
        try:
            print(
                f"[VIDEO RETRY TASK] Starting video retrieval retry for: {video_generation_id}"
            )

            # Get video generation data
            # Using raw SQL
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            video_gen = dict(video_gen_record)
            user_id = video_gen.get("user_id")
            current_status = video_gen.get("generation_status")

            # Check if this task is eligible for retry
            if current_status not in ["video_completed", "failed", "retrieval_failed"]:
                raise Exception(
                    f"Cannot retry video retrieval. Current status: {current_status}"
                )

            # Check retry count
            retry_count = video_gen.get("retry_count", 0)
            max_retries = 3

            if retry_count >= max_retries:
                raise Exception(f"Maximum retry attempts ({max_retries}) exceeded")

            # Get video URL from parameter or task data
            if not video_url:
                task_meta = video_gen.get("task_meta", {})
                video_url = task_meta.get("future_links_url") or task_meta.get(
                    "video_url"
                )

                if not video_url:
                    raise Exception("No video URL available for retry")

            print(
                f"[VIDEO RETRY TASK] Attempting video retrieval from URL: {video_url}"
            )

            # Import and use the video service for retry
            from app.core.services.modelslab_v7_video import ModelsLabV7VideoService

            video_service = ModelsLabV7VideoService()

            # Attempt video retrieval
            retry_result = await video_service.retry_video_retrieval(video_url)

            if not retry_result.get("success"):
                # Update retry count and status
                new_retry_count = retry_count + 1

                update_query = text(
                    """
                    UPDATE video_generations
                    SET retry_count = :retry_count,
                        generation_status = :status,
                        error_message = :error_message,
                        can_resume = :can_resume
                    WHERE id = :id
                """
                )

                status = (
                    "retrieval_failed" if new_retry_count < max_retries else "failed"
                )

                await session.execute(
                    update_query,
                    {
                        "retry_count": new_retry_count,
                        "status": status,
                        "error_message": retry_result.get(
                            "error", "Video retrieval failed"
                        ),
                        "can_resume": new_retry_count < max_retries,
                        "id": video_generation_id,
                    },
                )
                await session.commit()

                raise Exception(
                    f"Video retrieval failed: {retry_result.get('error', 'Unknown error')}"
                )

            # Success - update task with video URL and mark as completed
            video_url = retry_result.get("video_url")
            video_duration = retry_result.get("duration", 0)

            # Persist video from CDN to our own S3 storage
            if video_url:
                original_cdn_url = video_url
                try:
                    from app.core.services.storage import (
                        get_storage_service,
                        S3StorageService,
                    )
                    import uuid as _uuid_mod

                    storage = get_storage_service()
                    s3_path = S3StorageService.build_media_path(
                        user_id=str(user_id) if user_id else "system",
                        media_type="video",
                        record_id=str(video_generation_id),
                        extension="mp4",
                    )
                    video_url = await storage.persist_from_url(
                        video_url,
                        s3_path,
                        content_type="video/mp4",
                        timeout_seconds=300,
                    )
                    logger.info(f"[VideoRetryTask] Persisted video to S3: {s3_path}")
                except Exception as persist_error:
                    logger.error(
                        f"[VideoRetryTask] Failed to persist video to S3: {persist_error}"
                    )
                    raise Exception(
                        f"Video retrieved but failed to persist to storage: {persist_error}"
                    )

            task_meta = video_gen.get("task_meta", {})
            task_meta.update(
                {
                    "retry_success": True,
                    "retry_video_url": video_url,
                    "original_cdn_url": original_cdn_url,
                    "provider_cdn_url": original_cdn_url,
                    "video_duration": video_duration,
                    "final_retrieval_time": "now()",
                }
            )

            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'completed',
                    video_url = :video_url,
                    retry_count = :retry_count,
                    error_message = NULL,
                    can_resume = false,
                    task_meta = :task_meta
                WHERE id = :id
            """
            )

            await session.execute(
                update_query,
                {
                    "video_url": video_url,
                    "retry_count": retry_count + 1,
                    "task_meta": json.dumps(task_meta),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            print(
                f"[VIDEO RETRY TASK] ✅ Video retrieval retry successful for: {video_generation_id}"
            )

            return {
                "status": "success",
                "message": "Video retrieval successful",
                "video_url": video_url,
                "duration": video_duration,
                "retry_count": retry_count + 1,
                "video_generation_id": video_generation_id,
            }

        except Exception as e:
            error_message = f"Video retrieval retry failed: {str(e)}"
            print(f"[VIDEO RETRY TASK] ❌ {error_message}")

            # Update status to failed
            try:
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'failed', 
                        error_message = :error_message 
                    WHERE id = :id
                """
                )
                await session.execute(
                    update_query,
                    {"error_message": error_message, "id": video_generation_id},
                )
                await session.commit()
            except:
                pass

            raise Exception(error_message)


@celery_app.task(bind=True)
def automatic_video_retry_task(self, video_generation_id: str):
    """Automatic retry task with exponential backoff for failed video retrievals"""
    return asyncio.run(async_automatic_video_retry_task(video_generation_id))


async def async_automatic_video_retry_task(video_generation_id: str):
    """Async implementation of automatic retry task"""
    async with async_session() as session:
        try:
            print(
                f"[AUTO RETRY TASK] Starting automatic retry for: {video_generation_id}"
            )

            # Get video generation data
            query = text("SELECT * FROM video_generations WHERE id = :id")
            result = await session.execute(query, {"id": video_generation_id})
            video_gen_record = result.mappings().first()

            if not video_gen_record:
                raise Exception(f"Video generation {video_generation_id} not found")

            video_gen = dict(video_gen_record)
            current_status = video_gen.get("generation_status")

            # Only retry if in a retryable state
            if current_status not in ["video_completed", "failed", "retrieval_failed"]:
                print(
                    f"[AUTO RETRY TASK] Skipping - current status {current_status} not retryable"
                )
                return {
                    "status": "skipped",
                    "message": f"Current status {current_status} not eligible for automatic retry",
                }

            # Check retry count
            retry_count = video_gen.get("retry_count", 0)
            max_automatic_retries = (
                2  # Maximum automatic retries before manual intervention
            )

            if retry_count >= max_automatic_retries:
                print(
                    f"[AUTO RETRY TASK] Maximum automatic retries ({max_automatic_retries}) reached"
                )
                # Update status to indicate manual retry is needed
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'retrieval_failed', 
                        can_resume = true, 
                        error_message = :error_message 
                    WHERE id = :id
                """
                )
                await session.execute(
                    update_query,
                    {
                        "error_message": f"Automatic retries exhausted. Please try manual retry.",
                        "id": video_generation_id,
                    },
                )
                await session.commit()

                return {
                    "status": "max_retries_reached",
                    "message": f"Maximum automatic retries ({max_automatic_retries}) reached",
                }

            # Calculate exponential backoff delay
            base_delay = 30  # 30 seconds
            exponential_delay = base_delay * (2**retry_count)  # 30s, 60s, 120s, etc.
            max_delay = 300  # 5 minutes maximum

            actual_delay = min(exponential_delay, max_delay)

            print(
                f"[AUTO RETRY TASK] Retry {retry_count + 1}/{max_automatic_retries}, waiting {actual_delay}s"
            )

            # Wait for exponential backoff
            await asyncio.sleep(actual_delay)

            # Get video URL from task meta
            task_meta_data = video_gen.get("task_meta", {})
            video_url = task_meta_data.get("future_links_url") or task_meta_data.get(
                "video_url"
            )

            if not video_url:
                print(f"[AUTO RETRY TASK] No video URL available for retry")
                return {
                    "status": "no_url",
                    "message": "No video URL available for automatic retry",
                }

            print(
                f"[AUTO RETRY TASK] Attempting automatic video retrieval from URL: {video_url}"
            )

            # Import and use the video service for retry
            from app.core.services.modelslab_v7_video import ModelsLabV7VideoService

            video_service = ModelsLabV7VideoService()

            # Attempt video retrieval
            retry_result = await video_service.retry_video_retrieval(video_url)

            if not retry_result.get("success"):
                # Update retry count and status
                new_retry_count = retry_count + 1

                update_query = text(
                    """
                    UPDATE video_generations
                    SET retry_count = :retry_count,
                        generation_status = :status,
                        error_message = :error_message,
                        can_resume = :can_resume
                    WHERE id = :id
                """
                )

                status = (
                    "retrieval_failed"
                    if new_retry_count < max_automatic_retries
                    else "failed"
                )

                await session.execute(
                    update_query,
                    {
                        "retry_count": new_retry_count,
                        "status": status,
                        "error_message": retry_result.get(
                            "error", "Video retrieval failed"
                        ),
                        "can_resume": new_retry_count < max_automatic_retries,
                        "id": video_generation_id,
                    },
                )
                await session.commit()

                # Schedule next automatic retry if we haven't reached max
                if new_retry_count < max_automatic_retries:
                    print(f"[AUTO RETRY TASK] Scheduling next automatic retry")
                    automatic_video_retry_task.apply_async(
                        args=[video_generation_id],
                        countdown=actual_delay * 2,  # Double the delay for next retry
                    )

                return {
                    "status": "failed",
                    "message": f'Automatic retry failed: {retry_result.get("error", "Unknown error")}',
                    "retry_count": new_retry_count,
                    "next_retry_scheduled": new_retry_count < max_automatic_retries,
                }

            # Success - update task with video URL and mark as completed
            video_url = retry_result.get("video_url")
            video_duration = retry_result.get("duration", 0)

            # Persist video from CDN to our own S3 storage
            if video_url:
                original_cdn_url = video_url
                try:
                    from app.core.services.storage import (
                        get_storage_service,
                        S3StorageService,
                    )
                    import uuid as _uuid_mod

                    storage = get_storage_service()
                    s3_path = S3StorageService.build_media_path(
                        user_id=str(user_id) if user_id else "system",
                        media_type="video",
                        record_id=str(video_generation_id),
                        extension="mp4",
                    )
                    video_url = await storage.persist_from_url(
                        video_url,
                        s3_path,
                        content_type="video/mp4",
                        timeout_seconds=300,
                    )
                    logger.info(f"[AutoRetryTask] Persisted video to S3: {s3_path}")
                except Exception as persist_error:
                    logger.error(
                        f"[AutoRetryTask] Failed to persist video to S3: {persist_error}"
                    )
                    raise Exception(
                        f"Video retrieved but failed to persist to storage: {persist_error}"
                    )

            task_meta = video_gen.get("task_meta", {})
            task_meta.update(
                {
                    "retry_success": True,
                    "retry_video_url": video_url,
                    "original_cdn_url": original_cdn_url,
                    "provider_cdn_url": original_cdn_url,
                    "video_duration": video_duration,
                    "final_retrieval_time": "now()",
                }
            )

            update_query = text(
                """
                UPDATE video_generations
                SET generation_status = 'completed',
                    video_url = :video_url,
                    retry_count = :retry_count,
                    error_message = NULL,
                    can_resume = false,
                    task_meta = :task_meta
                WHERE id = :id
            """
            )

            await session.execute(
                update_query,
                {
                    "video_url": video_url,
                    "retry_count": retry_count + 1,
                    "task_meta": json.dumps(task_meta),
                    "id": video_generation_id,
                },
            )
            await session.commit()

            print(
                f"[AUTO RETRY TASK] ✅ Automatic video retrieval successful for: {video_generation_id}"
            )

            return {
                "status": "success",
                "message": "Automatic video retrieval successful",
                "video_url": video_url,
                "duration": video_duration,
                "retry_count": retry_count + 1,
                "video_generation_id": video_generation_id,
            }

        except Exception as e:
            error_message = f"Automatic retry failed: {str(e)}"
            print(f"[AUTO RETRY TASK] ❌ {error_message}")

            # Update status to failed
            try:
                update_query = text(
                    """
                    UPDATE video_generations 
                    SET generation_status = 'failed', 
                        error_message = :error_message 
                    WHERE id = :id
                """
                )
                await session.execute(
                    update_query,
                    {"error_message": error_message, "id": video_generation_id},
                )
                await session.commit()
            except:
                pass

            raise Exception(error_message)
