

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "public";






CREATE TYPE "public"."audio_type" AS ENUM (
    'narrator',
    'character',
    'sound_effect',
    'background_music',
    'music',
    'sfx'
);


ALTER TYPE "public"."audio_type" OWNER TO "postgres";


CREATE TYPE "public"."badge_rarity" AS ENUM (
    'common',
    'uncommon',
    'rare',
    'epic',
    'legendary'
);


ALTER TYPE "public"."badge_rarity" OWNER TO "postgres";


CREATE TYPE "public"."book_status" AS ENUM (
    'PROCESSING',
    'GENERATING',
    'READY',
    'FAILED',
    'QUEUED',
    'published',
    'failed',
    'PENDING_PAYMENT'
);


ALTER TYPE "public"."book_status" OWNER TO "postgres";


CREATE TYPE "public"."book_type" AS ENUM (
    'learning',
    'entertainment'
);


ALTER TYPE "public"."book_type" OWNER TO "postgres";


CREATE TYPE "public"."difficulty_level" AS ENUM (
    'easy',
    'medium',
    'hard'
);


ALTER TYPE "public"."difficulty_level" OWNER TO "postgres";


CREATE TYPE "public"."merge_status" AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'FAILED'
);


ALTER TYPE "public"."merge_status" OWNER TO "postgres";


CREATE TYPE "public"."subscription_status" AS ENUM (
    'active',
    'cancelled',
    'expired',
    'past_due',
    'trialing'
);


ALTER TYPE "public"."subscription_status" OWNER TO "postgres";


CREATE TYPE "public"."subscription_tier" AS ENUM (
    'free',
    'basic',
    'pro'
);


ALTER TYPE "public"."subscription_tier" OWNER TO "postgres";


CREATE TYPE "public"."user_role" AS ENUM (
    'author',
    'explorer',
    'superadmin'
);


ALTER TYPE "public"."user_role" OWNER TO "postgres";


CREATE TYPE "public"."video_generation_status" AS ENUM (
    'pending',
    'generating_audio',
    'generating_images',
    'generating_video',
    'combining',
    'completed',
    'failed',
    'applying_lipsync',
    'lipsync_completed',
    'lipsync_failed',
    'audio_completed',
    'images_completed',
    'video_completed',
    'merging_audio',
    'retrying'
);


ALTER TYPE "public"."video_generation_status" OWNER TO "postgres";


CREATE TYPE "public"."video_quality_tier" AS ENUM (
    'basic',
    'standard',
    'standard_2',
    'pro',
    'master'
);


ALTER TYPE "public"."video_quality_tier" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."check_usage_limit"("p_user_id" "uuid") RETURNS boolean
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_subscription RECORD;
BEGIN
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
    AND status = 'active';
    
    IF NOT FOUND THEN
        -- No active subscription, use free tier limits
        SELECT * INTO v_subscription
        FROM subscription_tiers
        WHERE tier = 'free';
        RETURN true; -- Allow free tier by default
    END IF;
    
    -- Check if within limits
    RETURN v_subscription.videos_generated_this_period < v_subscription.monthly_video_limit;
END;
$$;


ALTER FUNCTION "public"."check_usage_limit"("p_user_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."increment_usage"("p_user_id" "uuid", "p_resource_id" "uuid" DEFAULT NULL::"uuid") RETURNS "void"
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    v_subscription RECORD;
BEGIN
    -- Get current subscription
    SELECT * INTO v_subscription
    FROM user_subscriptions
    WHERE user_id = p_user_id
    AND status = 'active'
    FOR UPDATE;
    
    IF FOUND THEN
        -- Increment usage counter
        UPDATE user_subscriptions
        SET videos_generated_this_period = videos_generated_this_period + 1,
            updated_at = NOW()
        WHERE id = v_subscription.id;
        
        -- Log usage
        INSERT INTO usage_logs (
            user_id,
            subscription_id,
            resource_type,
            resource_id,
            billing_period_start,
            billing_period_end
        ) VALUES (
            p_user_id,
            v_subscription.id,
            'video_generation',
            p_resource_id,
            v_subscription.current_period_start,
            v_subscription.current_period_end
        );
    ELSE
        -- Create free subscription if none exists
        INSERT INTO user_subscriptions (
            user_id,
            tier,
            status,
            monthly_video_limit,
            videos_generated_this_period,
            current_period_start,
            current_period_end
        ) VALUES (
            p_user_id,
            'free',
            'active',
            2,
            1,
            NOW(),
            NOW() + INTERVAL '30 days'
        )
        ON CONFLICT (user_id) DO UPDATE
        SET videos_generated_this_period = user_subscriptions.videos_generated_this_period + 1;
    END IF;
END;
$$;


ALTER FUNCTION "public"."increment_usage"("p_user_id" "uuid", "p_resource_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_book_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) RETURNS TABLE("id" "uuid", "book_id" "uuid", "content_chunk" "text", "chunk_type" "text", "chunk_index" integer, "similarity" double precision)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    be.id,
    be.book_id,
    be.content_chunk,
    be.chunk_type,
    be.chunk_index,
    1 - (be.embedding <=> query_embedding) AS similarity
  FROM book_embeddings be
  WHERE 1 - (be.embedding <=> query_embedding) > match_threshold
  ORDER BY be.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;


ALTER FUNCTION "public"."match_book_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."match_chapter_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) RETURNS TABLE("id" "uuid", "chapter_id" "uuid", "book_id" "uuid", "content_chunk" "text", "chunk_index" integer, "similarity" double precision)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT
    ce.id,
    ce.chapter_id,
    ce.book_id,
    ce.content_chunk,
    ce.chunk_index,
    1 - (ce.embedding <=> query_embedding) AS similarity
  FROM chapter_embeddings ce
  WHERE 1 - (ce.embedding <=> query_embedding) > match_threshold
  ORDER BY ce.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;


ALTER FUNCTION "public"."match_chapter_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."reset_monthly_usage"() RETURNS integer
    LANGUAGE "plpgsql"
    AS $$
DECLARE
    rows_updated INTEGER;
BEGIN
    UPDATE user_subscriptions
    SET videos_generated_this_period = 0,
        current_period_start = NOW(),
        current_period_end = NOW() + INTERVAL '30 days',
        updated_at = NOW()
    WHERE current_period_end <= NOW()
    AND status = 'active';
    
    GET DIAGNOSTICS rows_updated = ROW_COUNT;
    RETURN rows_updated;
END;
$$;


ALTER FUNCTION "public"."reset_monthly_usage"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_learning_content_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_learning_content_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."audio_exports" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "chapter_id" "uuid" NOT NULL,
    "export_format" "text" DEFAULT 'mp3'::"text",
    "status" "text" DEFAULT 'pending'::"text",
    "download_url" "text",
    "audio_files" "jsonb",
    "mix_settings" "jsonb" DEFAULT '{}'::"jsonb",
    "error_message" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "audio_exports_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'processing'::"text", 'completed'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."audio_exports" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."audio_generations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "video_generation_id" "uuid",
    "audio_type" "public"."audio_type" NOT NULL,
    "scene_id" character varying(50),
    "character_name" character varying(100),
    "text_content" "text",
    "voice_id" character varying(100),
    "audio_url" "text",
    "duration_seconds" numeric,
    "file_size_bytes" bigint,
    "status" character varying(20) DEFAULT 'pending'::character varying,
    "error_message" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "duration" double precision,
    "generation_status" "text" DEFAULT 'pending'::"text",
    "sequence_order" integer,
    "model_id" character varying(100) DEFAULT 'eleven_multilingual_v2'::character varying,
    "voice_model" character varying(100),
    "audio_format" character varying(20) DEFAULT 'mp3'::character varying,
    "generation_time_seconds" double precision,
    "audio_length_seconds" double precision,
    "service_provider" character varying(50) DEFAULT 'modelslab_v7'::character varying,
    "chapter_id" "uuid",
    "user_id" "uuid"
);


ALTER TABLE "public"."audio_generations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."badges" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text" NOT NULL,
    "image_url" "text",
    "criteria" "text" NOT NULL,
    "rarity" "public"."badge_rarity" DEFAULT 'common'::"public"."badge_rarity",
    "points" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."badges" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."book_embeddings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "book_id" "uuid",
    "content_chunk" "text" NOT NULL,
    "embedding" "public"."vector"(1536),
    "chunk_index" integer NOT NULL,
    "chunk_size" integer NOT NULL,
    "chunk_type" "text" NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."book_embeddings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."book_sections" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "book_id" "uuid",
    "section_number" character varying(10) NOT NULL,
    "section_type" character varying(20) NOT NULL,
    "title" character varying(500) NOT NULL,
    "description" "text",
    "order_index" integer NOT NULL,
    "created_at" timestamp without time zone DEFAULT "now"(),
    "updated_at" timestamp without time zone DEFAULT "now"()
);


ALTER TABLE "public"."book_sections" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."books" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "title" "text" NOT NULL,
    "author_name" "text",
    "user_id" "uuid",
    "description" "text",
    "cover_image_url" "text",
    "book_type" "public"."book_type" NOT NULL,
    "difficulty" "public"."difficulty_level" DEFAULT 'medium'::"public"."difficulty_level",
    "total_chapters" integer DEFAULT 0,
    "estimated_duration" integer,
    "tags" "text"[],
    "language" "text" DEFAULT 'en'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "cover_image_path" "text",
    "error_message" "text",
    "progress" integer DEFAULT 0,
    "total_steps" integer DEFAULT 4,
    "progress_message" "text",
    "status" "public"."book_status" DEFAULT 'QUEUED'::"public"."book_status",
    "content" "text",
    "original_file_storage_path" "text",
    "stripe_checkout_session_id" "text",
    "stripe_payment_intent_id" "text",
    "stripe_customer_id" "text",
    "payment_status" "text" DEFAULT 'unpaid'::"text",
    "has_sections" boolean DEFAULT false,
    "structure_type" character varying(20) DEFAULT 'flat'::character varying
);


ALTER TABLE "public"."books" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chapter_embeddings" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chapter_id" "uuid",
    "book_id" "uuid",
    "content_chunk" "text" NOT NULL,
    "embedding" "public"."vector"(1536),
    "chunk_index" integer NOT NULL,
    "chunk_size" integer NOT NULL,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."chapter_embeddings" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chapter_scripts" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "chapter_id" "uuid" NOT NULL,
    "plot_overview_id" "uuid",
    "script_id" "uuid",
    "user_id" "uuid" NOT NULL,
    "plot_enhanced" boolean DEFAULT false,
    "character_enhanced" boolean DEFAULT false,
    "scenes" "jsonb",
    "acts" "jsonb",
    "beats" "jsonb",
    "character_details" "jsonb",
    "character_arcs" "jsonb",
    "status" "text" DEFAULT 'pending'::"text",
    "version" integer DEFAULT 1,
    "generation_metadata" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."chapter_scripts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."chapters" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "book_id" "uuid",
    "chapter_number" integer NOT NULL,
    "title" "text" NOT NULL,
    "content" "text" NOT NULL,
    "summary" "text",
    "duration" integer,
    "ai_generated_content" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "section_id" "uuid",
    "order_index" integer DEFAULT 0
);


ALTER TABLE "public"."chapters" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."character_archetypes" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text",
    "category" "text",
    "traits" "jsonb",
    "typical_roles" "jsonb",
    "example_characters" "text",
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."character_archetypes" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."characters" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "plot_overview_id" "uuid" NOT NULL,
    "book_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "name" "text" NOT NULL,
    "role" "text",
    "character_arc" "text",
    "physical_description" "text",
    "personality" "text",
    "archetypes" "jsonb",
    "want" "text",
    "need" "text",
    "lie" "text",
    "ghost" "text",
    "image_url" "text",
    "image_generation_prompt" "text",
    "image_metadata" "jsonb",
    "generation_method" "text",
    "model_used" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."characters" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."image_generations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "video_generation_id" "uuid",
    "scene_id" character varying(50),
    "shot_index" integer DEFAULT 0,
    "scene_description" "text",
    "image_prompt" "text",
    "image_url" "text",
    "thumbnail_url" "text",
    "width" integer,
    "height" integer,
    "file_size_bytes" bigint,
    "status" character varying(20) DEFAULT 'pending'::character varying,
    "error_message" "text",
    "generation_time_seconds" numeric,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "image_type" character varying(50),
    "character_name" character varying(255),
    "sequence_order" integer,
    "style" character varying(50),
    "text_prompt" "text",
    "prompt" "text",
    "model_id" character varying(100) DEFAULT 'gen4_image'::character varying,
    "aspect_ratio" character varying(20) DEFAULT '16:9'::character varying,
    "enhancement_type" character varying(50),
    "batch_index" integer,
    "service_provider" character varying(50) DEFAULT 'modelslab_v7'::character varying,
    "scene_number" integer,
    "fetch_url" character varying(500),
    "request_id" character varying(100),
    "user_id" "uuid",
    "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE "public"."image_generations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."learning_content" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chapter_id" "uuid",
    "book_id" "uuid",
    "user_id" "uuid",
    "content_type" "text" NOT NULL,
    "content_url" "text",
    "script" "text",
    "duration" integer DEFAULT 180,
    "status" "text" DEFAULT 'processing'::"text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "tavus_video_id" "text",
    "tavus_url" "text",
    "tavus_response" "jsonb",
    "error_message" "text",
    "generation_progress" "text",
    "video_segments" "jsonb",
    "combined_video_url" "text",
    CONSTRAINT "learning_content_content_type_check" CHECK (("content_type" = ANY (ARRAY['audio_narration'::"text", 'realistic_video'::"text"]))),
    CONSTRAINT "learning_content_status_check" CHECK (("status" = ANY (ARRAY['processing'::"text", 'ready'::"text", 'failed'::"text"])))
);


ALTER TABLE "public"."learning_content" OWNER TO "postgres";


COMMENT ON COLUMN "public"."learning_content"."tavus_video_id" IS 'Tavus video ID for tracking video generation';



COMMENT ON COLUMN "public"."learning_content"."tavus_url" IS 'Tavus hosted URL for the video';



COMMENT ON COLUMN "public"."learning_content"."tavus_response" IS 'Full Tavus API response for debugging';



COMMENT ON COLUMN "public"."learning_content"."error_message" IS 'Detailed error message if generation fails';



COMMENT ON COLUMN "public"."learning_content"."generation_progress" IS 'Current generation progress (e.g., 37/100)';



COMMENT ON COLUMN "public"."learning_content"."video_segments" IS 'Array of video segment URLs to be combined';



COMMENT ON COLUMN "public"."learning_content"."combined_video_url" IS 'Final combined video URL after FFmpeg processing';



CREATE TABLE IF NOT EXISTS "public"."merge_operations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "video_file_url" "text",
    "audio_file_url" "text",
    "merge_status" "public"."merge_status" DEFAULT 'PENDING'::"public"."merge_status",
    "progress" integer DEFAULT 0,
    "output_file_url" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "input_sources" "jsonb",
    "quality_tier" "text",
    "output_format" "text",
    "ffmpeg_params" "jsonb",
    "merge_name" "text",
    "error_message" "text",
    "processing_stats" "jsonb",
    "preview_url" "text",
    CONSTRAINT "merge_operations_progress_check" CHECK ((("progress" >= 0) AND ("progress" <= 100)))
);


ALTER TABLE "public"."merge_operations" OWNER TO "postgres";


COMMENT ON COLUMN "public"."merge_operations"."input_sources" IS 'Array of input file sources for the merge operation';



COMMENT ON COLUMN "public"."merge_operations"."quality_tier" IS 'Quality tier for the merge output (web, medium, high, custom)';



COMMENT ON COLUMN "public"."merge_operations"."output_format" IS 'Output format for the merged file (mp4, webm, mov)';



COMMENT ON COLUMN "public"."merge_operations"."ffmpeg_params" IS 'Custom FFmpeg parameters for advanced processing';



COMMENT ON COLUMN "public"."merge_operations"."merge_name" IS 'User-defined name for the merge operation';



COMMENT ON COLUMN "public"."merge_operations"."error_message" IS 'Error message if the merge operation failed';



COMMENT ON COLUMN "public"."merge_operations"."processing_stats" IS 'Statistics and metadata from the merge processing';



COMMENT ON COLUMN "public"."merge_operations"."preview_url" IS 'URL of the generated preview video clip (first 10 seconds of merged output)';



CREATE TABLE IF NOT EXISTS "public"."nft_collectibles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "name" "text" NOT NULL,
    "description" "text" NOT NULL,
    "image_url" "text",
    "animation_url" "text",
    "story_moment" "text" NOT NULL,
    "rarity" "public"."badge_rarity" DEFAULT 'common'::"public"."badge_rarity",
    "book_id" "uuid",
    "chapter_id" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."nft_collectibles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."pipeline_steps" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "video_generation_id" "uuid",
    "step_name" "text" NOT NULL,
    "step_order" integer NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "started_at" timestamp with time zone,
    "completed_at" timestamp with time zone,
    "error_message" "text",
    "step_data" "jsonb" DEFAULT '{}'::"jsonb",
    "retry_count" integer DEFAULT 0,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."pipeline_steps" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."plot_overviews" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "book_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "logline" "text",
    "themes" "jsonb",
    "story_type" "text",
    "genre" "text",
    "tone" "text",
    "audience" "text",
    "setting" "text",
    "generation_method" "text",
    "model_used" "text",
    "generation_cost" numeric(10,4),
    "status" "text" DEFAULT 'pending'::"text",
    "version" integer DEFAULT 1,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."plot_overviews" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."profiles" (
    "id" "uuid" NOT NULL,
    "email" "text" NOT NULL,
    "display_name" "text",
    "role" "public"."user_role" DEFAULT 'explorer'::"public"."user_role" NOT NULL,
    "avatar_url" "text",
    "bio" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."profiles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."quiz_attempts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "quiz_id" "uuid",
    "answers" "jsonb" NOT NULL,
    "score" integer NOT NULL,
    "completed_at" timestamp with time zone DEFAULT "now"(),
    "time_taken" integer
);


ALTER TABLE "public"."quiz_attempts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."quizzes" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chapter_id" "uuid",
    "title" "text" NOT NULL,
    "questions" "jsonb" NOT NULL,
    "difficulty" "public"."difficulty_level" DEFAULT 'medium'::"public"."difficulty_level",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."quizzes" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."scripts" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chapter_id" "uuid",
    "user_id" "uuid",
    "script_style" character varying(50) DEFAULT 'cinematic_movie'::character varying NOT NULL,
    "script" "text" NOT NULL,
    "scene_descriptions" "jsonb" DEFAULT '[]'::"jsonb",
    "characters" "jsonb" DEFAULT '[]'::"jsonb",
    "character_details" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "status" character varying(20) DEFAULT 'ready'::character varying,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "service_used" character varying(50),
    "script_name" character varying(255)
);


ALTER TABLE "public"."scripts" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."story_choices" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chapter_id" "uuid",
    "choice_text" "text" NOT NULL,
    "consequence" "text" NOT NULL,
    "next_chapter_id" "uuid",
    "choice_order" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."story_choices" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."subscription_history" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "subscription_id" "uuid",
    "event_type" character varying(100) NOT NULL,
    "from_tier" "public"."subscription_tier",
    "to_tier" "public"."subscription_tier",
    "from_status" "public"."subscription_status",
    "to_status" "public"."subscription_status",
    "stripe_event_id" character varying(255),
    "stripe_invoice_id" character varying(255),
    "amount_paid" numeric(10,2),
    "currency" character varying(3) DEFAULT 'USD'::character varying,
    "reason" "text",
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."subscription_history" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."subscription_tiers" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "tier" "public"."subscription_tier" NOT NULL,
    "display_name" character varying(100) NOT NULL,
    "description" "text",
    "monthly_price" numeric(10,2) NOT NULL,
    "stripe_price_id" character varying(255),
    "stripe_product_id" character varying(255),
    "monthly_video_limit" integer NOT NULL,
    "video_quality" character varying(50) NOT NULL,
    "has_watermark" boolean DEFAULT false NOT NULL,
    "max_video_duration" integer,
    "priority_processing" boolean DEFAULT false,
    "features" "jsonb" DEFAULT '{}'::"jsonb",
    "display_order" integer DEFAULT 0,
    "is_active" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."subscription_tiers" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."usage_logs" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "subscription_id" "uuid" NOT NULL,
    "resource_type" character varying(50) DEFAULT 'video_generation'::character varying NOT NULL,
    "resource_id" "uuid",
    "usage_count" integer DEFAULT 1,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "billing_period_start" timestamp with time zone,
    "billing_period_end" timestamp with time zone,
    "cost_usd" numeric(10,6) DEFAULT 0.0
);


ALTER TABLE "public"."usage_logs" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_badges" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "badge_id" "uuid",
    "earned_at" timestamp with time zone DEFAULT "now"(),
    "blockchain_asset_id" bigint,
    "transaction_id" "text"
);


ALTER TABLE "public"."user_badges" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_collectibles" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "collectible_id" "uuid",
    "earned_at" timestamp with time zone DEFAULT "now"(),
    "blockchain_asset_id" bigint,
    "transaction_id" "text"
);


ALTER TABLE "public"."user_collectibles" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_progress" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "book_id" "uuid",
    "current_chapter" integer DEFAULT 1,
    "progress_percentage" integer DEFAULT 0,
    "time_spent" integer DEFAULT 0,
    "last_read_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."user_progress" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_story_progress" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid",
    "book_id" "uuid",
    "current_branch" "text" NOT NULL,
    "choices_made" "jsonb" DEFAULT '[]'::"jsonb",
    "story_state" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."user_story_progress" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_subscriptions" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "tier" "public"."subscription_tier" DEFAULT 'free'::"public"."subscription_tier" NOT NULL,
    "status" "public"."subscription_status" DEFAULT 'active'::"public"."subscription_status" NOT NULL,
    "stripe_customer_id" character varying(255),
    "stripe_subscription_id" character varying(255),
    "stripe_price_id" character varying(255),
    "monthly_video_limit" integer DEFAULT 2 NOT NULL,
    "video_quality" character varying(50) DEFAULT '480p'::character varying,
    "has_watermark" boolean DEFAULT true,
    "current_period_start" timestamp with time zone,
    "current_period_end" timestamp with time zone,
    "videos_generated_this_period" integer DEFAULT 0,
    "next_billing_date" timestamp with time zone,
    "cancel_at_period_end" boolean DEFAULT false,
    "cancelled_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."user_subscriptions" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."video_generations" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "chapter_id" "uuid",
    "script_id" "uuid",
    "user_id" "uuid",
    "generation_status" "public"."video_generation_status" DEFAULT 'pending'::"public"."video_generation_status",
    "quality_tier" "public"."video_quality_tier" DEFAULT 'basic'::"public"."video_quality_tier",
    "video_url" "text",
    "subtitle_url" "text",
    "thumbnail_url" "text",
    "duration_seconds" numeric,
    "file_size_bytes" bigint,
    "script_data" "jsonb",
    "audio_files" "jsonb" DEFAULT '[]'::"jsonb",
    "image_files" "jsonb" DEFAULT '[]'::"jsonb",
    "video_segments" "jsonb" DEFAULT '[]'::"jsonb",
    "progress_log" "jsonb" DEFAULT '[]'::"jsonb",
    "error_message" "text",
    "processing_time_seconds" numeric,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "image_data" "jsonb",
    "video_data" "jsonb",
    "merge_data" "jsonb",
    "lipsync_data" "jsonb",
    "audio_task_id" "text",
    "task_metadata" "jsonb",
    "pipeline_state" "jsonb" DEFAULT '{}'::"jsonb",
    "failed_at_step" "text",
    "can_resume" boolean DEFAULT false,
    "retry_count" integer DEFAULT 0,
    "character_voice_mappings" "jsonb",
    "merge_failed_at" timestamp with time zone,
    "last_retry_at" timestamp with time zone
);


ALTER TABLE "public"."video_generations" OWNER TO "postgres";


COMMENT ON COLUMN "public"."video_generations"."can_resume" IS 'Indicates if manual retry/resume is available for this generation';



COMMENT ON COLUMN "public"."video_generations"."retry_count" IS 'Number of retry attempts for video generation failures';



COMMENT ON COLUMN "public"."video_generations"."merge_failed_at" IS 'Timestamp when the video merge task failed, used for error tracking and retry logic';



COMMENT ON COLUMN "public"."video_generations"."last_retry_at" IS 'Timestamp of the last retry attempt';



CREATE TABLE IF NOT EXISTS "public"."video_segments" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "video_generation_id" "uuid",
    "scene_id" character varying(50),
    "segment_index" integer NOT NULL,
    "video_url" "text",
    "thumbnail_url" "text",
    "duration_seconds" numeric,
    "width" integer,
    "height" integer,
    "file_size_bytes" bigint,
    "status" character varying(50) DEFAULT 'pending'::character varying,
    "error_message" "text",
    "processing_service" character varying(50),
    "processing_model" character varying(100),
    "generation_time_seconds" numeric,
    "metadata" "jsonb" DEFAULT '{}'::"jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "scene_description" "text",
    "source_image_url" "text",
    "fps" integer DEFAULT 24,
    "generation_method" character varying(50),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "key_scene_shot_url" "text"
);


ALTER TABLE "public"."video_segments" OWNER TO "postgres";


COMMENT ON COLUMN "public"."video_segments"."key_scene_shot_url" IS 'URL of the last frame extracted from this video segment, used as starting image for next scene';



CREATE TABLE IF NOT EXISTS "public"."videos" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "book_id" "uuid",
    "chapter_id" "uuid",
    "user_id" "uuid",
    "video_url" "text" NOT NULL,
    "script" "text",
    "character_details" "text",
    "scene_prompt" "text",
    "created_at" bigint NOT NULL,
    "source" "text",
    "klingai_video_url" "text"
);


ALTER TABLE "public"."videos" OWNER TO "postgres";


ALTER TABLE ONLY "public"."audio_exports"
    ADD CONSTRAINT "audio_exports_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."audio_generations"
    ADD CONSTRAINT "audio_generations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."badges"
    ADD CONSTRAINT "badges_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."badges"
    ADD CONSTRAINT "badges_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."book_embeddings"
    ADD CONSTRAINT "book_embeddings_book_id_chunk_type_chunk_index_key" UNIQUE ("book_id", "chunk_type", "chunk_index");



ALTER TABLE ONLY "public"."book_embeddings"
    ADD CONSTRAINT "book_embeddings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."book_sections"
    ADD CONSTRAINT "book_sections_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."books"
    ADD CONSTRAINT "books_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chapter_embeddings"
    ADD CONSTRAINT "chapter_embeddings_chapter_id_chunk_index_key" UNIQUE ("chapter_id", "chunk_index");



ALTER TABLE ONLY "public"."chapter_embeddings"
    ADD CONSTRAINT "chapter_embeddings_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chapter_scripts"
    ADD CONSTRAINT "chapter_scripts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_book_id_chapter_number_key" UNIQUE ("book_id", "chapter_number");



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."character_archetypes"
    ADD CONSTRAINT "character_archetypes_name_key" UNIQUE ("name");



ALTER TABLE ONLY "public"."character_archetypes"
    ADD CONSTRAINT "character_archetypes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."characters"
    ADD CONSTRAINT "characters_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."image_generations"
    ADD CONSTRAINT "image_generations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."learning_content"
    ADD CONSTRAINT "learning_content_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."merge_operations"
    ADD CONSTRAINT "merge_operations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."nft_collectibles"
    ADD CONSTRAINT "nft_collectibles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."pipeline_steps"
    ADD CONSTRAINT "pipeline_steps_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."pipeline_steps"
    ADD CONSTRAINT "pipeline_steps_video_generation_id_step_name_key" UNIQUE ("video_generation_id", "step_name");



ALTER TABLE ONLY "public"."plot_overviews"
    ADD CONSTRAINT "plot_overviews_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."quiz_attempts"
    ADD CONSTRAINT "quiz_attempts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."quizzes"
    ADD CONSTRAINT "quizzes_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."scripts"
    ADD CONSTRAINT "scripts_chapter_id_user_id_script_style_key" UNIQUE ("chapter_id", "user_id", "script_style");



ALTER TABLE ONLY "public"."scripts"
    ADD CONSTRAINT "scripts_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."story_choices"
    ADD CONSTRAINT "story_choices_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subscription_history"
    ADD CONSTRAINT "subscription_history_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subscription_tiers"
    ADD CONSTRAINT "subscription_tiers_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subscription_tiers"
    ADD CONSTRAINT "subscription_tiers_tier_key" UNIQUE ("tier");



ALTER TABLE ONLY "public"."plot_overviews"
    ADD CONSTRAINT "unique_book_user_version" UNIQUE ("book_id", "user_id", "version");



ALTER TABLE ONLY "public"."characters"
    ADD CONSTRAINT "unique_plot_overview_name" UNIQUE ("plot_overview_id", "name");



ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "unique_user_subscription" UNIQUE ("user_id");



ALTER TABLE ONLY "public"."usage_logs"
    ADD CONSTRAINT "usage_logs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_badges"
    ADD CONSTRAINT "user_badges_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_badges"
    ADD CONSTRAINT "user_badges_user_id_badge_id_key" UNIQUE ("user_id", "badge_id");



ALTER TABLE ONLY "public"."user_collectibles"
    ADD CONSTRAINT "user_collectibles_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_collectibles"
    ADD CONSTRAINT "user_collectibles_user_id_collectible_id_key" UNIQUE ("user_id", "collectible_id");



ALTER TABLE ONLY "public"."user_progress"
    ADD CONSTRAINT "user_progress_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_progress"
    ADD CONSTRAINT "user_progress_user_id_book_id_key" UNIQUE ("user_id", "book_id");



ALTER TABLE ONLY "public"."user_story_progress"
    ADD CONSTRAINT "user_story_progress_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_story_progress"
    ADD CONSTRAINT "user_story_progress_user_id_book_id_key" UNIQUE ("user_id", "book_id");



ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."video_generations"
    ADD CONSTRAINT "video_generations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."video_segments"
    ADD CONSTRAINT "video_segments_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."videos"
    ADD CONSTRAINT "videos_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_audio_exports_chapter_id" ON "public"."audio_exports" USING "btree" ("chapter_id");



CREATE INDEX "idx_audio_exports_status" ON "public"."audio_exports" USING "btree" ("status");



CREATE INDEX "idx_audio_exports_user_id" ON "public"."audio_exports" USING "btree" ("user_id");



CREATE INDEX "idx_audio_generations_chapter_id" ON "public"."audio_generations" USING "btree" ("chapter_id");



CREATE INDEX "idx_audio_generations_model_id" ON "public"."audio_generations" USING "btree" ("model_id");



CREATE INDEX "idx_audio_generations_service" ON "public"."audio_generations" USING "btree" ("service_provider");



CREATE INDEX "idx_audio_generations_user_id" ON "public"."audio_generations" USING "btree" ("user_id");



CREATE INDEX "idx_book_embeddings_book_id" ON "public"."book_embeddings" USING "btree" ("book_id");



CREATE INDEX "idx_book_embeddings_embedding" ON "public"."book_embeddings" USING "ivfflat" ("embedding" "public"."vector_cosine_ops") WITH ("lists"='100');



CREATE INDEX "idx_book_sections_book_id" ON "public"."book_sections" USING "btree" ("book_id");



CREATE INDEX "idx_book_sections_order" ON "public"."book_sections" USING "btree" ("book_id", "order_index");



CREATE INDEX "idx_books_author_id" ON "public"."books" USING "btree" ("user_id");



CREATE INDEX "idx_books_original_file_storage_path" ON "public"."books" USING "btree" ("original_file_storage_path");



CREATE INDEX "idx_books_payment_status" ON "public"."books" USING "btree" ("payment_status");



CREATE INDEX "idx_books_stripe_checkout_session_id" ON "public"."books" USING "btree" ("stripe_checkout_session_id");



CREATE INDEX "idx_chapter_embeddings_book_id" ON "public"."chapter_embeddings" USING "btree" ("book_id");



CREATE INDEX "idx_chapter_embeddings_chapter_id" ON "public"."chapter_embeddings" USING "btree" ("chapter_id");



CREATE INDEX "idx_chapter_embeddings_embedding" ON "public"."chapter_embeddings" USING "ivfflat" ("embedding" "public"."vector_cosine_ops") WITH ("lists"='100');



CREATE INDEX "idx_chapter_scripts_chapter" ON "public"."chapter_scripts" USING "btree" ("chapter_id");



CREATE INDEX "idx_chapter_scripts_plot" ON "public"."chapter_scripts" USING "btree" ("plot_overview_id");



CREATE INDEX "idx_chapter_scripts_status" ON "public"."chapter_scripts" USING "btree" ("status");



CREATE INDEX "idx_chapter_scripts_user" ON "public"."chapter_scripts" USING "btree" ("user_id");



CREATE INDEX "idx_chapters_book_id" ON "public"."chapters" USING "btree" ("book_id");



CREATE INDEX "idx_chapters_order" ON "public"."chapters" USING "btree" ("section_id", "order_index");



CREATE INDEX "idx_chapters_section_id" ON "public"."chapters" USING "btree" ("section_id");



CREATE INDEX "idx_character_archetypes_active" ON "public"."character_archetypes" USING "btree" ("is_active");



CREATE INDEX "idx_character_archetypes_category" ON "public"."character_archetypes" USING "btree" ("category");



CREATE INDEX "idx_characters_archetypes" ON "public"."characters" USING "gin" ("archetypes");



CREATE INDEX "idx_characters_book_user" ON "public"."characters" USING "btree" ("book_id", "user_id");



CREATE INDEX "idx_characters_plot_overview" ON "public"."characters" USING "btree" ("plot_overview_id");



CREATE INDEX "idx_characters_role" ON "public"."characters" USING "btree" ("role");



CREATE INDEX "idx_image_generations_character" ON "public"."image_generations" USING "btree" ("character_name");



CREATE INDEX "idx_image_generations_model_id" ON "public"."image_generations" USING "btree" ("model_id");



CREATE INDEX "idx_image_generations_request_id" ON "public"."image_generations" USING "btree" ("request_id");



CREATE INDEX "idx_image_generations_scene_number" ON "public"."image_generations" USING "btree" ("scene_number");



CREATE INDEX "idx_image_generations_service" ON "public"."image_generations" USING "btree" ("service_provider");



CREATE INDEX "idx_image_generations_type" ON "public"."image_generations" USING "btree" ("image_type");



CREATE INDEX "idx_image_generations_user_id" ON "public"."image_generations" USING "btree" ("user_id");



CREATE INDEX "idx_learning_content_book_id" ON "public"."learning_content" USING "btree" ("book_id");



CREATE INDEX "idx_learning_content_chapter_id" ON "public"."learning_content" USING "btree" ("chapter_id");



CREATE INDEX "idx_learning_content_generation_progress" ON "public"."learning_content" USING "btree" ("generation_progress");



CREATE INDEX "idx_learning_content_status" ON "public"."learning_content" USING "btree" ("status");



CREATE INDEX "idx_learning_content_tavus_url" ON "public"."learning_content" USING "btree" ("tavus_url");



CREATE INDEX "idx_learning_content_tavus_video_id" ON "public"."learning_content" USING "btree" ("tavus_video_id");



CREATE INDEX "idx_learning_content_type" ON "public"."learning_content" USING "btree" ("content_type");



CREATE INDEX "idx_learning_content_user_id" ON "public"."learning_content" USING "btree" ("user_id");



CREATE INDEX "idx_merge_operations_status" ON "public"."merge_operations" USING "btree" ("merge_status");



CREATE INDEX "idx_merge_operations_user_id" ON "public"."merge_operations" USING "btree" ("user_id");



CREATE INDEX "idx_pipeline_steps_status" ON "public"."pipeline_steps" USING "btree" ("status");



CREATE INDEX "idx_pipeline_steps_video_gen_id" ON "public"."pipeline_steps" USING "btree" ("video_generation_id");



CREATE INDEX "idx_plot_overviews_book_user" ON "public"."plot_overviews" USING "btree" ("book_id", "user_id");



CREATE INDEX "idx_plot_overviews_created_at" ON "public"."plot_overviews" USING "btree" ("created_at");



CREATE INDEX "idx_plot_overviews_status" ON "public"."plot_overviews" USING "btree" ("status");



CREATE INDEX "idx_quiz_attempts_user_id" ON "public"."quiz_attempts" USING "btree" ("user_id");



CREATE INDEX "idx_scripts_chapter_user" ON "public"."scripts" USING "btree" ("chapter_id", "user_id");



CREATE INDEX "idx_scripts_service_used" ON "public"."scripts" USING "btree" ("service_used");



CREATE INDEX "idx_scripts_style" ON "public"."scripts" USING "btree" ("script_style");



CREATE INDEX "idx_subscription_history_created_at" ON "public"."subscription_history" USING "btree" ("created_at");



CREATE INDEX "idx_subscription_history_event" ON "public"."subscription_history" USING "btree" ("event_type");



CREATE INDEX "idx_subscription_history_subscription_id" ON "public"."subscription_history" USING "btree" ("subscription_id");



CREATE INDEX "idx_subscription_history_user_id" ON "public"."subscription_history" USING "btree" ("user_id");



CREATE INDEX "idx_usage_logs_created_at" ON "public"."usage_logs" USING "btree" ("created_at");



CREATE INDEX "idx_usage_logs_resource" ON "public"."usage_logs" USING "btree" ("resource_type", "resource_id");



CREATE INDEX "idx_usage_logs_subscription_id" ON "public"."usage_logs" USING "btree" ("subscription_id");



CREATE INDEX "idx_usage_logs_user_id" ON "public"."usage_logs" USING "btree" ("user_id");



CREATE INDEX "idx_user_badges_user_id" ON "public"."user_badges" USING "btree" ("user_id");



CREATE INDEX "idx_user_collectibles_user_id" ON "public"."user_collectibles" USING "btree" ("user_id");



CREATE INDEX "idx_user_progress_book_id" ON "public"."user_progress" USING "btree" ("book_id");



CREATE INDEX "idx_user_progress_user_id" ON "public"."user_progress" USING "btree" ("user_id");



CREATE INDEX "idx_user_subscriptions_status" ON "public"."user_subscriptions" USING "btree" ("status");



CREATE INDEX "idx_user_subscriptions_stripe_customer" ON "public"."user_subscriptions" USING "btree" ("stripe_customer_id");



CREATE INDEX "idx_user_subscriptions_user_id" ON "public"."user_subscriptions" USING "btree" ("user_id");



CREATE INDEX "idx_video_generations_audio_task" ON "public"."video_generations" USING "btree" ("audio_task_id");



CREATE INDEX "idx_video_generations_can_resume" ON "public"."video_generations" USING "btree" ("can_resume");



CREATE INDEX "idx_video_generations_chapter" ON "public"."video_generations" USING "btree" ("chapter_id");



CREATE INDEX "idx_video_generations_lipsync_status" ON "public"."video_generations" USING "btree" ("generation_status");



CREATE INDEX "idx_video_generations_merge_status" ON "public"."video_generations" USING "btree" ("generation_status");



CREATE INDEX "idx_video_generations_retry_count" ON "public"."video_generations" USING "btree" ("retry_count");



CREATE INDEX "idx_video_generations_script" ON "public"."video_generations" USING "btree" ("script_id");



CREATE INDEX "idx_video_generations_status" ON "public"."video_generations" USING "btree" ("generation_status");



CREATE INDEX "idx_video_generations_task_metadata" ON "public"."video_generations" USING "gin" ("task_metadata");



CREATE INDEX "idx_video_generations_user" ON "public"."video_generations" USING "btree" ("user_id");



CREATE INDEX "idx_video_segments_generation_method" ON "public"."video_segments" USING "btree" ("generation_method");



CREATE INDEX "idx_video_segments_key_scene_shot" ON "public"."video_segments" USING "btree" ("key_scene_shot_url");



CREATE INDEX "idx_videos_book_id" ON "public"."videos" USING "btree" ("book_id");



CREATE INDEX "idx_videos_chapter_id" ON "public"."videos" USING "btree" ("chapter_id");



CREATE INDEX "idx_videos_user_id" ON "public"."videos" USING "btree" ("user_id");



CREATE OR REPLACE TRIGGER "update_chapter_scripts_updated_at" BEFORE UPDATE ON "public"."chapter_scripts" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_character_archetypes_updated_at" BEFORE UPDATE ON "public"."character_archetypes" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_characters_updated_at" BEFORE UPDATE ON "public"."characters" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_learning_content_updated_at" BEFORE UPDATE ON "public"."learning_content" FOR EACH ROW EXECUTE FUNCTION "public"."update_learning_content_updated_at"();



CREATE OR REPLACE TRIGGER "update_plot_overviews_updated_at" BEFORE UPDATE ON "public"."plot_overviews" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_subscription_tiers_updated_at" BEFORE UPDATE ON "public"."subscription_tiers" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



CREATE OR REPLACE TRIGGER "update_user_subscriptions_updated_at" BEFORE UPDATE ON "public"."user_subscriptions" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."audio_exports"
    ADD CONSTRAINT "audio_exports_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."audio_generations"
    ADD CONSTRAINT "audio_generations_video_generation_id_fkey" FOREIGN KEY ("video_generation_id") REFERENCES "public"."video_generations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."book_embeddings"
    ADD CONSTRAINT "book_embeddings_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."book_sections"
    ADD CONSTRAINT "book_sections_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."books"
    ADD CONSTRAINT "books_author_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapter_embeddings"
    ADD CONSTRAINT "chapter_embeddings_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapter_embeddings"
    ADD CONSTRAINT "chapter_embeddings_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapter_scripts"
    ADD CONSTRAINT "chapter_scripts_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapter_scripts"
    ADD CONSTRAINT "chapter_scripts_plot_overview_id_fkey" FOREIGN KEY ("plot_overview_id") REFERENCES "public"."plot_overviews"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapter_scripts"
    ADD CONSTRAINT "chapter_scripts_script_id_fkey" FOREIGN KEY ("script_id") REFERENCES "public"."scripts"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapter_scripts"
    ADD CONSTRAINT "chapter_scripts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."chapters"
    ADD CONSTRAINT "chapters_section_id_fkey" FOREIGN KEY ("section_id") REFERENCES "public"."book_sections"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."characters"
    ADD CONSTRAINT "characters_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."characters"
    ADD CONSTRAINT "characters_plot_overview_id_fkey" FOREIGN KEY ("plot_overview_id") REFERENCES "public"."plot_overviews"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."characters"
    ADD CONSTRAINT "characters_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."audio_generations"
    ADD CONSTRAINT "fk_audio_generations_user_id" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id");



ALTER TABLE ONLY "public"."image_generations"
    ADD CONSTRAINT "fk_image_generations_user_id" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id");



ALTER TABLE ONLY "public"."image_generations"
    ADD CONSTRAINT "image_generations_video_generation_id_fkey" FOREIGN KEY ("video_generation_id") REFERENCES "public"."video_generations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."learning_content"
    ADD CONSTRAINT "learning_content_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."learning_content"
    ADD CONSTRAINT "learning_content_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."learning_content"
    ADD CONSTRAINT "learning_content_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."merge_operations"
    ADD CONSTRAINT "merge_operations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."nft_collectibles"
    ADD CONSTRAINT "nft_collectibles_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."nft_collectibles"
    ADD CONSTRAINT "nft_collectibles_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."pipeline_steps"
    ADD CONSTRAINT "pipeline_steps_video_generation_id_fkey" FOREIGN KEY ("video_generation_id") REFERENCES "public"."video_generations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."plot_overviews"
    ADD CONSTRAINT "plot_overviews_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."plot_overviews"
    ADD CONSTRAINT "plot_overviews_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."profiles"
    ADD CONSTRAINT "profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."quiz_attempts"
    ADD CONSTRAINT "quiz_attempts_quiz_id_fkey" FOREIGN KEY ("quiz_id") REFERENCES "public"."quizzes"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."quiz_attempts"
    ADD CONSTRAINT "quiz_attempts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."quizzes"
    ADD CONSTRAINT "quizzes_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."scripts"
    ADD CONSTRAINT "scripts_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."scripts"
    ADD CONSTRAINT "scripts_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."story_choices"
    ADD CONSTRAINT "story_choices_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."story_choices"
    ADD CONSTRAINT "story_choices_next_chapter_id_fkey" FOREIGN KEY ("next_chapter_id") REFERENCES "public"."chapters"("id");



ALTER TABLE ONLY "public"."subscription_history"
    ADD CONSTRAINT "subscription_history_subscription_id_fkey" FOREIGN KEY ("subscription_id") REFERENCES "public"."user_subscriptions"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."subscription_history"
    ADD CONSTRAINT "subscription_history_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."usage_logs"
    ADD CONSTRAINT "usage_logs_subscription_id_fkey" FOREIGN KEY ("subscription_id") REFERENCES "public"."user_subscriptions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."usage_logs"
    ADD CONSTRAINT "usage_logs_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_badges"
    ADD CONSTRAINT "user_badges_badge_id_fkey" FOREIGN KEY ("badge_id") REFERENCES "public"."badges"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_badges"
    ADD CONSTRAINT "user_badges_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_collectibles"
    ADD CONSTRAINT "user_collectibles_collectible_id_fkey" FOREIGN KEY ("collectible_id") REFERENCES "public"."nft_collectibles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_collectibles"
    ADD CONSTRAINT "user_collectibles_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_progress"
    ADD CONSTRAINT "user_progress_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_progress"
    ADD CONSTRAINT "user_progress_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_story_progress"
    ADD CONSTRAINT "user_story_progress_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_story_progress"
    ADD CONSTRAINT "user_story_progress_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_subscriptions"
    ADD CONSTRAINT "user_subscriptions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."video_generations"
    ADD CONSTRAINT "video_generations_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."video_generations"
    ADD CONSTRAINT "video_generations_script_id_fkey" FOREIGN KEY ("script_id") REFERENCES "public"."scripts"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."video_generations"
    ADD CONSTRAINT "video_generations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."video_segments"
    ADD CONSTRAINT "video_segments_video_generation_id_fkey" FOREIGN KEY ("video_generation_id") REFERENCES "public"."video_generations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."videos"
    ADD CONSTRAINT "videos_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "public"."books"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."videos"
    ADD CONSTRAINT "videos_chapter_id_fkey" FOREIGN KEY ("chapter_id") REFERENCES "public"."chapters"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."videos"
    ADD CONSTRAINT "videos_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."profiles"("id") ON DELETE SET NULL;



CREATE POLICY "Anyone can read badges" ON "public"."badges" FOR SELECT TO "authenticated";



CREATE POLICY "Anyone can read collectibles" ON "public"."nft_collectibles" FOR SELECT TO "authenticated";



CREATE POLICY "Anyone can read ready books" ON "public"."books" FOR SELECT USING (("status" = 'READY'::"public"."book_status"));



CREATE POLICY "Authors can create books" ON "public"."books" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "Authors can manage embeddings for own books" ON "public"."book_embeddings" TO "authenticated" USING (("book_id" IN ( SELECT "books"."id"
   FROM "public"."books"
  WHERE ("books"."user_id" = "auth"."uid"()))));



CREATE POLICY "Authors can manage embeddings for own chapters" ON "public"."chapter_embeddings" TO "authenticated" USING (("book_id" IN ( SELECT "books"."id"
   FROM "public"."books"
  WHERE ("books"."user_id" = "auth"."uid"()))));



CREATE POLICY "Authors can read own books" ON "public"."books" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Authors can update own books" ON "public"."books" FOR UPDATE TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Everyone can view active character archetypes" ON "public"."character_archetypes" FOR SELECT USING (("is_active" = true));



CREATE POLICY "Everyone can view subscription tiers" ON "public"."subscription_tiers" FOR SELECT USING (("is_active" = true));



CREATE POLICY "Service role can manage chapters" ON "public"."chapters" TO "service_role" USING (true) WITH CHECK (true);



CREATE POLICY "Service role full access to chapter scripts" ON "public"."chapter_scripts" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to character archetypes" ON "public"."character_archetypes" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to characters" ON "public"."characters" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to plot overviews" ON "public"."plot_overviews" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to subscription history" ON "public"."subscription_history" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to subscription tiers" ON "public"."subscription_tiers" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to subscriptions" ON "public"."user_subscriptions" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "Service role full access to usage logs" ON "public"."usage_logs" USING ((("auth"."jwt"() ->> 'role'::"text") = 'service_role'::"text"));



CREATE POLICY "System can award badges" ON "public"."user_badges" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "System can award collectibles" ON "public"."user_collectibles" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can access chapters based on book status" ON "public"."chapters" TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM "public"."books" "b"
  WHERE ("b"."id" = "chapters"."book_id")))) WITH CHECK ((EXISTS ( SELECT 1
   FROM "public"."books" "b"
  WHERE (("b"."id" = "chapters"."book_id") AND ("b"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can create own quiz attempts" ON "public"."quiz_attempts" FOR INSERT TO "authenticated" WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can delete own chapter scripts" ON "public"."chapter_scripts" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own characters" ON "public"."characters" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own plot overviews" ON "public"."plot_overviews" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own book records" ON "public"."books" FOR DELETE TO "authenticated" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete their own learning content" ON "public"."learning_content" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own chapter scripts" ON "public"."chapter_scripts" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own characters" ON "public"."characters" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own plot overviews" ON "public"."plot_overviews" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own profile" ON "public"."profiles" FOR INSERT TO "authenticated" WITH CHECK (("auth"."uid"() = "id"));



CREATE POLICY "Users can insert their own audio generations" ON "public"."audio_generations" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own image generations" ON "public"."image_generations" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert their own learning content" ON "public"."learning_content" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can manage own books and view ready books" ON "public"."books" TO "authenticated" USING ((("user_id" = "auth"."uid"()) OR ("status" = 'READY'::"public"."book_status"))) WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can manage own progress" ON "public"."user_progress" TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can manage own story progress" ON "public"."user_story_progress" TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can manage their own scripts" ON "public"."scripts" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can manage their own video generations" ON "public"."video_generations" USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can read chapters of ready books" ON "public"."chapters" FOR SELECT USING ((( SELECT "books"."status"
   FROM "public"."books"
  WHERE ("books"."id" = "chapters"."book_id")) = 'READY'::"public"."book_status"));



CREATE POLICY "Users can read embeddings for accessible books" ON "public"."book_embeddings" FOR SELECT TO "authenticated" USING (("book_id" IN ( SELECT "books"."id"
   FROM "public"."books"
  WHERE (("books"."status" = 'READY'::"public"."book_status") OR ("books"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can read embeddings for accessible chapters" ON "public"."chapter_embeddings" FOR SELECT TO "authenticated" USING (("chapter_id" IN ( SELECT "c"."id"
   FROM ("public"."chapters" "c"
     JOIN "public"."books" "b" ON (("c"."book_id" = "b"."id")))
  WHERE (("b"."status" = 'READY'::"public"."book_status") OR ("b"."user_id" = "auth"."uid"())))));



CREATE POLICY "Users can read own badges" ON "public"."user_badges" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can read own collectibles" ON "public"."user_collectibles" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can read own profile" ON "public"."profiles" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "id"));



CREATE POLICY "Users can read own progress" ON "public"."user_progress" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can read own quiz attempts" ON "public"."quiz_attempts" FOR SELECT TO "authenticated" USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can read quizzes for ready books" ON "public"."quizzes" FOR SELECT USING ((( SELECT "books"."status"
   FROM "public"."books"
  WHERE ("books"."id" = ( SELECT "chapters"."book_id"
           FROM "public"."chapters"
          WHERE ("chapters"."id" = "quizzes"."chapter_id")))) = 'READY'::"public"."book_status"));



CREATE POLICY "Users can read story choices for ready books" ON "public"."story_choices" FOR SELECT USING ((( SELECT "books"."status"
   FROM "public"."books"
  WHERE ("books"."id" = ( SELECT "chapters"."book_id"
           FROM "public"."chapters"
          WHERE ("chapters"."id" = "story_choices"."chapter_id")))) = 'READY'::"public"."book_status"));



CREATE POLICY "Users can update own chapter scripts" ON "public"."chapter_scripts" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own characters" ON "public"."characters" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own plot overviews" ON "public"."plot_overviews" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own profile" ON "public"."profiles" FOR UPDATE TO "authenticated" USING (("auth"."uid"() = "id"));



CREATE POLICY "Users can update their own learning content" ON "public"."learning_content" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own chapter scripts" ON "public"."chapter_scripts" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own characters" ON "public"."characters" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own plot overviews" ON "public"."plot_overviews" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own subscription" ON "public"."user_subscriptions" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own subscription history" ON "public"."subscription_history" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own usage logs" ON "public"."usage_logs" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view their audio generations" ON "public"."audio_generations" FOR SELECT USING ((("auth"."uid"() = "user_id") OR (EXISTS ( SELECT 1
   FROM "public"."video_generations"
  WHERE (("video_generations"."id" = "audio_generations"."video_generation_id") AND ("video_generations"."user_id" = "auth"."uid"()))))));



CREATE POLICY "Users can view their image generations" ON "public"."image_generations" FOR SELECT USING ((("auth"."uid"() = "user_id") OR (EXISTS ( SELECT 1
   FROM "public"."video_generations"
  WHERE (("video_generations"."id" = "image_generations"."video_generation_id") AND ("video_generations"."user_id" = "auth"."uid"()))))));



CREATE POLICY "Users can view their own learning content" ON "public"."learning_content" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view video segments for their videos" ON "public"."video_segments" USING ((EXISTS ( SELECT 1
   FROM "public"."video_generations"
  WHERE (("video_generations"."id" = "video_segments"."video_generation_id") AND ("video_generations"."user_id" = "auth"."uid"())))));



ALTER TABLE "public"."audio_generations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."badges" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."book_embeddings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."book_sections" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."books" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."chapter_embeddings" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."chapter_scripts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."chapters" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."character_archetypes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."characters" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."image_generations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."learning_content" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."nft_collectibles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."plot_overviews" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."profiles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."quiz_attempts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."quizzes" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."scripts" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."story_choices" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."subscription_history" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."subscription_tiers" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."usage_logs" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_badges" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_collectibles" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_progress" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_story_progress" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."user_subscriptions" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."video_generations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."video_segments" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_out"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_send"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_out"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_send"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_in"("cstring", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_out"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_recv"("internal", "oid", integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_send"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_typmod_in"("cstring"[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(real[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(double precision[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(integer[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_halfvec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_sparsevec"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."array_to_vector"(numeric[], integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_float4"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_sparsevec"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_to_vector"("public"."halfvec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_halfvec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_to_vector"("public"."sparsevec", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_float4"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_halfvec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_to_sparsevec"("public"."vector", integer, boolean) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "anon";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector"("public"."vector", integer, boolean) TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."binary_quantize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."check_usage_limit"("p_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."check_usage_limit"("p_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."check_usage_limit"("p_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cosine_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_accum"(double precision[], "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_add"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_cmp"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_concat"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_eq"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ge"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_gt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_l2_squared_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_le"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_lt"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_mul"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_ne"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_negative_inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_spherical_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."halfvec_sub"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."hamming_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnsw_sparsevec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hnswhandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."increment_usage"("p_user_id" "uuid", "p_resource_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."increment_usage"("p_user_id" "uuid", "p_resource_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."increment_usage"("p_user_id" "uuid", "p_resource_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_bit_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflat_halfvec_support"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "postgres";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "anon";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "authenticated";
GRANT ALL ON FUNCTION "public"."ivfflathandler"("internal") TO "service_role";



GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "postgres";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "anon";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "authenticated";
GRANT ALL ON FUNCTION "public"."jaccard_distance"(bit, bit) TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l1_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."halfvec", "public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_norm"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."l2_normalize"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."match_book_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."match_book_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_book_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."match_chapter_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."match_chapter_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."match_chapter_embeddings"("query_embedding" "public"."vector", "match_threshold" double precision, "match_count" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."reset_monthly_usage"() TO "anon";
GRANT ALL ON FUNCTION "public"."reset_monthly_usage"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."reset_monthly_usage"() TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_cmp"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_eq"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ge"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_gt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_l2_squared_distance"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_le"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_lt"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_ne"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "anon";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sparsevec_negative_inner_product"("public"."sparsevec", "public"."sparsevec") TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."halfvec", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "postgres";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "anon";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."subvector"("public"."vector", integer, integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."update_learning_content_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_learning_content_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_learning_content_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_accum"(double precision[], "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_add"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_avg"(double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_cmp"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "anon";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_combine"(double precision[], double precision[]) TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_concat"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_dims"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_eq"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ge"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_gt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_l2_squared_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_le"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_lt"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_mul"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_ne"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_negative_inner_product"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_norm"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_spherical_distance"("public"."vector", "public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."vector_sub"("public"."vector", "public"."vector") TO "service_role";












GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."avg"("public"."vector") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."halfvec") TO "service_role";



GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "postgres";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "anon";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "authenticated";
GRANT ALL ON FUNCTION "public"."sum"("public"."vector") TO "service_role";









GRANT ALL ON TABLE "public"."audio_exports" TO "anon";
GRANT ALL ON TABLE "public"."audio_exports" TO "authenticated";
GRANT ALL ON TABLE "public"."audio_exports" TO "service_role";



GRANT ALL ON TABLE "public"."audio_generations" TO "anon";
GRANT ALL ON TABLE "public"."audio_generations" TO "authenticated";
GRANT ALL ON TABLE "public"."audio_generations" TO "service_role";



GRANT ALL ON TABLE "public"."badges" TO "anon";
GRANT ALL ON TABLE "public"."badges" TO "authenticated";
GRANT ALL ON TABLE "public"."badges" TO "service_role";



GRANT ALL ON TABLE "public"."book_embeddings" TO "anon";
GRANT ALL ON TABLE "public"."book_embeddings" TO "authenticated";
GRANT ALL ON TABLE "public"."book_embeddings" TO "service_role";



GRANT ALL ON TABLE "public"."book_sections" TO "anon";
GRANT ALL ON TABLE "public"."book_sections" TO "authenticated";
GRANT ALL ON TABLE "public"."book_sections" TO "service_role";



GRANT ALL ON TABLE "public"."books" TO "anon";
GRANT ALL ON TABLE "public"."books" TO "authenticated";
GRANT ALL ON TABLE "public"."books" TO "service_role";



GRANT ALL ON TABLE "public"."chapter_embeddings" TO "anon";
GRANT ALL ON TABLE "public"."chapter_embeddings" TO "authenticated";
GRANT ALL ON TABLE "public"."chapter_embeddings" TO "service_role";



GRANT ALL ON TABLE "public"."chapter_scripts" TO "anon";
GRANT ALL ON TABLE "public"."chapter_scripts" TO "authenticated";
GRANT ALL ON TABLE "public"."chapter_scripts" TO "service_role";



GRANT ALL ON TABLE "public"."chapters" TO "anon";
GRANT ALL ON TABLE "public"."chapters" TO "authenticated";
GRANT ALL ON TABLE "public"."chapters" TO "service_role";



GRANT ALL ON TABLE "public"."character_archetypes" TO "anon";
GRANT ALL ON TABLE "public"."character_archetypes" TO "authenticated";
GRANT ALL ON TABLE "public"."character_archetypes" TO "service_role";



GRANT ALL ON TABLE "public"."characters" TO "anon";
GRANT ALL ON TABLE "public"."characters" TO "authenticated";
GRANT ALL ON TABLE "public"."characters" TO "service_role";



GRANT ALL ON TABLE "public"."image_generations" TO "anon";
GRANT ALL ON TABLE "public"."image_generations" TO "authenticated";
GRANT ALL ON TABLE "public"."image_generations" TO "service_role";



GRANT ALL ON TABLE "public"."learning_content" TO "anon";
GRANT ALL ON TABLE "public"."learning_content" TO "authenticated";
GRANT ALL ON TABLE "public"."learning_content" TO "service_role";



GRANT ALL ON TABLE "public"."merge_operations" TO "anon";
GRANT ALL ON TABLE "public"."merge_operations" TO "authenticated";
GRANT ALL ON TABLE "public"."merge_operations" TO "service_role";



GRANT ALL ON TABLE "public"."nft_collectibles" TO "anon";
GRANT ALL ON TABLE "public"."nft_collectibles" TO "authenticated";
GRANT ALL ON TABLE "public"."nft_collectibles" TO "service_role";



GRANT ALL ON TABLE "public"."pipeline_steps" TO "anon";
GRANT ALL ON TABLE "public"."pipeline_steps" TO "authenticated";
GRANT ALL ON TABLE "public"."pipeline_steps" TO "service_role";



GRANT ALL ON TABLE "public"."plot_overviews" TO "anon";
GRANT ALL ON TABLE "public"."plot_overviews" TO "authenticated";
GRANT ALL ON TABLE "public"."plot_overviews" TO "service_role";



GRANT ALL ON TABLE "public"."profiles" TO "anon";
GRANT ALL ON TABLE "public"."profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."profiles" TO "service_role";



GRANT ALL ON TABLE "public"."quiz_attempts" TO "anon";
GRANT ALL ON TABLE "public"."quiz_attempts" TO "authenticated";
GRANT ALL ON TABLE "public"."quiz_attempts" TO "service_role";



GRANT ALL ON TABLE "public"."quizzes" TO "anon";
GRANT ALL ON TABLE "public"."quizzes" TO "authenticated";
GRANT ALL ON TABLE "public"."quizzes" TO "service_role";



GRANT ALL ON TABLE "public"."scripts" TO "anon";
GRANT ALL ON TABLE "public"."scripts" TO "authenticated";
GRANT ALL ON TABLE "public"."scripts" TO "service_role";



GRANT ALL ON TABLE "public"."story_choices" TO "anon";
GRANT ALL ON TABLE "public"."story_choices" TO "authenticated";
GRANT ALL ON TABLE "public"."story_choices" TO "service_role";



GRANT ALL ON TABLE "public"."subscription_history" TO "anon";
GRANT ALL ON TABLE "public"."subscription_history" TO "authenticated";
GRANT ALL ON TABLE "public"."subscription_history" TO "service_role";



GRANT ALL ON TABLE "public"."subscription_tiers" TO "anon";
GRANT ALL ON TABLE "public"."subscription_tiers" TO "authenticated";
GRANT ALL ON TABLE "public"."subscription_tiers" TO "service_role";



GRANT ALL ON TABLE "public"."usage_logs" TO "anon";
GRANT ALL ON TABLE "public"."usage_logs" TO "authenticated";
GRANT ALL ON TABLE "public"."usage_logs" TO "service_role";



GRANT ALL ON TABLE "public"."user_badges" TO "anon";
GRANT ALL ON TABLE "public"."user_badges" TO "authenticated";
GRANT ALL ON TABLE "public"."user_badges" TO "service_role";



GRANT ALL ON TABLE "public"."user_collectibles" TO "anon";
GRANT ALL ON TABLE "public"."user_collectibles" TO "authenticated";
GRANT ALL ON TABLE "public"."user_collectibles" TO "service_role";



GRANT ALL ON TABLE "public"."user_progress" TO "anon";
GRANT ALL ON TABLE "public"."user_progress" TO "authenticated";
GRANT ALL ON TABLE "public"."user_progress" TO "service_role";



GRANT ALL ON TABLE "public"."user_story_progress" TO "anon";
GRANT ALL ON TABLE "public"."user_story_progress" TO "authenticated";
GRANT ALL ON TABLE "public"."user_story_progress" TO "service_role";



GRANT ALL ON TABLE "public"."user_subscriptions" TO "anon";
GRANT ALL ON TABLE "public"."user_subscriptions" TO "authenticated";
GRANT ALL ON TABLE "public"."user_subscriptions" TO "service_role";



GRANT ALL ON TABLE "public"."video_generations" TO "anon";
GRANT ALL ON TABLE "public"."video_generations" TO "authenticated";
GRANT ALL ON TABLE "public"."video_generations" TO "service_role";



GRANT ALL ON TABLE "public"."video_segments" TO "anon";
GRANT ALL ON TABLE "public"."video_segments" TO "authenticated";
GRANT ALL ON TABLE "public"."video_segments" TO "service_role";



GRANT ALL ON TABLE "public"."videos" TO "anon";
GRANT ALL ON TABLE "public"."videos" TO "authenticated";
GRANT ALL ON TABLE "public"."videos" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






























RESET ALL;

  create policy "Allow authenticated delete for own files in books bucket"
  on "storage"."objects"
  as permissive
  for delete
  to authenticated
using ((auth.uid() = owner));



  create policy "Allow authenticated inserts in books bucket"
  on "storage"."objects"
  as permissive
  for insert
  to authenticated
with check ((bucket_id = 'books'::text));



  create policy "Allow authenticated update for own files in books bucket"
  on "storage"."objects"
  as permissive
  for update
  to authenticated
using ((auth.uid() = owner));



  create policy "Allow authenticated view for own files in books bucket"
  on "storage"."objects"
  as permissive
  for select
  to authenticated
using ((auth.uid() = owner));



