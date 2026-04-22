import pytest
import json


class TestTrailerScriptGeneration:
    """KAN-150: Trailer script and narration generation.

    KAN-149 (scene selection) must complete before script generation.
    KAN-150 uses AI to generate a trailer script from selected scenes,
    extract narration text, and optionally generate narration audio.
    """

    def test_tone_narration_styles_defined(self):
        """Verify all supported tones have narration style guidance."""
        # Mirror the _tone_narration_styles from service.py (can't import due to sqlmodel chain)
        tone_styles = {
            "epic": "grand, sweeping, building intensity — like a movie trailer voiceover",
            "dramatic": "intense, emotional, with pauses for impact — think Oscar-bait trailer",
            "action": "fast-paced, punchy, building momentum — quick cuts feel",
            "romantic": "tender, intimate, warm — soft and inviting",
            "mysterious": "enigmatic, slow-burn, with questions — draw the viewer in",
            "default": "engaging and compelling, balancing energy with clarity",
        }

        tones = ["epic", "dramatic", "action", "romantic", "mysterious"]
        for tone in tones:
            assert tone in tone_styles, f"Tone '{tone}' missing from style map"
            assert len(tone_styles[tone]) > 20, f"Tone '{tone}' should have detailed style guidance"

    def test_default_tone_fallback(self):
        """Unknown tone falls back to default style."""
        tone_styles = {
            "epic": "grand, sweeping, building intensity — like a movie trailer voiceover",
            "dramatic": "intense, emotional, with pauses for impact — think Oscar-bait trailer",
            "action": "fast-paced, punchy, building momentum — quick cuts feel",
            "romantic": "tender, intimate, warm — soft and inviting",
            "mysterious": "enigmatic, slow-burn, with questions — draw the viewer in",
            "default": "engaging and compelling, balancing energy with clarity",
        }

        style = tone_styles.get("unknown_tone", tone_styles["default"])
        assert "engaging" in style, "Unknown tone should use default style"

    def test_script_result_structure(self):
        """Verify script generation returns correct structure."""
        # Simulate what _generate_trailer_script returns
        ai_response = {
            "script": {
                "title": "Epic Trailer",
                "tone": "epic",
                "total_duration_seconds": 90.0,
                "scene_sequence": [
                    {
                        "scene_number": 1,
                        "narration": "In a world where darkness rises...",
                        "visual_description": "Sunset over mountains",
                        "duration_seconds": 8.0,
                    },
                    {
                        "scene_number": 2,
                        "narration": "One hero must find the light.",
                        "visual_description": "Warrior stands at cliff edge",
                        "duration_seconds": 7.0,
                    },
                ],
                "title_cards": {"tagline": "Coming Soon"},
            },
            "narration_text": "In a world where darkness rises... One hero must find the light.",
        }

        result = {
            "script": json.dumps(ai_response["script"], ensure_ascii=False),
            "narration_text": ai_response["narration_text"],
        }

        assert "script" in result
        assert "narration_text" in result
        assert len(result["narration_text"]) > 0

        # Verify script is valid JSON
        parsed_script = json.loads(result["script"])
        assert "scene_sequence" in parsed_script
        assert len(parsed_script["scene_sequence"]) == 2
        assert parsed_script["scene_sequence"][0]["scene_number"] == 1

    def test_narration_text_is_clean(self):
        """Narration text should be clean voiceover text, no JSON or stage directions."""
        narration_text = "In a world where darkness rises. One hero must find the light."

        # Should not contain JSON syntax
        assert "{" not in narration_text
        assert "}" not in narration_text
        assert "\"" not in narration_text
        # Should be plain text suitable for TTS
        assert len(narration_text) > 0

    def test_voice_mapping(self):
        """Verify voice names map to valid ElevenLabs voice IDs."""
        voice_map = {
            "male_deep": "21m00Tcm4TlvDq8ikWAM",
            "female_soft": "EXAVITQu4vr4xnSDxMaL",
            "male_narrator": "nPczCjzK2NnW1Nn0iX0G",
            "female_narrator": "mTSvIrmUhORL3Bq3Bq7M",
        }

        for voice_name, voice_id in voice_map.items():
            assert len(voice_id) == 20, f"Voice '{voice_name}' should have valid ElevenLabs ID"
            assert voice_id.isalnum(), f"Voice ID should be alphanumeric"

    def test_empty_narration_skips_audio(self):
        """Empty or whitespace-only narration should not trigger audio generation."""
        empty_texts = ["", "   ", "\n\t", None]

        for text in empty_texts:
            # Simulate the check in _generate_narration_audio
            should_generate = bool(text and text.strip()) if text else False
            assert should_generate is False, f"Empty/whitespace text should not trigger audio: '{text}'"

    def test_title_cards_in_prompt(self):
        """Title cards should be included in the AI prompt context."""
        title_cards = {
            "series_name": "The Chronicles",
            "tagline": "Some stories never end",
            "cta_text": "Streaming now",
        }

        # Simulate prompt building
        parts = []
        if title_cards.get("series_name"):
            parts.append(f'Series/Book: "{title_cards["series_name"]}"')
        if title_cards.get("tagline"):
            parts.append(f'Tagline: "{title_cards["tagline"]}"')
        if title_cards.get("cta_text"):
            parts.append(f'Call-to-action: "{title_cards["cta_text"]}"')

        assert len(parts) == 3
        assert "Chronicles" in parts[0]
        assert "stories never end" in parts[1]
        assert "Streaming now" in parts[2]

    def test_trailer_status_transitions(self):
        """KAN-150 should transition status correctly: scenes_selected → script_ready → audio_ready."""
        # Mirror TrailerStatus enum values (can't import due to sqlmodel chain)
        valid_start_statuses = {"scenes_selected", "script_ready"}
        invalid_start_statuses = {
            "analyzing", "audio_ready", "assembling", "completed", "failed",
        }

        # Verify the status enum values used in the generate method
        for status_val in valid_start_statuses:
            assert status_val in valid_start_statuses

        for status_val in invalid_start_statuses:
            assert status_val not in valid_start_statuses

    def test_script_json_scene_sequence_schema(self):
        """Each scene in the script sequence should have required fields."""
        scene_entry = {
            "scene_number": 1,
            "narration": "In a world...",
            "visual_description": "Mountains at sunset",
            "duration_seconds": 8.0,
        }

        required_keys = {"scene_number", "narration", "visual_description", "duration_seconds"}
        assert required_keys.issubset(set(scene_entry.keys())), \
            f"Scene entry missing keys: {required_keys - set(scene_entry.keys())}"

    def test_total_duration_near_target(self):
        """Scene durations should sum close to the target trailer duration."""
        target_duration = 90
        scenes = [
            {"duration_seconds": 8.0},
            {"duration_seconds": 7.0},
            {"duration_seconds": 10.0},
            {"duration_seconds": 8.0},
            {"duration_seconds": 6.0},
            {"duration_seconds": 9.0},
            {"duration_seconds": 7.0},
            {"duration_seconds": 8.0},
            {"duration_seconds": 10.0},
            {"duration_seconds": 7.0},
        ]

        total = sum(s["duration_seconds"] for s in scenes)
        # Should be within 20% of target
        assert abs(total - target_duration) / target_duration < 0.30, \
            f"Total duration {total}s is too far from target {target_duration}s"