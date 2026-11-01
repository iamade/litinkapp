import pytest

class TestImageModelConfig:
    """KAN-164: Image generation fails with invalid model ID"""
    def test_all_configured_models_are_valid_strings(self):
        """All model IDs in config should be non-empty strings"""
        from app.core.model_config import IMAGE_MODEL_CONFIG
        assert IMAGE_MODEL_CONFIG, "IMAGE_MODEL_CONFIG must not be empty"
        for tier, config in IMAGE_MODEL_CONFIG.items():
            # ModelConfig declares primary, fallback, then optional fallback2..fallback13.
            models = [config.primary, config.fallback]
            models.extend(getattr(config, f'fallback{i}') for i in range(2, 14))
            # primary and fallback are required fields, so they must be set.
            assert config.primary, f'primary missing in {tier}'
            assert config.fallback, f'fallback missing in {tier}'
            for model in models:
                if model:
                    assert isinstance(model, str) and len(model) > 0, f'Invalid model ID in {tier}: {model}'
