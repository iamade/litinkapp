Restructured Model Configuration (Tiered)
1. Script Generation

Free → OpenRouter free / ultra-cheap LLMs

Basic → DeepSeek, Mistral

Standard → Claude 3 Haiku, GPT-3.5 Turbo

Pro → GPT-4o-mini, Claude 3.5 Sonnet

Premium → GPT-4o, Claude 3 Opus

Enterprise → Custom fine-tuned models (optional RAG + customer private datasets)

2. Image Generation

Free → ModelsLab v7 (Google Imagen 4 Ultra)

Basic → ModelsLab v7 (Imagen 4 Fast)

Standard → HuggingFace diffusion models (e.g., Stable Diffusion XL, Playground v2.5)

Pro → NANO BANANA
Premium → Seedream-4-High-Res ($0.02/image), OpenAI DALL-E-3 ($0.04/image)

Enterprise → Custom fine-tuned diffusion pipeline (private LoRA + DreamBooth)

. Video Generation

Free → ModelsLab V7 (SeedDance / ULTRA) + FFmpeg backend (limit to 2 short clips/month, 720p, watermark)

Basic → ModelsLab V7 (FAST Veo2 ~$0.05/s), capped at 720p, 10 videos/month

Standard → HuggingFace / Stability AI open video models (like SVD / Stable Video Diffusion XL), 1080p, 30 videos/month

Pro → Ray3 Draft / Kling AI SDR (~$0.08–0.12/s est). Up to 4K, higher length, 100 videos/month

Premium → Veo3 with Audio / Ray3 HDR+EXR (~$0.10–0.15/s). 4K+, advanced features, 100–200 videos/month, API priority

Enterprise → Hybrid Infra: Veo3 + Kling AI + Ray3 with OpenShot timeline editor. White-label, unlimited, dedicated GPU cluster.

4. Audio / Voice

Free → ModelsLab (ElevenLabs clone, cheap TTS)

Paid (Basic → Enterprise) → ElevenLabs Direct (multilingual v2, $0.30 / 1K chars), scaling voices and languages per tier

🔹 Cost → Margin Mapping Example (Per 5-min 720p video)

Veo2 (Basic): ~$15 cost → priced at $30 (≈50% margin)

Ray3 Draft / Kling SDR (Pro): ~$24 cost → priced at $50 (≈52% margin)

Veo3 HDR (Premium): ~$30 cost → priced at $75 (≈60% margin)

Enterprise: Negotiated — always price 2–3× GPU cost to lock 60%+ margin.


| Tier           | Monthly Price  | Avg. Cost/User  | Margin | Script (LLMs)                         | Image Gen                                             | Audio/Voice                                        | Video Gen                                                                |
| -------------- | -------------- | --------------- | ------ | ------------------------------------- | ----------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------ |
| **Free**       | $0             | $2–3 subsidized | N/A    | OpenRouter free (QwQ-32B, LLaMA-3B)   | ModelsLab v7 (Imagen 4 Ultra)                         | ModelsLab clone (~$0.001/1K chars)                 | ModelsLab SeedDance + FFmpeg (2 Narration vids/mo, 720p, watermark and wan2.5-i2v-preview fallback Ray2 1 character dialogue video/month  720p, watermark )                |
| **Basic**      | $19            | $8–10           | 47–58% | DeepSeek Chat / Mistral-7B            | ModelsLab v7 (Imagen 4 Fast)                          | ElevenLabs (entry, ~$0.30/1K chars, capped)        | fallback ModelsLab Wan2.2 as fallback (~$0.05/s, 720p, 10 narration vids/mo and wan2.5-i2v-preview fall back Ray2 6 character dialogue )                              |
| **Standard**   | $49            | $20–25          | 49–59% | Claude 3 Haiku / GPT-3.5 Turbo        | HuggingFace SDXL / Playground v2.5                    | ElevenLabs multilingual                            | HuggingFace SVD XL / Stability (1080p, 30 vids/mo)                       |
| **Pro**        | $99            | $40–50          | 49–60% | GPT-4o-mini / Claude 3.5 Sonnet       | **Nano Banana API** (high-quality image gen)          | ElevenLabs advanced voices                         | Ray3 Draft / Kling SDR (4K, 100 vids/mo)                                 |
| **Premium**    | $299           | $120–150        | 50–60% | GPT-4o / Claude 3 Opus                | Seedream-4-High-Res ($0.02/img), DALL-E 3 ($0.04/img) | ElevenLabs pro-tier (cloned + multilingual studio) | Veo3 + Ray3 HDR (~$0.10/s, 4K HDR/EXR, 100–200 vids/mo, API priority)    |
| **Enterprise** | Custom (>$999) | $400–600+       | 60–70% | Custom fine-tuned GPT/Claude with RAG | Custom diffusion pipelines, private LoRAs             | ElevenLabs enterprise + brand voice                | Hybrid Veo3+Kling+Ray3 with OpenShot timeline editing, white-label infra |
