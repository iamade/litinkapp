# OpenRouter Integration & Implementation Guide

## Quick Start: OpenRouter Setup

### 1. OpenRouter Account Setup
```bash
# 1. Sign up at https://openrouter.ai
# 2. Get your API key from dashboard
# 3. Add to your .env file:
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

### 2. Install OpenRouter Python Client
```bash
# Using OpenAI client (OpenRouter is OpenAI-compatible)
pip install openai httpx pydantic
```

## Implementation Code

### 1. OpenRouter Service Implementation

```python
# backend/app/services/openrouter_service.py
from typing import Dict, Any, Optional, List
import httpx
from openai import AsyncOpenAI
from app.core.config import settings
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class ModelTier(Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"

class OpenRouterService:
    """
    OpenRouter integration for intelligent model routing
    Handles all LLM requests with automatic fallback and cost optimization
    """
    
    # Model configurations with costs (per 1K tokens)
    MODEL_CONFIGS = {
        ModelTier.FREE: {
            "primary": "meta-llama/llama-3.2-3b-instruct",
            "fallback": "google/gemini-flash-1.5-8b",
            "max_tokens": 2000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00006,
            "cost_per_1k_output": 0.00006
        },
        ModelTier.BASIC: {
            "primary": "deepseek/deepseek-chat",
            "fallback": "mistralai/mistral-7b-instruct",
            "max_tokens": 3000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00014,
            "cost_per_1k_output": 0.00028
        },
        ModelTier.STANDARD: {
            "primary": "anthropic/claude-3-haiku-20240307",
            "fallback": "openai/gpt-3.5-turbo",
            "max_tokens": 4000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00025,
            "cost_per_1k_output": 0.00125
        },
        ModelTier.PREMIUM: {
            "primary": "openai/gpt-4o-mini",
            "fallback": "anthropic/claude-3.5-sonnet",
            "max_tokens": 8000,
            "temperature": 0.7,
            "cost_per_1k_input": 0.00015,
            "cost_per_1k_output": 0.00060
        },
        ModelTier.PROFESSIONAL: {
            "primary": "openai/gpt-4o",
            "fallback": "anthropic/claude-3-opus-20240229",
            "max_tokens": 16000,
            "temperature": 0.8,
            "cost_per_1k_input": 0.00250,
            "cost_per_1k_output": 0.01000
        }
    }
    
    def __init__(self):
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY is required")
        
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            default_headers={
                "HTTP-Referer": settings.FRONTEND_URL,  # Optional, for rankings
                "X-Title": "LitinkAI"  # Optional, shows in OpenRouter dashboard
            }
        )
        
        # Initialize cost tracking
        self.cost_tracker = CostTracker()
    
    async def generate_script(
        self,
        content: str,
        user_tier: ModelTier,
        script_type: str = "cinematic",
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Generate script using tier-appropriate model
        """
        config = self.MODEL_CONFIGS[user_tier]
        model = config["fallback"] if use_fallback else config["primary"]
        
        try:
            # Prepare messages based on script type
            messages = self._prepare_script_messages(content, script_type)
            
            # Log the request
            logger.info(f"[OpenRouter] Generating {script_type} script with {model} for {user_tier.value} tier")
            
            # Make the API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
                stream=False
            )
            
            # Extract content and usage
            generated_content = response.choices[0].message.content
            usage = response.usage
            
            # Calculate cost
            input_cost = (usage.prompt_tokens / 1000) * config["cost_per_1k_input"]
            output_cost = (usage.completion_tokens / 1000) * config["cost_per_1k_output"]
            total_cost = input_cost + output_cost
            
            # Track the cost
            await self.cost_tracker.track(
                user_tier=user_tier,
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                cost=total_cost
            )
            
            return {
                "status": "success",
                "content": generated_content,
                "model_used": model,
                "tier": user_tier.value,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost": total_cost
                }
            }
            
        except Exception as e:
            logger.error(f"[OpenRouter] Error with {model}: {str(e)}")
            
            # Try fallback if not already using it
            if not use_fallback:
                logger.info(f"[OpenRouter] Attempting fallback model")
                return await self.generate_script(
                    content=content,
                    user_tier=user_tier,
                    script_type=script_type,
                    use_fallback=True
                )
            
            # If fallback also failed, return error
            return {
                "status": "error",
                "error": str(e),
                "model_attempted": model,
                "tier": user_tier.value
            }
    
    def _prepare_script_messages(self, content: str, script_type: str) -> List[Dict[str, str]]:
        """
        Prepare messages for different script types
        """
        system_prompts = {
            "cinematic": """You are a professional screenwriter. Convert the provided content into a cinematic screenplay format with:
                - Proper scene headings (INT./EXT. LOCATION - TIME)
                - Character names in uppercase when introduced
                - Dialogue and action descriptions
                - Visual descriptions for scene generation""",
            
            "narration": """You are a professional narrator. Convert the content into an engaging narration script with:
                - Rich, descriptive voice-over text
                - Scene descriptions for visual context
                - Emotional and atmospheric descriptions
                - Clear pacing and transitions""",
            
            "educational": """You are an educational content creator. Convert the content into a clear, educational script with:
                - Clear learning objectives
                - Step-by-step explanations
                - Visual cues for graphics and demonstrations
                - Engaging but informative tone""",
            
            "marketing": """You are a marketing copywriter. Convert the content into a compelling marketing script with:
                - Hook in the first 3 seconds
                - Clear value proposition
                - Call-to-action
                - Emotional engagement"""
        }
        
        system_prompt = system_prompts.get(script_type, system_prompts["cinematic"])
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Convert this content into a {script_type} script:\n\n{content}"}
        ]
    
    async def analyze_content(
        self,
        content: str,
        user_tier: ModelTier,
        analysis_type: str = "summary"
    ) -> Dict[str, Any]:
        """
        Analyze content for various purposes (summary, keywords, difficulty, etc.)
        """
        config = self.MODEL_CONFIGS[user_tier]
        model = config["primary"]
        
        analysis_prompts = {
            "summary": "Provide a concise summary of this content in 2-3 sentences.",
            "keywords": "Extract 5-10 key topics or themes from this content.",
            "difficulty": "Assess the reading difficulty level of this content (elementary, middle school, high school, college, professional).",
            "genre": "Identify the genre and style of this content.",
            "characters": "List all characters mentioned in this content with brief descriptions."
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["summary"])
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a content analyst."},
                    {"role": "user", "content": f"{prompt}\n\nContent:\n{content[:3000]}"}  # Limit content for analysis
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for analysis
            )
            
            return {
                "status": "success",
                "analysis_type": analysis_type,
                "result": response.choices[0].message.content,
                "model_used": model
            }
            
        except Exception as e:
            logger.error(f"[OpenRouter] Analysis error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "analysis_type": analysis_type
            }
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models from OpenRouter
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
                )
                
                if response.status_code == 200:
                    models = response.json()["data"]
                    # Filter and format models
                    return [
                        {
                            "id": model["id"],
                            "name": model.get("name", model["id"]),
                            "context_length": model.get("context_length", 4096),
                            "pricing": model.get("pricing", {}),
                            "supported": model["id"] in [
                                config["primary"] for config in self.MODEL_CONFIGS.values()
                            ]
                        }
                        for model in models
                    ]
                else:
                    logger.error(f"Failed to fetch models: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching available models: {str(e)}")
            return []


class CostTracker:
    """
    Track costs for OpenRouter API usage
    """
    
    def __init__(self):
        self.redis_client = None  # Initialize with Redis connection
        self.supabase_client = None  # Initialize with Supabase connection
    
    async def track(
        self,
        user_tier: ModelTier,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ):
        """
        Track API usage and costs
        """
        # Store in database for billing
        # This is a simplified version - expand based on your needs
        logger.info(f"[Cost Tracking] Model: {model}, Tokens: {input_tokens + output_tokens}, Cost: ${cost:.6f}")
        
        # You would typically:
        # 1. Store in database
        # 2. Update user's usage quota
        # 3. Check against limits
        # 4. Send alerts if needed
```

### 2. Subscription Manager Implementation

```python
# backend/app/services/subscription_manager.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import stripe
from app.core.database import get_supabase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SubscriptionTier(Enum):
    FREE = "free"
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class SubscriptionManager:
    """
    Manages user subscriptions and tier-based access
    """
    
    TIER_LIMITS = {
        SubscriptionTier.FREE: {
            "videos_per_month": 2,
            "max_video_duration": 60,  # seconds
            "max_resolution": "720p",
            "watermark": True,
            "priority": 0,
            "support": "community",
            "api_access": False,
            "price_monthly": 0
        },
        SubscriptionTier.BASIC: {
            "videos_per_month": 10,
            "max_video_duration": 180,
            "max_resolution": "720p",
            "watermark": False,
            "priority": 1,
            "support": "email",
            "api_access": False,
            "price_monthly": 19
        },
        SubscriptionTier.STANDARD: {
            "videos_per_month": 30,
            "max_video_duration": 300,
            "max_resolution": "1080p",
            "watermark": False,
            "priority": 2,
            "support": "priority_email",
            "api_access": False,
            "voice_cloning": True,
            "price_monthly": 49
        },
        SubscriptionTier.PREMIUM: {
            "videos_per_month": 100,
            "max_video_duration": 600,
            "max_resolution": "4K",
            "watermark": False,
            "priority": 3,
            "support": "chat",
            "api_access": True,
            "voice_cloning": True,
            "custom_voices": 5,
            "price_monthly": 99
        },
        SubscriptionTier.PROFESSIONAL: {
            "videos_per_month": 500,  # Soft limit
            "max_video_duration": 1800,
            "max_resolution": "4K",
            "watermark": False,
            "priority": 4,
            "support": "phone",
            "api_access": True,
            "voice_cloning": True,
            "custom_voices": "unlimited",
            "custom_models": True,
            "price_monthly": 299
        },
        SubscriptionTier.ENTERPRISE: {
            "videos_per_month": "unlimited",
            "max_video_duration": "unlimited",
            "max_resolution": "8K",
            "watermark": False,
            "priority": 5,
            "support": "dedicated",
            "api_access": True,
            "white_label": True,
            "custom_deployment": True,
            "sla": "99.9%",
            "price_monthly": "custom"
        }
    }
    
    def __init__(self, supabase_client=None):
        self.supabase = supabase_client
        stripe.api_key = settings.STRIPE_SECRET_KEY
    
    async def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """
        Get user's current subscription tier
        """
        try:
            # Check database for user subscription
            result = self.supabase.table('user_subscriptions').select('*').eq(
                'user_id', user_id
            ).eq('status', 'active').single().execute()
            
            if result.data:
                return SubscriptionTier(result.data['tier'])
            else:
                # Default to free tier
                return SubscriptionTier.FREE
                
        except Exception as e:
            logger.error(f"Error getting user tier: {str(e)}")
            return SubscriptionTier.FREE
    
    async def check_usage_limits(
        self,
        user_id: str,
        resource_type: str = "video"
    ) -> Dict[str, Any]:
        """
        Check if user has exceeded their usage limits
        """
        tier = await self.get_user_tier(user_id)
        limits = self.TIER_LIMITS[tier]
        
        # Get current month's usage
        current_period_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        
        usage_result = self.supabase.table('usage_logs').select('*').eq(
            'user_id', user_id
        ).gte('created_at', current_period_start.isoformat()).execute()
        
        video_count = len([u for u in usage_result.data if u['resource_type'] == 'video'])
        
        return {
            "tier": tier.value,
            "limits": limits,
            "current_usage": {
                "videos": video_count,
                "period_start": current_period_start.isoformat(),
                "period_end": (current_period_start + timedelta(days=30)).isoformat()
            },
            "can_generate": video_count < limits["videos_per_month"] if isinstance(limits["videos_per_month"], int) else True,
            "videos_remaining": max(0, limits["videos_per_month"] - video_count) if isinstance(limits["videos_per_month"], int) else "unlimited"
        }
    
    async def create_checkout_session(
        self,
        user_id: str,
        tier: SubscriptionTier,
        success_url: str,
        cancel_url: str
    ) -> Dict[str, Any]:
        """
        Create Stripe checkout session for subscription
        """
        try:
            # Get price ID for tier (you need to create these in Stripe Dashboard)
            price_ids = {
                SubscriptionTier.BASIC: settings.STRIPE_BASIC_PRICE_ID,
                SubscriptionTier.STANDARD: settings.STRIPE_STANDARD_PRICE_ID,
                SubscriptionTier.PREMIUM: settings.STRIPE_PREMIUM_PRICE_ID,
                SubscriptionTier.PROFESSIONAL: settings.STRIPE_PROFESSIONAL_PRICE_ID
            }
            
            price_id = price_ids.get(tier)
            if not price_id:
                raise ValueError(f"No price ID configured for tier: {tier.value}")
            
            # Create Stripe checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user_id,
                    'tier': tier.value
                }
            )
            
            return {
                "checkout_url": session.url,
                "session_id": session.id
            }
            
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise
    
    async def handle_subscription_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ):
        """
        Handle Stripe webhook events for subscriptions
        """
        if event_type == 'checkout.session.completed':
            session = event_data['object']
            user_id = session['metadata']['user_id']
            tier = session['metadata']['tier']
            
            # Update user subscription in database
            self.supabase.table('user_subscriptions').upsert({
                'user_id': user_id,
                'tier': tier,
                'status': 'active',
                'stripe_customer_id': session['customer'],
                'stripe_subscription_id': session['subscription'],
                'current_period_start': datetime.now().isoformat(),
                'current_period_end': (datetime.now() + timedelta(days=30)).isoformat(),
                'video_count_limit': self.TIER_LIMITS[SubscriptionTier(tier)]['videos_per_month'],
                'video_count_used': 0
            }).execute()
            
            logger.info(f"Subscription activated for user {user_id}: {tier}")
            
        elif event_type == 'customer.subscription.deleted':
            subscription = event_data['object']
            
            # Downgrade to free tier
            result = self.supabase.table('user_subscriptions').update({
                'status': 'cancelled',
                'tier': 'free'
            }).eq('stripe_subscription_id', subscription['id']).execute()
            
            logger.info(f"Subscription cancelled: {subscription['id']}")
```

### 3. Updated Configuration

```python
# backend/app/core/config.py - Add these settings
class Settings(BaseSettings):
    # ... existing settings ...
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    
    # Stripe Subscription Price IDs
    STRIPE_BASIC_PRICE_ID: Optional[str] = None
    STRIPE_STANDARD_PRICE_ID: Optional[str] = None
    STRIPE_PREMIUM_PRICE_ID: Optional[str] = None
    STRIPE_PROFESSIONAL_PRICE_ID: Optional[str] = None
    
    # Rate Limiting per Tier (requests per minute)
    RATE_LIMITS = {
        "free": 10,
        "basic": 30,
        "standard": 60,
        "premium": 120,
        "professional": 300,
        "enterprise": 1000
    }
```

### 4. API Endpoint Updates

```python
# backend/app/api/v1/video_generation.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.openrouter_service import OpenRouterService, ModelTier
from app.services.subscription_manager import SubscriptionManager
from app.core.auth import get_current_active_user

router = APIRouter()

@router.post("/generate-video")
async def generate_video(
    request: VideoGenerationRequest,
    current_user: dict = Depends(get_current_active_user),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    openrouter: OpenRouterService = Depends(get_openrouter_service)
):
    """
    Generate video with tier-based model selection
    """
    # Check user's subscription and limits
    usage_check = await subscription_manager.check_usage_limits(current_user['id'])
    
    if not usage_check['can_generate']:
        raise HTTPException(
            status_code=402,
            detail=f"Monthly limit reached. You have used {usage_check['current_usage']['videos']} out of {usage_check['limits']['videos_per_month']} videos. Please upgrade your subscription."
        )
    
    # Get user's tier
    user_tier = await subscription_manager.get_user_tier(current_user['id'])
    model_tier = ModelTier(user_tier.value)
    
    # Generate script using OpenRouter
    script_result = await openrouter.generate_script(
        content=request.content,
        user_tier=model_tier,
        script_type=request.script_type
    )
    
    if script_result['status'] != 'success':
        raise HTTPException(status_code=500, detail="Script generation failed")
    
    # Continue with existing video generation pipeline
    # but use tier-appropriate models for each step
    
    return {
        "status": "processing",
        "job_id": job_id,
        "tier": user_tier.value,
        "estimated_cost": script_result['usage']['estimated_cost']
    }
```

## Testing the Integration

### 1. Test OpenRouter Connection

```python
# test_openrouter.py
import asyncio
from app.services.openrouter_service import OpenRouterService, ModelTier

async def test_openrouter():
    service = OpenRouterService()
    
    # Test with free tier model
    result = await service.generate_script(
        content="A brave knight saves a kingdom from a dragon.",
        user_tier=ModelTier.FREE,
        script_type="cinematic"
    )
    
    print(f"Status: {result['status']}")
    print(f"Model Used: {result['model_used']}")
    print(f"Cost: ${result['usage']['estimated_cost']:.6f}")
    print(f"Generated Script:\n{result['content'][:500]}...")

if __name__ == "__main__":
    asyncio.run(test_openrouter())
```

### 2. Cost Monitoring Dashboard

```python
# backend/app/api/v1/admin.py
@router.get("/cost-analysis")
async def get_cost_analysis(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Get cost analysis for admin dashboard
    """
    # Query usage logs
    query = supabase.table('usage_logs').select('*')
    
    if date_from:
        query = query.gte('created_at', date_from)
    if date_to:
        query = query.lte('created_at', date_to)
    
    usage_data = query.execute()
    
    # Aggregate costs by tier and model
    cost_by_tier = {}
    cost_by_model = {}
    total_cost = 0
    total_revenue = 0
    
    for log in usage_data.data:
        tier = log['tier_at_time']
        model = log['model_used']
        cost = log['cost_usd']
        
        cost_by_tier[tier] = cost_by_tier.get(tier, 0) + cost
        cost_by_model[model] = cost_by_model.get(model, 0) + cost
        total_cost += cost
    
    # Calculate revenue (simplified)
    subscription_data = supabase.table('user_subscriptions').select('*').eq('status', 'active').execute()
    
    for sub in subscription_data.data:
        tier_price = SubscriptionManager.TIER_LIMITS[SubscriptionTier(sub['tier'])]['price_monthly']
        if isinstance(tier_price, (int, float)):
            total_revenue += tier_price
    
    profit_margin = ((total_revenue - total_cost) / total_revenue * 100) if total_revenue > 0 else 0
    
    return {
        "total_cost": total_cost,
        "total_revenue": total_revenue,
        "profit_margin": f"{profit_margin:.1f}%",
        "cost_by_tier": cost_by_tier,
        "cost_by_model": cost_by_model,
        "recommendations": generate_cost_recommendations(cost_by_tier, cost_by_model)
    }
```

## Deployment Checklist

- [ ] Create OpenRouter account and get API key
- [ ] Set up Stripe products and price IDs for each tier
- [ ] Update environment variables
- [ ] Deploy database migrations for new tables
- [ ] Implement rate limiting middleware
- [ ] Set up monitoring and alerting
- [ ] Test with each tier's limits
- [ ] Create admin dashboard for cost monitoring
- [ ] Document API changes for frontend team
- [ ] Set up webhook endpoints for Stripe

## Monitoring & Optimization

### Key Metrics to Track
1. **Cost per video by tier**
2. **Model success/failure rates**
3. **Average response times**
4. **Fallback trigger frequency**
5. **User upgrade/downgrade patterns**
6. **Profit margin by tier**

### Cost Optimization Strategies
1. **Cache common requests** (summaries, analyses)
2. **Batch similar requests** when possible
3. **Use cheaper models for preprocessing**
4. **Implement request deduplication**
5. **Monitor and adjust model selection based on actual costs**

## Support & Troubleshooting

### Common Issues and Solutions

1. **Rate Limiting**: OpenRouter has rate limits. Implement exponential backoff.
2. **Model Availability**: Some models may be temporarily unavailable. Always have fallbacks.
3. **Cost Overruns**: Set up alerts when costs exceed thresholds.
4. **Latency Issues**: Consider caching and regional deployments.

---

*Implementation Guide Version: 1.0*  
*Last Updated: 2024*