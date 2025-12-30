# AI Strategy & Pricing

## AI Model Strategy

Our AI strategy employs a robust multi-tiered approach designed to balance performance, cost, and availability. We utilize a "waterfall" fallback system: requests are first routed to the **Primary** model. If that model is unavailable, rate-limited, or fails, the system automatically attempts the **Secondary (Fallback)** model, and finally the **Fallback 2** model.

### Text & Script Generation Strategy

Based on the [LMSYS Chatbot Arena](https://lmarena.ai/) "Creative Writing" Leaderboard (Top 20), we have designed a tiered strategy that prioritizes the most capable models for advanced users while ensuring efficient, high-quality generation for all tiers. **Qwen** has been selected as a superior alternative to Grok for our specific use cases. All text and script generation models are accessed via **OpenRouter** to ensure reliable connectivity and fallback handling.

| Tier | Primary Model | Secondary (Fallback) | Fallback 2 |
| :--- | :--- | :--- | :--- |
| **Free** | **DeepSeek-v3.2-thinking** | **Qwen** (Efficient) | **ChatGPT-4o-latest** |
| **Basic** | **Qwen** (Replacing Grok-4.1) | **ChatGPT-4o-latest** | **Ernie-5.0** |
| **Standard** | **Qwen-Thinking** (Replacing Grok-Thinking) | **GPT-4.5-preview** | **Claude-Opus-4.1** |
| **Premium** | **Claude-Sonnet-4.5** | **Gemini-3-flash (Thinking)** | **Qwen-Thinking** |
| **Professional** | **Gemini-3-flash** | **Gemini-2.5-pro** | **GPT-5.1** |
| **Enterprise** | **Gemini-3-pro** (#1 Creative) | **Claude-Opus-4.5** | **GPT-5.1-high** |

### Media Generation Strategy

#### Image Generation Strategy
Leveraging the top performing models from the leaderboard to ensure optimal quality-to-cost ratios for each tier. **ModelsLab** is used as the primary gateway for supported models to streamline API management.

| Tier | Primary Model | Secondary (Fallback) | Fallback 2 |
| :--- | :--- | :--- | :--- |
| **Free** | **Hunyuan-Image-3.0** (Direct API) | **Seedream-4.5** (ModelsLab) | **Flux-2-Dev** (ModelsLab) |
| **Basic** | **Nano Banana / Gemini-2.5** (Direct API) | **Flux-2-Dev** (ModelsLab) | **Hunyuan-Image-3.0** (Direct API) |
| **Standard** | **Flux-2-Pro** (ModelsLab) | **Flux-2-Flex** (Direct API) | **Nano Banana / Gemini-2.5** (Direct API) |
| **Premium** | **Flux-2-Max** (ModelsLab) | **Nano Banana Pro / Gemini-3** (Direct API) | **Flux-2-Pro** (ModelsLab) |
| **Professional** | **Nano Banana Pro / Gemini-3** (Direct API) | **Flux-2-Max** (ModelsLab) | **GPT-Image-1.5** (Direct API) |
| **Enterprise** | **GPT-Image-1.5** (Direct API) | **Nano Banana Pro / Gemini-3** (Direct API) | **Flux-2-Max** (ModelsLab) |

#### Video Generation Strategy
Optimizing for high-fidelity motion and consistency while managing compute costs. **ModelsLab** aggregates top video models, while Google's **Veo** is accessed directly for enterprise-grade performance.

| Tier | Primary Model | Secondary (Fallback) | Fallback 2 |
| :--- | :--- | :--- | :--- |
| **Free** | **Seedance-v1-Pro** (ModelsLab) | **Veo-3-Fast** (Direct API) | **Kling-2.5-Turbo** (ModelsLab) |
| **Basic** | **Kling-2.5-Turbo-1080p** (ModelsLab) | **Seedance-v1-Pro** (ModelsLab) | **Veo-3-Fast** (Direct API) |
| **Standard** | **Veo-3-Fast-Audio** (Direct API) | **Kling-2.6-Pro** (ModelsLab) | **Wan2.5-I2V-Preview** (ModelsLab) |
| **Premium** | **Veo-3-Audio** (Direct API) | **Wan2.5-I2V-Preview** (ModelsLab) | **Veo-3-Fast-Audio** (Direct API) |
| **Professional** | **Veo-3.1-Fast-Audio** (Direct API) | **Veo-3-Audio** (Direct API) | **Wan2.5-I2V-Preview** (ModelsLab) |
| **Enterprise** | **Veo-3.1-Audio** (Direct API) | **Veo-3.1-Fast-Audio** (Direct API) | **Wan2.5-I2V-Preview** (ModelsLab) |

#### Audio Generation Strategy

| Tier | Primary Model | Secondary (Fallback) | Fallback 2 |
| :--- | :--- | :--- | :--- |
| **All Tiers** | **ElevenLabs Multilingual v2** | **ElevenLabs Turbo v2** | **ElevenLabs English v1** |

---

## Subscription Pricing Tiers

We offer flexible subscription plans tailored to different creator needs.

| Feature | Free | Basic | Standard | Premium | Professional | Enterprise |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Target Audience** | Trial / Hobbyist | Casual Creators | Serious Creators | Power Users | Studios / Agencies | Large Organizations |
| **Monthly Price** | **$0** | **$29** | **$79** | **$199** | **$499** | **Custom** |
| **Videos per Month** | 2 | 8 | 20 | 60 | 150 | Unlimited |
| **Max Resolution** | 720p | 720p | 1080p | **4K** | **4K** | **8K** |
| **Video Duration** | 5 min | 15 min | 30 min | 60 min | 90 min | Unlimited |
| **Book Uploads** | 3 | 10 | 25 | 100 | Unlimited | Unlimited |
| **Video Books** | 1 | 3 | 10 | 50 | Unlimited | Unlimited |
| **Chapters / Book** | 2 | Unlimited | Unlimited | Unlimited | Unlimited | Unlimited |
| **No Watermark** | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Model Selection** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Voice Cloning** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **API Access** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Support** | Community | Email | Priority Email | Priority Email | Dedicated Rep | 24/7 Dedicated |

### Payment Processing Fees
*   **Stripe**: 2.9% + CA$0.30 per successful transaction for domestic cards.

---

### Old Strategy (For Reference)

| Tier | Primary Model | Secondary (Fallback) | Fallback 2 |
| :--- | :--- | :--- | :--- |
| **Free** | **Gemini 2.0 Flash** (clean, fast) | **Llama 3.3 70B** (open source power) | DeepSeek Chat |
| **Basic** | **DeepSeek Chat** (strong reasoning) | **Mistral Nemo** (efficient) | Llama 3.3 70B |
| **Standard** | **Claude 3 Haiku** (fast, creative) | **GPT-3.5 Turbo** (reliable) | DeepSeek Chat |
| **Premium** | **GPT-4o Mini** (smart, efficient) | **Claude 3.5 Sonnet** (high iq) | Claude 3 Haiku |
| **Professional** | **GPT-4o** (omni-model) | **Claude 3 Opus** (reasoning heavy) | GPT-4o Mini |
| **Enterprise** | **GPT-4o** (omni-model) | **Claude 3 Opus** (reasoning heavy) | Claude 3.5 Sonnet |