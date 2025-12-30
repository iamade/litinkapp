-- ============================================
-- Migration Validation Script
-- ============================================
-- Run this in Supabase Studio SQL Editor after migrations
-- to verify everything was created correctly
-- ============================================

-- 1. Check all expected tables exist
SELECT
  'Tables Check' as check_name,
  COUNT(*) as count,
  CASE
    WHEN COUNT(*) >= 12 THEN '✅ PASS'
    ELSE '❌ FAIL - Expected at least 12 tables'
  END as status
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

-- 2. List all tables
SELECT
  table_name,
  (SELECT COUNT(*) FROM information_schema.columns c WHERE c.table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name;

-- 3. Check plot_overviews table exists (the one causing the error)
SELECT
  'plot_overviews table' as check_name,
  CASE
    WHEN EXISTS (
      SELECT 1 FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = 'plot_overviews'
    ) THEN '✅ EXISTS'
    ELSE '❌ MISSING'
  END as status;

-- 4. Check script_story_type columns exist
SELECT
  table_name,
  column_name,
  data_type,
  '✅ Column exists' as status
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name = 'script_story_type'
ORDER BY table_name;

-- 5. Check RLS is enabled on all tables
SELECT
  tablename,
  CASE
    WHEN rowsecurity THEN '✅ RLS Enabled'
    ELSE '❌ RLS Disabled'
  END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 6. Check foreign key relationships
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table,
  '✅ Foreign key exists' as status
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
  AND tc.table_name IN ('plot_overviews', 'scripts', 'characters', 'image_generations', 'audio_generations')
ORDER BY tc.table_name, kcu.column_name;

-- 7. Check indexes were created
SELECT
  'Indexes Check' as check_name,
  COUNT(*) as index_count,
  CASE
    WHEN COUNT(*) >= 20 THEN '✅ PASS'
    ELSE '⚠️ WARNING - Expected at least 20 indexes'
  END as status
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname LIKE 'idx_%';

-- 8. Check ENUM types exist
SELECT
  t.typname as enum_name,
  '✅ ENUM exists' as status
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname = 'public'
  AND t.typtype = 'e'
ORDER BY t.typname;

-- 9. Sample data check (from seed.sql)
SELECT
  'Seed Data Check' as check_name,
  (SELECT COUNT(*) FROM profiles) as profiles_count,
  (SELECT COUNT(*) FROM books) as books_count,
  (SELECT COUNT(*) FROM chapters) as chapters_count,
  (SELECT COUNT(*) FROM user_subscriptions) as subscriptions_count,
  CASE
    WHEN (SELECT COUNT(*) FROM profiles) > 0 THEN '✅ Seed data loaded'
    ELSE '⚠️ No seed data found'
  END as status;

-- 10. Final summary
SELECT
  '=== MIGRATION VALIDATION SUMMARY ===' as summary,
  CASE
    WHEN (
      SELECT COUNT(*) FROM information_schema.tables
      WHERE table_schema = 'public' AND table_name = 'plot_overviews'
    ) = 1
    AND (
      SELECT COUNT(*) FROM information_schema.columns
      WHERE table_schema = 'public'
        AND table_name = 'plot_overviews'
        AND column_name = 'script_story_type'
    ) = 1
    AND (
      SELECT COUNT(*) FROM pg_tables
      WHERE schemaname = 'public' AND rowsecurity = true
    ) >= 10
    THEN '✅✅✅ ALL CHECKS PASSED - Migration successful!'
    ELSE '❌ Some checks failed - Review results above'
  END as final_status;
