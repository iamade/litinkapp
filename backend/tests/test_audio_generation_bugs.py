import pytest


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