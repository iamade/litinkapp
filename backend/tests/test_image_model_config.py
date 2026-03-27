import pytest

class TestImageModelConfig:
    """KAN-164: Image generation fails with invalid model ID"""
    def test_all_configured_models_are_valid_strings(self):
        """All model IDs in config should be non-empty strings"""
        from app.core.services.model_config import IMAGE_MODEL_CONFIG
        for tier, config in IMAGE_MODEL_CONFIG.items():
            models = [config.primary_model]
            if hasattr(config, 'fallback_models'):
                models.extend(config.fallback_models)
            for model in models:
                if model:
                    assert isinstance(model, str) and len(model) > 0, f'Invalid model ID in {tier}: {model}'
