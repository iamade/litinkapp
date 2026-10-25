# Script routing revision — 2026-10-01

Base: staging e6de95dceaa57f056ff839a7d21187640bde33e3. User explicitly requested an isolated versioned change from current staging. This supersedes the repository's default dev-branch/read-only supervisor convention for this bounded patch. Existing merge/deploy approval and Tobi-only push rules remain.

Remove Featherless from all five script configuration slots. Prefer the existing Ollama adapter/account, then preserve existing non-ZAI alternatives in relative order; move ZAI entries to the end. Free uses its existing gemma4:31b; Basic and Standard use existing deepseek-v4-pro:cloud; Premium and Professional/Enterprise use existing kimi-k2.6:cloud. No model IDs are introduced beyond those already present in the script catalog. Model availability and backend commercial entitlement require confirmation before deployment; this patch does not prove live inference.

Standard and Professional previously had no Ollama slot: this adds one existing catalog model for each. Historical subscription 'pro' maps to Standard; 'professional' and 'enterprise' map to the PRO config slot. Token limits, temperature, credit charging and legacy estimated-cost fields are unchanged. Those static cost estimates are not proof of actual provider costs.

Second existing OLLAMA_API_KEY_2 is present in local env files but unused by the current adapter. It remains unused here. Ownership, account rules, commercial eligibility and shared capacity must be verified; no account rotation to circumvent limits. No credential values inspected or copied into this branch.

No MiniMax/Qwen adapter was added; existing MiniMax ladder entries remain but current ProviderRouter cannot execute them. No image/audio/video/embedding configuration change. ZAI backend product entitlement remains a release blocker: Coding Plan access is not generic SaaS API authorization. No provider calls or spend in this verification.

Validation: 13 offline script policy tests pass. Other config AST is identical to base. git diff --check passes. Broader adapter/TTS collection blocked by missing anthropic in the local Python environment. Existing image test fails on its old app.core.services.model_config import, absent on unchanged staging; this is not repaired in this patch.

Rollback: revert the bounded commit / restore model_config.py from base before deployment. Push is queued for Tobi; no merge, deployment or service restart authorized by this patch.
