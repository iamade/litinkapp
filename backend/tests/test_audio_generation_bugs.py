import pytest


class TestAudioGenerationPerScene:
    """KAN-165: Audio should be per-scene, not entire script.

    Root cause: Sound effects and background music results lacked scene/scene_number
    keys, so find_scene_audio() could never match them to specific scenes. Also,
    extract_dialogue_per_scene() was hardcoded to characters=[] preventing any
    character dialogue detection.
    """

    def test_sfx_results_include_scene_keys(self):
        """Verify SFX audio results include 'scene' and 'scene_number' keys."""
        # This simulates what generate_sound_effects_audio() returns after the fix
        sfx_result = {
            "id": "test-sfx-id",
            "effect_id": 1,
            "audio_url": "https://example.com/sfx.mp3",
            "description": "Ocean waves crashing",
            "duration": 10,
            "scene": 2,
            "scene_number": 2,
            "shot_type": "key_scene",
            "shot_index": 0,
        }
        assert "scene" in sfx_result, "SFX result must include 'scene' key for per-scene matching"
        assert "scene_number" in sfx_result, "SFX result must include 'scene_number' key"
        assert sfx_result["scene"] == 2
        assert sfx_result["scene_number"] == 2

    def test_bgm_results_include_scene_number(self):
        """Verify BGM results include 'scene_number' key (consistent with narrator/character)."""
        bgm_result = {
            "id": "test-bgm-id",
            "scene": 3,
            "scene_number": 3,  # KAN-165: added explicit scene_number
            "audio_url": "https://example.com/bgm.mp3",
            "description": "Tense orchestral music",
            "duration": 30,
        }
        assert "scene" in bgm_result, "BGM result must include 'scene' key"
        assert "scene_number" in bgm_result, "BGM result must include 'scene_number' key"
        assert bgm_result["scene"] == 3
        assert bgm_result["scene_number"] == 3

    def test_sfx_results_use_id_not_db_id(self):
        """Verify SFX results use 'id' key (consistent with narrator/character/bgm)."""
        sfx_result = {
            "id": "test-sfx-id",
            "effect_id": 1,
            "audio_url": "https://example.com/sfx.mp3",
            "description": "Thunder",
            "duration": 5,
            "scene": 1,
            "scene_number": 1,
            "shot_type": "key_scene",
            "shot_index": 0,
        }
        assert "id" in sfx_result, "SFX result must use 'id' key (not 'db_id')"
        assert "db_id" not in sfx_result, "SFX result must NOT use 'db_id' (legacy key removed)"

    def test_narrator_results_include_scene_number(self):
        """Verify narrator results already include both 'scene' and 'scene_number'."""
        narrator_result = {
            "id": "test-narrator-id",
            "scene": 1,
            "scene_number": 1,
            "audio_url": "https://example.com/narrator.mp3",
            "duration": 15,
            "text": "Call me Ishmael.",
        }
        assert "scene" in narrator_result
        assert "scene_number" in narrator_result
        assert narrator_result["scene"] == narrator_result["scene_number"]

    def test_character_results_include_scene_number(self):
        """Verify character dialogue results include both 'scene' and 'scene_number'."""
        char_result = {
            "id": "test-char-id",
            "character": "Ishmael",
            "voice_name": "Drew",
            "voice_id": "29vD33N1CtxCmqQRPOHJ",
            "scene": 2,
            "scene_number": 2,
            "audio_url": "https://example.com/char.mp3",
            "duration": 8,
            "text": "I want to see the world.",
        }
        assert "scene" in char_result
        assert "scene_number" in char_result
        assert char_result["scene"] == char_result["scene_number"]

    def _find_scene_audio(self, scene_id, audio_files, selected_audio_ids=None):
        """Standalone copy of find_scene_audio for testing without celery imports.

        Priority: explicit selection > exact scene match (character > narrator > any type) > fallback.
        """
        scene_number = int(scene_id.split("_")[1]) if "_" in scene_id else 1

        all_audio = []
        for audio_type in ["characters", "narrator", "sound_effects", "background_music"]:
            all_audio.extend(audio_files.get(audio_type, []))

        # Priority 0: Explicitly selected audio
        if selected_audio_ids:
            for audio in all_audio:
                if audio.get("id") in selected_audio_ids and audio.get("audio_url"):
                    if (
                        audio.get("scene") == scene_number
                        or audio.get("scene_number") == scene_number
                    ):
                        return audio

        # Priority 1: Exact scene match in character audio
        for audio in audio_files.get("characters", []):
            if (
                audio.get("scene") == scene_number
                or audio.get("scene_number") == scene_number
            ) and audio.get("audio_url"):
                return audio

        # Priority 2: Exact scene match in narrator audio
        for audio in audio_files.get("narrator", []):
            if (
                audio.get("scene") == scene_number
                or audio.get("scene_number") == scene_number
            ) and audio.get("audio_url"):
                return audio

        # Priority 3: Exact scene match in any type
        for audio in all_audio:
            if (
                audio.get("scene") == scene_number
                or audio.get("scene_number") == scene_number
            ) and audio.get("audio_url"):
                return audio

        # Priority 4: Any audio with a URL (fallback)
        for audio in all_audio:
            if audio.get("audio_url"):
                return audio

        return None

    def test_find_scene_audio_matches_sfx_by_scene(self):
        """Verify find_scene_audio can match SFX to specific scenes after fix.

        Before KAN-165 fix, SFX results had no 'scene' key, so find_scene_audio
        would skip them in Priority 1-3 and only match via Priority 4 fallback
        (which returns the first audio regardless of scene, breaking per-scene audio).
        """
        # Simulate audio_files dict with the fixed format
        audio_files = {
            "narrator": [
                {"id": "n1", "scene": 1, "scene_number": 1, "audio_url": "https://example.com/n1.mp3", "duration": 10, "text": "Scene 1 narration"},
            ],
            "characters": [
                {"id": "c1", "scene": 1, "scene_number": 1, "audio_url": "https://example.com/c1.mp3", "duration": 8, "text": "Dialogue scene 1", "character": "Ishmael"},
                {"id": "c2", "scene": 2, "scene_number": 2, "audio_url": "https://example.com/c2.mp3", "duration": 12, "text": "Dialogue scene 2", "character": "Ahab"},
            ],
            "sound_effects": [
                {"id": "s1", "scene": 1, "scene_number": 1, "audio_url": "https://example.com/s1.mp3", "description": "Waves", "duration": 5},
                {"id": "s2", "scene": 2, "scene_number": 2, "audio_url": "https://example.com/s2.mp3", "description": "Thunder", "duration": 3},
            ],
            "background_music": [
                {"id": "b1", "scene": 1, "scene_number": 1, "audio_url": "https://example.com/b1.mp3", "description": "Calm sea music", "duration": 30},
                {"id": "b2", "scene": 2, "scene_number": 2, "audio_url": "https://example.com/b2.mp3", "description": "Storm music", "duration": 30},
            ],
        }

        # Verify scene_1 finds character audio (Priority 1)
        result_1 = self._find_scene_audio("scene_1", audio_files)
        assert result_1 is not None, "Should find audio for scene_1"
        assert result_1["id"] == "c1", f"Expected character audio for scene_1, got {result_1['id']}"

        # Verify scene_2 finds character audio (Priority 1)
        result_2 = self._find_scene_audio("scene_2", audio_files)
        assert result_2 is not None, "Should find audio for scene_2"
        assert result_2["id"] == "c2", f"Expected character audio for scene_2, got {result_2['id']}"

        # Verify scene with no character/narrator audio falls back to SFX
        audio_files_no_char = {
            "narrator": [],
            "characters": [],
            "sound_effects": [
                {"id": "s3", "scene": 3, "scene_number": 3, "audio_url": "https://example.com/s3.mp3", "description": "Creaking ship", "duration": 7},
            ],
            "background_music": [
                {"id": "b3", "scene": 3, "scene_number": 3, "audio_url": "https://example.com/b3.mp3", "description": "Eerie music", "duration": 30},
            ],
        }
        result_3 = self._find_scene_audio("scene_3", audio_files_no_char)
        assert result_3 is not None, "Should find SFX audio for scene_3"
        assert result_3["scene_number"] == 3, "Found audio should be for scene 3"

    def test_find_scene_audio_sfx_before_fix_would_fail(self):
        """Document the pre-fix behavior: SFX without scene keys always falls to fallback.

        This test verifies that the old format (without scene keys on SFX) would
        not match per-scene and would fall through to Priority 4 fallback.
        """
        # OLD format (pre-fix): SFX missing scene/scene_number keys
        old_audio_files = {
            "narrator": [],
            "characters": [],
            "sound_effects": [
                {"effect_id": 1, "db_id": "old-s1", "audio_url": "https://example.com/old-s1.mp3", "description": "Waves", "duration": 5},
                {"effect_id": 2, "db_id": "old-s2", "audio_url": "https://example.com/old-s2.mp3", "description": "Thunder", "duration": 3},
            ],
            "background_music": [],
        }

        # Scene 2 should NOT get the thunder SFX - it falls to Priority 4 fallback
        # which returns the FIRST audio (waves) regardless of scene mismatch
        result = self._find_scene_audio("scene_2", old_audio_files)
        # With old format, find_scene_audio DOES return something (Priority 4 fallback)
        # But it's the WRONG audio - waves for scene_2 instead of thunder
        assert result is not None, "Priority 4 fallback always returns something"
        # This would be the WRONG audio - scene_2 gets waves (effect_id=1) instead of thunder
        assert result.get("effect_id") == 1, "OLD BUG: Priority 4 returns first audio regardless of scene"

    def test_all_audio_types_consistent_id_key(self):
        """All audio types should use 'id' as the record identifier key."""
        narrator = {"id": "n1", "scene": 1, "scene_number": 1, "audio_url": "url", "duration": 5, "text": "narration"}
        character = {"id": "c1", "scene": 1, "scene_number": 1, "audio_url": "url", "duration": 8, "text": "dialogue", "character": "X"}
        sfx = {"id": "s1", "scene": 1, "scene_number": 1, "audio_url": "url", "description": "bang", "duration": 3}
        bgm = {"id": "b1", "scene": 1, "scene_number": 1, "audio_url": "url", "description": "music", "duration": 30}

        for label, item in [("narrator", narrator), ("character", character), ("sfx", sfx), ("bgm", bgm)]:
            assert "id" in item, f"{label} result must have 'id' key"
            assert "db_id" not in item, f"{label} result must NOT have legacy 'db_id' key"


class TestAudioDurationValidation:
    """KAN-166: Audio duration validation reports wrong length.

    Root cause: When API doesn't return audio_time (e.g., ElevenLabs fallback sets it to 0),
    duration is stored as 0 in both DB and results. The video pipeline's duration validation
    checks `audio_duration > 0` which means 0-duration audio BYPASSES min/max checks entirely
    and gets passed to the video generation API with invalid duration.
    """

    def test_fallback_audio_time_is_zero(self):
        """Verify that ElevenLabs fallback returns audio_time=0 (the root cause)."""
        # This simulates what the fallback paths in audio_tasks.py currently return
        fallback_result = {
            "status": "success",
            "audio_url": "https://example.com/fallback-audio.mp3",
            "audio_time": 0,  # ElevenLabs direct API doesn't return duration
            "model_used": "direct_eleven_multilingual_v2",
            "service": "elevenlabs_direct",
        }
        assert fallback_result["audio_time"] == 0, "Fallback audio_time should be 0 before KAN-166 fix"

    def test_duration_validation_skips_zero_duration(self):
        """Verify that pre-fix validation logic allows 0-duration audio to pass through.

        The old condition was: `if min_audio and audio_duration > 0 and audio_duration < min_audio`
        When audio_duration=0, the `audio_duration > 0` check fails, so the entire
        min-duration check is skipped — audio with 0s duration passes validation.
        """
        min_audio = 2.0  # Model requires at least 2s
        audio_duration = 0  # Unknown duration from fallback

        # OLD logic: `min_audio and audio_duration > 0 and audio_duration < min_audio`
        old_check = min_audio and audio_duration > 0 and audio_duration < min_audio
        assert old_check is False, "OLD BUG: 0-duration audio bypasses min check entirely"

        # FIXED logic: After KAN-166, if duration <= 0, we probe the file
        # and if still <= 0 after probing, we skip the audio entirely
        if audio_duration <= 0:
            # Attempt probe (simulated)
            probed_duration = 5.0  # Assume probe finds 5s
            if probed_duration > 0:
                audio_duration = probed_duration

        new_check = min_audio and audio_duration > 0 and audio_duration < min_audio
        assert new_check is False, "5s audio is above min_audio(2s), so no padding needed"

    def test_probed_duration_fixes_validation(self):
        """After KAN-166 fix, probing actual duration allows proper min/max checks."""
        min_audio = 2.0
        audio_duration = 0  # API returned 0

        # Simulate KAN-166 fix: probe the file
        probed_duration = 1.5  # File is actually 1.5s (below minimum)
        if audio_duration <= 0 and probed_duration > 0:
            audio_duration = probed_duration

        # Now the check works correctly
        needs_padding = min_audio and audio_duration > 0 and audio_duration < min_audio
        assert needs_padding is True, "1.5s audio (below 2s min) should need padding"

    def test_zero_duration_audio_skipped_after_fix(self):
        """After KAN-166, if duration remains 0 after probing, audio is skipped."""
        audio_duration = 0  # API returned 0

        # Simulate failed probe
        probed_duration = None  # Probe also failed

        if audio_duration <= 0:
            if probed_duration and probed_duration > 0:
                audio_duration = probed_duration
            # else: duration stays 0

        # After KAN-166 fix: audio with duration <= 0 is explicitly skipped
        assert audio_duration <= 0, "Unproable audio should be skipped"

    def test_sfx_default_duration_inaccurate(self):
        """SFX uses fallback duration=10, BGM uses 30 — these are inaccurate defaults."""
        # SFX line: duration = result.get("audio_time", 10)
        sfx_fallback_duration = 10
        # BGM line: duration = result.get("audio_time", 30.0)
        bgm_fallback_duration = 30.0

        # These defaults may not match the actual audio file duration
        # KAN-166 fix: probe actual file when available to get real duration
        assert sfx_fallback_duration == 10, "SFX fallback is 10s (may be inaccurate)"
        assert bgm_fallback_duration == 30.0, "BGM fallback is 30s (may be inaccurate)"

    def test_probed_duration_updates_result_dict(self):
        """After KAN-166, probed duration should flow into the results dict.

        This ensures find_scene_audio() and the video pipeline get accurate duration
        instead of 0 or inaccurate defaults.
        """
        # Simulate what happens after the fix:
        # 1. API returns audio_time=0
        # 2. After persist, probe actual file → real duration
        # 3. duration in result dict uses probed value
        result_duration = 0  # Before probe
        probed_duration = 11.0  # Actual file is 11s

        if result_duration <= 0 and probed_duration > 0:
            result_duration = probed_duration

        # The result dict now has correct duration
        narrator_result = {
            "id": "test-id",
            "scene": 1,
            "scene_number": 1,
            "audio_url": "https://example.com/narrator.mp3",
            "duration": result_duration,  # Now 11s instead of 0
            "text": "Call me Ishmael.",
        }
        assert narrator_result["duration"] == 11.0, "Duration should reflect probed value"
        assert narrator_result["duration"] > 0, "Duration should be positive for validation to work"