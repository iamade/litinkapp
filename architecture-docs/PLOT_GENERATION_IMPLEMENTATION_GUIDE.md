# Plot Generation Implementation Guide

## Overview

This guide provides step-by-step implementation instructions for the Plot Generation backend architecture. Follow these steps to implement the complete system.

## Step 1: Database Migration

Create the following migration file:

**File:** `backend/supabase/migrations/20250926_create_plot_system.sql`

```sql
-- ===================================================================
-- Plot Generation System Migration
-- Creates tables for plot overviews, characters, and enhanced scripts
-- ===================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create plot_overviews table
CREATE TABLE IF NOT EXISTS plot_overviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Core Plot Elements
    logline TEXT,
    themes JSONB DEFAULT '[]',
    story_type VARCHAR(50),
    genre VARCHAR(50),
    tone VARCHAR(50),
    audience VARCHAR(50),
    setting TEXT,
    
    -- Generation Metadata
    generation_method VARCHAR(50) DEFAULT 'openrouter',
    model_used VARCHAR(100),
    generation_cost DECIMAL(10,6) DEFAULT 0,
    
    -- Status and Versioning
    status VARCHAR(20) DEFAULT 'active',
    version INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(book_id, user_id, version)
);

-- Create characters table
CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plot_overview_id UUID NOT NULL REFERENCES plot_overviews(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Core Character Info
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100), -- 'protagonist', 'antagonist', 'supporting', 'minor'
    character_arc TEXT,
    physical_description TEXT,
    personality TEXT,
    
    -- Character Development
    archetypes JSONB DEFAULT '[]', -- Array of archetype strings
    want TEXT, -- External goal
    need TEXT, -- Internal need
    lie TEXT, -- Character's false belief
    ghost TEXT, -- Backstory wound
    
    -- Visual Assets
    image_url TEXT,
    image_generation_prompt TEXT,
    image_metadata JSONB DEFAULT '{}',
    
    -- Generation Metadata
    generation_method VARCHAR(50) DEFAULT 'openrouter',
    model_used VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(plot_overview_id, name)
);

-- Create enhanced chapter_scripts table
CREATE TABLE IF NOT EXISTS chapter_scripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    plot_overview_id UUID REFERENCES plot_overviews(id) ON DELETE SET NULL,
    script_id UUID REFERENCES scripts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Script Enhancement Data
    plot_enhanced BOOLEAN DEFAULT false,
    character_enhanced BOOLEAN DEFAULT false,
    
    -- Scene Breakdown
    scenes JSONB DEFAULT '[]', -- Array of scene objects
    acts JSONB DEFAULT '[]', -- Array of act objects
    beats JSONB DEFAULT '[]', -- Array of story beat objects
    
    -- Character Integration
    character_details JSONB DEFAULT '{}', -- Character info used in script
    character_arcs JSONB DEFAULT '{}', -- Character arc progression
    
    -- Status and Metadata
    status VARCHAR(20) DEFAULT 'active',
    version INTEGER DEFAULT 1,
    generation_metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(chapter_id, user_id, version)
);

-- Create character_archetypes reference table
CREATE TABLE IF NOT EXISTS character_archetypes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(50), -- 'hero', 'mentor', 'shadow', etc.
    traits JSONB DEFAULT '[]',
    typical_roles JSONB DEFAULT '[]',
    example_characters TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Insert default archetypes
INSERT INTO character_archetypes (name, description, category, traits, typical_roles, example_characters) VALUES
('The Hero', 'The central character who overcomes challenges and grows', 'hero', '["brave", "determined", "flawed", "growing"]', '["protagonist", "main character"]', 'Luke Skywalker, Frodo Baggins, Harry Potter'),
('The Mentor', 'The wise guide who helps the hero', 'guide', '["wise", "experienced", "supportive", "mysterious"]', '["teacher", "guide", "advisor"]', 'Gandalf, Obi-Wan Kenobi, Dumbledore'),
('The Shadow', 'The antagonist representing the hero''s dark side', 'antagonist', '["dark", "opposing", "powerful", "threatening"]', '["villain", "antagonist", "obstacle"]', 'Darth Vader, Sauron, Voldemort'),
('The Ally', 'The loyal companion who supports the hero', 'companion', '["loyal", "supportive", "skilled", "brave"]', '["sidekick", "friend", "companion"]', 'Hermione Granger, Samwise Gamgee, Han Solo'),
('The Threshold Guardian', 'Tests the hero''s resolve at key moments', 'challenger', '["testing", "blocking", "protective", "cautious"]', '["gatekeeper", "challenger", "obstacle"]', 'The Sphinx, Doormen, Bureaucrats'),
('The Shapeshifter', 'Character whose loyalty and nature keep changing', 'variable', '["mysterious", "changing", "unpredictable", "complex"]', '["double agent", "love interest", "ally/enemy"]', 'Snape, Lando Calrissian, Gollum'),
('The Trickster', 'Provides comic relief and unexpected wisdom', 'comic', '["humorous", "wise", "disruptive", "unconventional"]', '["comic relief", "fool", "jester"]', 'Mercutio, C-3PO, Tyrion Lannister');

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_plot_overviews_book_user ON plot_overviews(book_id, user_id);
CREATE INDEX IF NOT EXISTS idx_plot_overviews_status ON plot_overviews(status);
CREATE INDEX IF NOT EXISTS idx_plot_overviews_created_at ON plot_overviews(created_at);

CREATE INDEX IF NOT EXISTS idx_characters_plot_overview ON characters(plot_overview_id);
CREATE INDEX IF NOT EXISTS idx_characters_book_user ON characters(book_id, user_id);
CREATE INDEX IF NOT EXISTS idx_characters_role ON characters(role);
CREATE INDEX IF NOT EXISTS idx_characters_archetypes ON characters USING GIN(archetypes);

CREATE INDEX IF NOT EXISTS idx_chapter_scripts_chapter ON chapter_scripts(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chapter_scripts_plot ON chapter_scripts(plot_overview_id);
CREATE INDEX IF NOT EXISTS idx_chapter_scripts_user ON chapter_scripts(user_id);
CREATE INDEX IF NOT EXISTS idx_chapter_scripts_status ON chapter_scripts(status);

CREATE INDEX IF NOT EXISTS idx_character_archetypes_category ON character_archetypes(category);
CREATE INDEX IF NOT EXISTS idx_character_archetypes_active ON character_archetypes(is_active);

-- Enable Row Level Security (RLS)
ALTER TABLE plot_overviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapter_scripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE character_archetypes ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users manage own plot overviews" ON plot_overviews
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users manage own characters" ON characters
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users manage own chapter scripts" ON chapter_scripts
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Everyone reads active archetypes" ON character_archetypes
    FOR SELECT USING (is_active = true);

CREATE POLICY "Service role manages archetypes" ON character_archetypes
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Create function for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_plot_overviews_updated_at BEFORE UPDATE
    ON plot_overviews FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_characters_updated_at BEFORE UPDATE
    ON characters FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chapter_scripts_updated_at BEFORE UPDATE
    ON chapter_scripts FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## Step 2: Update Main Router

**File:** `backend/app/main.py` - Add plot router

```python
# Add this import
from app.api.v1 import plots

# Add this line to include the plots router
app.include_router(plots.router, prefix="/api/v1", tags=["plots"])
```

## Step 3: Environment Configuration

**File:** `backend/.env` - Add these variables

```bash
# Plot Generation Configuration
ENABLE_PLOT_GENERATION=true
PLOT_GENERATION_TIMEOUT=180
CHARACTER_IMAGE_GENERATION=true

# Cache Configuration for Plot System
PLOT_CACHE_TTL=3600
ARCHETYPE_CACHE_TTL=86400
```

## Step 4: Frontend Integration Updates

**File:** `src/services/userService.ts` - Update existing methods

```typescript
// The existing methods already match our API design:
// - generatePlotOverview(bookId: string)
// - savePlotOverview(bookId: string, plot: any)
// - getPlotOverview(bookId: string)

// Add these new methods for enhanced functionality:

async getCharacterArchetypes() {
  const response = await apiClient.get<any[]>('/archetypes');
  return response.data;
},

async generateCharacterImage(characterId: string, customPrompt?: string) {
  const response = await apiClient.post<{image_url: string}>(`/characters/${characterId}/generate-image`, {
    custom_prompt: customPrompt
  });
  return response.data;
},

async analyzeCharacterArchetypes(characterDescription: string) {
  const response = await apiClient.post<any>('/characters/analyze-archetypes', {
    character_description: characterDescription
  });
  return response.data;
},

// Update the existing generateScriptAndScenes method to use enhanced version
async generateEnhancedScriptAndScenes(
  chapterId: string,
  scriptStyle: string = "cinematic",
  usePlotContext: boolean = true,
  enhanceCharacterDevelopment: boolean = true
) {
  return apiClient.post<any>('/ai/generate-script-and-scenes', {
    chapter_id: chapterId,
    script_style: scriptStyle,
    use_plot_context: usePlotContext,
    enhance_character_development: enhanceCharacterDevelopment
  });
}
```

## Step 5: Testing Strategy

### Unit Tests

**File:** `backend/tests/test_plot_service.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.plot_service import PlotService, PlotGenerationError, SubscriptionLimitError

@pytest.fixture
def plot_service():
    mock_supabase = MagicMock()
    return PlotService(mock_supabase)

@pytest.mark.asyncio
async def test_generate_plot_overview_success(plot_service):
    # Mock subscription check
    plot_service.subscription_manager.get_user_tier = AsyncMock(return_value="standard")
    plot_service.subscription_manager.check_usage_limits = AsyncMock(return_value={"can_generate": True})
    
    # Mock OpenRouter response
    plot_service.openrouter.generate_script = AsyncMock(return_value={
        "status": "success",
        "content": '{"logline": "Test logline", "themes": ["adventure"], "genre": "fantasy"}',
        "model_used": "test-model",
        "usage": {"estimated_cost": 0.01}
    })
    
    # Mock RAG service
    plot_service._get_book_context_for_plot = AsyncMock(return_value={
        "book": {"title": "Test Book"},
        "total_chapters": 5
    })
    
    # Mock database storage
    plot_service._store_plot_overview = AsyncMock(return_value={
        "id": "test-plot-id",
        "plot_overview": {"logline": "Test logline"}
    })
    
    result = await plot_service.generate_plot_overview("book-id", "user-id")
    
    assert result["id"] == "test-plot-id"
    assert "plot_overview" in result

@pytest.mark.asyncio
async def test_generate_plot_overview_subscription_limit(plot_service):
    plot_service.subscription_manager.check_usage_limits = AsyncMock(return_value={"can_generate": False})
    
    with pytest.raises(SubscriptionLimitError):
        await plot_service.generate_plot_overview("book-id", "user-id")
```

### Integration Tests

**File:** `backend/tests/test_plot_integration.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_plot_generation_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test plot generation endpoint
        response = await client.post(
            "/api/v1/books/test-book-id/plot/generate",
            json={"custom_instructions": "Focus on character development"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 402]  # Success or subscription limit
        
        if response.status_code == 200:
            data = response.json()
            assert "plot_overview" in data
            assert "characters" in data["plot_overview"]

@pytest.mark.asyncio
async def test_enhanced_script_generation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/ai/generate-script-and-scenes",
            json={
                "chapter_id": "test-chapter-id",
                "script_style": "cinematic",
                "use_plot_context": True
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [200, 402, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "script" in data
            assert "plot_enhanced" in data
```

## Step 6: Performance Monitoring

**File:** `backend/app/middleware/plot_monitoring.py`

```python
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class PlotPerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only monitor plot-related endpoints
        if "/plot" in str(request.url) or "/characters" in str(request.url):
            start_time = time.time()
            
            response: Response = await call_next(request)
            
            process_time = time.time() - start_time
            
            # Log performance metrics
            logger.info(
                f"Plot API Performance - "
                f"Path: {request.url.path}, "
                f"Method: {request.method}, "
                f"Status: {response.status_code}, "
                f"Duration: {process_time:.3f}s"
            )
            
            # Add performance header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        else:
            return await call_next(request)
```

## Step 7: Error Handling and Logging

**File:** `backend/app/utils/plot_error_handler.py`

```python
import logging
from typing import Dict, Any
from fastapi import HTTPException
from app.services.plot_service import PlotGenerationError, SubscriptionLimitError

logger = logging.getLogger(__name__)

class PlotErrorHandler:
    @staticmethod
    def handle_plot_service_error(error: Exception, context: Dict[str, Any] = None) -> HTTPException:
        """Convert plot service errors to appropriate HTTP exceptions"""
        
        context = context or {}
        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **context
        }
        
        # Log the error
        logger.error(f"Plot service error: {error_details}")
        
        # Convert to appropriate HTTP exception
        if isinstance(error, SubscriptionLimitError):
            return HTTPException(
                status_code=402,
                detail={
                    "message": "Subscription limit exceeded",
                    "error": str(error),
                    "error_code": "SUBSCRIPTION_LIMIT_EXCEEDED"
                }
            )
        
        elif isinstance(error, PlotGenerationError):
            return HTTPException(
                status_code=400,
                detail={
                    "message": "Plot generation failed",
                    "error": str(error),
                    "error_code": "PLOT_GENERATION_FAILED"
                }
            )
        
        elif "OpenRouter" in str(error):
            return HTTPException(
                status_code=503,
                detail={
                    "message": "AI service temporarily unavailable",
                    "error_code": "AI_SERVICE_UNAVAILABLE"
                }
            )
        
        else:
            return HTTPException(
                status_code=500,
                detail={
                    "message": "Internal server error",
                    "error_code": "INTERNAL_ERROR"
                }
            )
    
    @staticmethod
    def log_plot_generation_metrics(
        user_id: str,
        book_id: str,
        generation_time: float,
        success: bool,
        error: str = None
    ):
        """Log plot generation metrics for monitoring"""
        
        metrics = {
            "event_type": "plot_generation",
            "user_id": user_id,
            "book_id": book_id,
            "generation_time": generation_time,
            "success": success,
            "error": error
        }
        
        if success:
            logger.info(f"Plot generation success: {metrics}")
        else:
            logger.error(f"Plot generation failure: {metrics}")
```

## Step 8: Deployment Checklist

### Pre-deployment Tasks

1. **Database Migration**
   ```bash
   # Run the migration
   supabase db push
   
   # Verify tables were created
   supabase db inspect
   ```

2. **Environment Variables**
   ```bash
   # Verify all required environment variables are set
   echo $OPENROUTER_API_KEY
   echo $SUPABASE_URL
   echo $SUPABASE_SERVICE_ROLE_KEY
   ```

3. **Dependencies**
   ```bash
   # Install any new dependencies
   pip install -r backend/requirements.txt
   ```

4. **Test Suite**
   ```bash
   # Run all tests
   python -m pytest backend/tests/test_plot_*
   ```

### Post-deployment Verification

1. **Health Check**
   ```bash
   curl -X GET "https://your-api.com/health/plot-service"
   ```

2. **Database Verification**
   ```sql
   -- Verify tables exist and have correct structure
   SELECT table_name FROM information_schema.tables 
   WHERE table_name IN ('plot_overviews', 'characters', 'chapter_scripts', 'character_archetypes');
   
   -- Check archetype data
   SELECT count(*) FROM character_archetypes WHERE is_active = true;
   ```

3. **API Endpoint Testing**
   ```bash
   # Test archetype endpoint (public)
   curl -X GET "https://your-api.com/api/v1/archetypes"
   
   # Test plot generation (requires auth)
   curl -X POST "https://your-api.com/api/v1/books/{book_id}/plot/generate" \
        -H "Authorization: Bearer YOUR_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"custom_instructions": "Test generation"}'
   ```

## Step 9: Monitoring and Analytics

### Key Metrics to Track

1. **Plot Generation Metrics**
   - Generation success rate
   - Average generation time
   - Cost per generation
   - User tier distribution

2. **Character System Metrics**
   - Character image generation rate
   - Archetype usage frequency
   - Character profile completeness

3. **Script Enhancement Metrics**
   - Plot-aware script adoption
   - Enhancement success rate
   - User satisfaction scores

### Monitoring Setup

**File:** `backend/app/monitoring/plot_metrics.py`

```python
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics
plot_generation_total = Counter('plot_generation_total', 'Total plot generations', ['user_tier', 'success'])
plot_generation_duration = Histogram('plot_generation_duration_seconds', 'Plot generation duration')
character_image_generation_total = Counter('character_image_generation_total', 'Character image generations')
active_plot_overviews = Gauge('active_plot_overviews_total', 'Total active plot overviews')

class PlotMetrics:
    @staticmethod
    def record_plot_generation(user_tier: str, duration: float, success: bool):
        """Record plot generation metrics"""
        plot_generation_total.labels(user_tier=user_tier, success=str(success).lower()).inc()
        plot_generation_duration.observe(duration)
        
        logger.info(f"Plot generation metric - Tier: {user_tier}, Duration: {duration}s, Success: {success}")
    
    @staticmethod
    def record_character_image_generation():
        """Record character image generation"""
        character_image_generation_total.inc()
    
    @staticmethod
    def update_active_plot_count(count: int):
        """Update active plot overview count"""
        active_plot_overviews.set(count)
```

## Step 10: Documentation Updates

### API Documentation

**File:** `backend/docs/plot_api.md`

```markdown
# Plot Generation API Documentation

## Endpoints

### Generate Plot Overview
`POST /api/v1/books/{book_id}/plot/generate`

Generates a comprehensive plot overview using AI analysis of the book content.

**Request:**
```json
{
  "custom_instructions": "Focus on character development and themes",
  "include_character_images": false
}
```

**Response:**
```json
{
  "id": "uuid",
  "book_id": "uuid",
  "plot_overview": {
    "logline": "A young wizard discovers his destiny...",
    "themes": ["good vs evil", "coming of age", "friendship"],
    "story_type": "hero's journey",
    "genre": "fantasy",
    "tone": "adventurous",
    "audience": "young adult",
    "setting": "magical school",
    "characters": [
      {
        "name": "Harry Potter",
        "role": "protagonist",
        "character_arc": "grows from naive boy to confident hero",
        "archetypes": ["The Hero", "The Orphan"],
        "want": "to belong somewhere",
        "need": "to accept his destiny",
        "lie": "he's not special",
        "ghost": "parents' death"
      }
    ]
  },
  "status": "active",
  "version": 1,
  "generation_metadata": {
    "model_used": "gpt-4",
    "cost": 0.05,
    "tier": "standard"
  },
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

### Save Plot Overview
`POST /api/v1/books/{book_id}/plot/save`

Saves or updates a plot overview.

### Get Plot Overview
`GET /api/v1/books/{book_id}/plot`

Retrieves the current plot overview for a book.

### Get Character Archetypes
`GET /api/v1/archetypes`

Returns all available character archetypes.

### Enhanced Script Generation
`POST /api/v1/ai/generate-script-and-scenes`

Generates scripts enhanced with plot and character context.
```

## Conclusion

This implementation guide provides a complete roadmap for implementing the plot generation system. The architecture integrates seamlessly with existing services while adding powerful new capabilities:

- **Plot Overview Generation**: AI-powered analysis of book content
- **Character Profiling**: Detailed character development with archetype analysis
- **Enhanced Script Generation**: Plot-aware script creation with character integration
- **Subscription Integration**: Tier-based access and usage tracking
- **Image Generation**: Character visualization capabilities
- **Comprehensive APIs**: Full REST API coverage for frontend integration

Follow the steps in order, test thoroughly at each stage, and monitor performance in production. The system is designed to scale and can be extended with additional features as needed.