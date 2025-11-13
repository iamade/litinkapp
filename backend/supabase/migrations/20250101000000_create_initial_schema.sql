/*
  # Create Initial Database Schema

  This migration creates the foundational database schema for the Litinkai platform.
  It includes all base tables, ENUM types, foreign key relationships, indexes, and RLS policies.

  ## Tables Created

  ### Core Content Tables
  - `profiles` - User profile information and preferences
  - `books` - Book content and metadata
  - `chapters` - Book chapters and sections
  - `scripts` - Generated scripts for video production
  - `characters` - Character definitions and details
  - `plot_overviews` - Plot summaries and story structure

  ### Generation Tables
  - `image_generations` - AI-generated images tracking
  - `audio_generations` - AI-generated audio tracking
  - `video_generations` - Video generation pipeline tracking

  ### Subscription & Usage Tables
  - `subscription_tiers` - Available subscription tier definitions
  - `user_subscriptions` - User subscription status and limits
  - `usage_logs` - Resource usage tracking for billing

  ## Security
  - RLS (Row Level Security) enabled on all tables
  - Policies enforce user data ownership and access control
  - Service role has full access for backend operations

  ## Notes
  - All operations use IF NOT EXISTS for idempotency
  - Foreign keys use appropriate CASCADE/SET NULL rules
  - Timestamps default to NOW() for created_at/updated_at
*/

-- ============================================
-- ENUM TYPES
-- ============================================

-- Book and content types
DO $$ BEGIN
  CREATE TYPE book_type AS ENUM ('learning', 'entertainment');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE book_status AS ENUM (
    'PROCESSING', 'GENERATING', 'READY', 'FAILED',
    'QUEUED', 'published', 'failed', 'PENDING_PAYMENT'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE difficulty_level AS ENUM ('easy', 'medium', 'hard');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Audio and video types
DO $$ BEGIN
  CREATE TYPE audio_type AS ENUM (
    'narrator', 'character', 'sound_effect',
    'background_music', 'music', 'sfx'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE video_generation_status AS ENUM (
    'pending', 'generating_audio', 'generating_images',
    'generating_video', 'combining', 'completed', 'failed',
    'applying_lipsync', 'lipsync_completed', 'lipsync_failed',
    'audio_completed', 'images_completed', 'video_completed',
    'merging_audio', 'retrying'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE video_quality_tier AS ENUM (
    'basic', 'standard', 'standard_2', 'pro', 'master'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Subscription types
DO $$ BEGIN
  CREATE TYPE subscription_tier AS ENUM ('free', 'basic', 'pro');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE subscription_status AS ENUM (
    'active', 'cancelled', 'expired', 'past_due', 'trialing'
  );
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- User role type
DO $$ BEGIN
  CREATE TYPE user_role AS ENUM ('author', 'explorer', 'superadmin');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Merge status type
DO $$ BEGIN
  CREATE TYPE merge_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- Badge rarity type
DO $$ BEGIN
  CREATE TYPE badge_rarity AS ENUM ('common', 'uncommon', 'rare', 'epic', 'legendary');
EXCEPTION
  WHEN duplicate_object THEN null;
END $$;

-- ============================================
-- PROFILES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  display_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  roles TEXT[] NOT NULL DEFAULT ARRAY['explorer'::TEXT],
  preferred_mode TEXT DEFAULT 'explorer',
  onboarding_completed JSONB DEFAULT '{}'::JSONB,
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  email_verified_at TIMESTAMPTZ,
  verification_token_sent_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY IF NOT EXISTS "Users can view own profile"
  ON profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY IF NOT EXISTS "Users can update own profile"
  ON profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY IF NOT EXISTS "Service role can manage all profiles"
  ON profiles FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- BOOKS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS books (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  author_name TEXT,
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  description TEXT,
  cover_image_url TEXT,
  book_type book_type NOT NULL,
  difficulty difficulty_level DEFAULT 'medium',
  total_chapters INTEGER DEFAULT 0,
  estimated_duration INTEGER,
  tags TEXT[],
  language TEXT DEFAULT 'en',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  cover_image_path TEXT,
  error_message TEXT,
  progress INTEGER DEFAULT 0,
  total_steps INTEGER DEFAULT 4,
  progress_message TEXT,
  status book_status DEFAULT 'QUEUED',
  content TEXT,
  original_file_storage_path TEXT,
  stripe_checkout_session_id TEXT,
  stripe_payment_intent_id TEXT,
  stripe_customer_id TEXT,
  payment_status TEXT DEFAULT 'unpaid',
  has_sections BOOLEAN DEFAULT FALSE,
  structure_type VARCHAR DEFAULT 'flat',
  uploaded_by_user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
  is_author BOOLEAN DEFAULT FALSE,
  created_with_platform BOOLEAN DEFAULT FALSE
);

-- Enable RLS
ALTER TABLE books ENABLE ROW LEVEL SECURITY;

-- Books policies
CREATE POLICY IF NOT EXISTS "Users can view own books"
  ON books FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can create own books"
  ON books FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can update own books"
  ON books FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can delete own books"
  ON books FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all books"
  ON books FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- CHAPTERS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS chapters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id UUID REFERENCES books(id) ON DELETE CASCADE,
  chapter_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  summary TEXT,
  duration INTEGER,
  ai_generated_content JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  section_id UUID,
  order_index INTEGER DEFAULT 0
);

-- Enable RLS
ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;

-- Chapters policies
CREATE POLICY IF NOT EXISTS "Users can view chapters of own books"
  ON chapters FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM books
      WHERE books.id = chapters.book_id
      AND books.user_id = auth.uid()
    )
  );

CREATE POLICY IF NOT EXISTS "Service role can manage all chapters"
  ON chapters FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- PLOT_OVERVIEWS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS plot_overviews (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  logline TEXT,
  themes JSONB,
  story_type TEXT,
  genre TEXT,
  tone TEXT,
  audience TEXT,
  setting TEXT,
  generation_method TEXT,
  model_used TEXT,
  generation_cost NUMERIC,
  status TEXT DEFAULT 'pending',
  version INTEGER DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  script_story_type TEXT
);

-- Enable RLS
ALTER TABLE plot_overviews ENABLE ROW LEVEL SECURITY;

-- Plot overviews policies
CREATE POLICY IF NOT EXISTS "Users can view own plot overviews"
  ON plot_overviews FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all plot overviews"
  ON plot_overviews FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- CHARACTERS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS characters (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  plot_overview_id UUID NOT NULL REFERENCES plot_overviews(id) ON DELETE CASCADE,
  book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  name TEXT NOT NULL,
  role TEXT,
  character_arc TEXT,
  physical_description TEXT,
  personality TEXT,
  archetypes JSONB,
  want TEXT,
  need TEXT,
  lie TEXT,
  ghost TEXT,
  image_url TEXT,
  image_generation_prompt TEXT,
  image_metadata JSONB,
  generation_method TEXT,
  model_used TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  image_generation_task_id TEXT,
  image_generation_status TEXT DEFAULT 'none'
);

-- Enable RLS
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;

-- Characters policies
CREATE POLICY IF NOT EXISTS "Users can view own characters"
  ON characters FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all characters"
  ON characters FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- SCRIPTS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS scripts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
  user_id UUID,
  script_style VARCHAR NOT NULL DEFAULT 'cinematic_movie',
  script TEXT NOT NULL,
  scene_descriptions JSONB DEFAULT '[]'::JSONB,
  characters JSONB DEFAULT '[]'::JSONB,
  character_details TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
  status VARCHAR DEFAULT 'ready',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  service_used VARCHAR,
  script_name VARCHAR,
  script_story_type TEXT
);

-- Enable RLS
ALTER TABLE scripts ENABLE ROW LEVEL SECURITY;

-- Scripts policies
CREATE POLICY IF NOT EXISTS "Users can view scripts of own chapters"
  ON scripts FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chapters
      JOIN books ON books.id = chapters.book_id
      WHERE chapters.id = scripts.chapter_id
      AND books.user_id = auth.uid()
    )
  );

CREATE POLICY IF NOT EXISTS "Service role can manage all scripts"
  ON scripts FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- VIDEO_GENERATIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS video_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id UUID REFERENCES chapters(id) ON DELETE CASCADE,
  script_id UUID REFERENCES scripts(id) ON DELETE SET NULL,
  user_id UUID,
  generation_status video_generation_status DEFAULT 'pending',
  quality_tier video_quality_tier DEFAULT 'basic',
  video_url TEXT,
  subtitle_url TEXT,
  thumbnail_url TEXT,
  duration_seconds NUMERIC,
  file_size_bytes BIGINT,
  script_data JSONB,
  audio_files JSONB DEFAULT '[]'::JSONB,
  image_files JSONB DEFAULT '[]'::JSONB,
  video_segments JSONB DEFAULT '[]'::JSONB,
  progress_log JSONB DEFAULT '[]'::JSONB,
  error_message TEXT,
  processing_time_seconds NUMERIC,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  image_data JSONB,
  video_data JSONB,
  merge_data JSONB,
  lipsync_data JSONB,
  audio_task_id TEXT,
  task_metadata JSONB,
  pipeline_state JSONB DEFAULT '{}'::JSONB,
  failed_at_step TEXT,
  can_resume BOOLEAN DEFAULT FALSE,
  retry_count INTEGER DEFAULT 0,
  character_voice_mappings JSONB,
  merge_failed_at TIMESTAMPTZ,
  last_retry_at TIMESTAMPTZ
);

-- Enable RLS
ALTER TABLE video_generations ENABLE ROW LEVEL SECURITY;

-- Video generations policies
CREATE POLICY IF NOT EXISTS "Users can view own video generations"
  ON video_generations FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all video generations"
  ON video_generations FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- IMAGE_GENERATIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS image_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_generation_id UUID REFERENCES video_generations(id) ON DELETE CASCADE,
  scene_id VARCHAR,
  shot_index INTEGER DEFAULT 0,
  scene_description TEXT,
  image_prompt TEXT,
  image_url TEXT,
  thumbnail_url TEXT,
  width INTEGER,
  height INTEGER,
  file_size_bytes BIGINT,
  status VARCHAR DEFAULT 'pending',
  error_message TEXT,
  generation_time_seconds NUMERIC,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  image_type VARCHAR DEFAULT 'scene',
  character_name VARCHAR,
  sequence_order INTEGER,
  style VARCHAR,
  text_prompt TEXT,
  prompt TEXT,
  model_id VARCHAR DEFAULT 'gen4_image',
  aspect_ratio VARCHAR DEFAULT '16:9',
  enhancement_type VARCHAR,
  batch_index INTEGER,
  service_provider VARCHAR DEFAULT 'modelslab_v7',
  scene_number INTEGER,
  fetch_url VARCHAR,
  request_id VARCHAR,
  user_id UUID,
  updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  script_id UUID REFERENCES scripts(id) ON DELETE SET NULL,
  character_id UUID REFERENCES characters(id) ON DELETE SET NULL,
  chapter_id UUID,
  retry_count INTEGER NOT NULL DEFAULT 0,
  last_attempted_at TIMESTAMPTZ,
  progress INTEGER DEFAULT 0
);

-- Enable RLS
ALTER TABLE image_generations ENABLE ROW LEVEL SECURITY;

-- Image generations policies
CREATE POLICY IF NOT EXISTS "Users can view own image generations"
  ON image_generations FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all image generations"
  ON image_generations FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- AUDIO_GENERATIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS audio_generations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_generation_id UUID REFERENCES video_generations(id) ON DELETE CASCADE,
  audio_type audio_type NOT NULL,
  scene_id VARCHAR,
  character_name VARCHAR,
  text_content TEXT,
  voice_id VARCHAR,
  audio_url TEXT,
  duration_seconds NUMERIC,
  file_size_bytes BIGINT,
  status VARCHAR DEFAULT 'pending',
  error_message TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  duration DOUBLE PRECISION,
  generation_status TEXT DEFAULT 'pending',
  sequence_order INTEGER,
  model_id VARCHAR DEFAULT 'eleven_multilingual_v2',
  voice_model VARCHAR,
  audio_format VARCHAR DEFAULT 'mp3',
  generation_time_seconds DOUBLE PRECISION,
  audio_length_seconds DOUBLE PRECISION,
  service_provider VARCHAR DEFAULT 'modelslab_v7',
  chapter_id UUID,
  user_id UUID,
  script_id UUID REFERENCES scripts(id) ON DELETE SET NULL
);

-- Enable RLS
ALTER TABLE audio_generations ENABLE ROW LEVEL SECURITY;

-- Audio generations policies
CREATE POLICY IF NOT EXISTS "Users can view own audio generations"
  ON audio_generations FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all audio generations"
  ON audio_generations FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- SUBSCRIPTION_TIERS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS subscription_tiers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tier subscription_tier NOT NULL,
  display_name VARCHAR NOT NULL,
  description TEXT,
  monthly_price NUMERIC NOT NULL,
  stripe_price_id VARCHAR,
  stripe_product_id VARCHAR,
  monthly_video_limit INTEGER NOT NULL,
  video_quality VARCHAR NOT NULL,
  has_watermark BOOLEAN NOT NULL DEFAULT FALSE,
  max_video_duration INTEGER,
  priority_processing BOOLEAN DEFAULT FALSE,
  features JSONB DEFAULT '{}'::JSONB,
  display_order INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE subscription_tiers ENABLE ROW LEVEL SECURITY;

-- Subscription tiers policies
CREATE POLICY IF NOT EXISTS "Anyone can view subscription tiers"
  ON subscription_tiers FOR SELECT
  TO authenticated
  USING (is_active = TRUE);

CREATE POLICY IF NOT EXISTS "Service role can manage subscription tiers"
  ON subscription_tiers FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- USER_SUBSCRIPTIONS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS user_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  tier subscription_tier NOT NULL DEFAULT 'free',
  status subscription_status NOT NULL DEFAULT 'active',
  stripe_customer_id VARCHAR,
  stripe_subscription_id VARCHAR,
  stripe_price_id VARCHAR,
  monthly_video_limit INTEGER NOT NULL DEFAULT 2,
  video_quality VARCHAR DEFAULT '480p',
  has_watermark BOOLEAN DEFAULT TRUE,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  videos_generated_this_period INTEGER DEFAULT 0,
  next_billing_date TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  cancelled_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE user_subscriptions ENABLE ROW LEVEL SECURITY;

-- User subscriptions policies
CREATE POLICY IF NOT EXISTS "Users can view own subscription"
  ON user_subscriptions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all subscriptions"
  ON user_subscriptions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- USAGE_LOGS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS usage_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  subscription_id UUID REFERENCES user_subscriptions(id) ON DELETE CASCADE,
  resource_type VARCHAR NOT NULL DEFAULT 'video_generation',
  resource_id UUID,
  usage_count INTEGER DEFAULT 1,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  billing_period_start TIMESTAMPTZ,
  billing_period_end TIMESTAMPTZ,
  cost_usd NUMERIC DEFAULT 0.0
);

-- Enable RLS
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Usage logs policies
CREATE POLICY IF NOT EXISTS "Users can view own usage logs"
  ON usage_logs FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Users can insert own usage logs"
  ON usage_logs FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY IF NOT EXISTS "Service role can manage all usage logs"
  ON usage_logs FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================
-- INDEXES
-- ============================================

-- Profiles indexes
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_roles ON profiles USING GIN(roles);

-- Books indexes
CREATE INDEX IF NOT EXISTS idx_books_user_id ON books(user_id);
CREATE INDEX IF NOT EXISTS idx_books_status ON books(status);
CREATE INDEX IF NOT EXISTS idx_books_book_type ON books(book_type);

-- Chapters indexes
CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_chapters_book_chapter ON chapters(book_id, chapter_number);

-- Scripts indexes
CREATE INDEX IF NOT EXISTS idx_scripts_chapter_id ON scripts(chapter_id);
CREATE INDEX IF NOT EXISTS idx_scripts_user_id ON scripts(user_id);

-- Characters indexes
CREATE INDEX IF NOT EXISTS idx_characters_book_id ON characters(book_id);
CREATE INDEX IF NOT EXISTS idx_characters_plot_overview_id ON characters(plot_overview_id);

-- Plot overviews indexes
CREATE INDEX IF NOT EXISTS idx_plot_overviews_book_id ON plot_overviews(book_id);
CREATE INDEX IF NOT EXISTS idx_plot_overviews_user_id ON plot_overviews(user_id);

-- Video generations indexes
CREATE INDEX IF NOT EXISTS idx_video_generations_chapter_id ON video_generations(chapter_id);
CREATE INDEX IF NOT EXISTS idx_video_generations_user_id ON video_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_video_generations_status ON video_generations(generation_status);

-- Image generations indexes
CREATE INDEX IF NOT EXISTS idx_image_generations_video_id ON image_generations(video_generation_id);
CREATE INDEX IF NOT EXISTS idx_image_generations_status ON image_generations(status);
CREATE INDEX IF NOT EXISTS idx_image_generations_user_id ON image_generations(user_id);

-- Audio generations indexes
CREATE INDEX IF NOT EXISTS idx_audio_generations_video_id ON audio_generations(video_generation_id);
CREATE INDEX IF NOT EXISTS idx_audio_generations_status ON audio_generations(status);

-- Subscriptions indexes
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_stripe_customer ON user_subscriptions(stripe_customer_id);

-- Usage logs indexes
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_subscription_id ON usage_logs(subscription_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE profiles IS 'User profile information and settings';
COMMENT ON TABLE books IS 'Book content and metadata';
COMMENT ON TABLE chapters IS 'Book chapters and their content';
COMMENT ON TABLE scripts IS 'Generated scripts for video production';
COMMENT ON TABLE characters IS 'Character definitions and visual representations';
COMMENT ON TABLE plot_overviews IS 'Story structure and plot summaries';
COMMENT ON TABLE video_generations IS 'Video generation pipeline tracking and status';
COMMENT ON TABLE image_generations IS 'AI-generated image tracking and metadata';
COMMENT ON TABLE audio_generations IS 'AI-generated audio tracking and metadata';
COMMENT ON TABLE subscription_tiers IS 'Available subscription plans and features';
COMMENT ON TABLE user_subscriptions IS 'User subscription status and usage limits';
COMMENT ON TABLE usage_logs IS 'Resource usage tracking for billing and analytics';
