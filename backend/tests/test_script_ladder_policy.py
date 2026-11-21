"""Offline script routing policy checks: no provider calls or service startup."""
import pytest
from app.core.model_config import ModelTier, SCRIPT_MODEL_CONFIG, get_model_config

@pytest.mark.parametrize('tier', list(SCRIPT_MODEL_CONFIG))
def test_script_prefers_existing_ollama_and_excludes_featherless(tier):
    models = SCRIPT_MODEL_CONFIG[tier].models
    assert models[0].startswith('ollama/')
    assert all(not model.startswith('featherless/') for model in models)
    assert len(models) == len(set(models))
    assert all(not model.startswith(('ollama2/', 'qwen/', 'minimax-portal/')) for model in models)
    zai_positions = [i for i, model in enumerate(models) if model.startswith('zai/')]
    assert zai_positions
    assert min(zai_positions) >= 5

@pytest.mark.parametrize('tier,limit,temp', [
    (ModelTier.FREE,4000,0.7), (ModelTier.BASIC,4000,0.7),
    (ModelTier.STANDARD,8000,0.7), (ModelTier.PREMIUM,8000,0.75),
    (ModelTier.PRO,16000,0.8),
])
def test_script_request_limits_remain_tier_specific(tier,limit,temp):
    config = SCRIPT_MODEL_CONFIG[tier]
    assert config.max_tokens == limit
    assert config.temperature == temp

def test_professional_alias_uses_pro_script_policy():
    assert get_model_config('script','professional') is SCRIPT_MODEL_CONFIG[ModelTier.PRO]

def test_historical_pro_subscription_keeps_standard_limits():
    assert get_model_config('script','pro') is SCRIPT_MODEL_CONFIG[ModelTier.STANDARD]

def test_enterprise_uses_professional_script_policy():
    assert get_model_config('script','enterprise') is SCRIPT_MODEL_CONFIG[ModelTier.PRO]
