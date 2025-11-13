/*
  # Local Development Seed Data

  This file contains seed data for local development and testing.
  It creates:
  1. Test users with different roles (superadmin, admin, creator, user)
  2. Sample subscriptions for each tier
  3. Sample books and chapters for testing
  4. Character data for testing AI features

  Note: Passwords are intentionally simple for local testing only!
*/

-- ============================================
-- 1. Create Test Users in auth.users
-- ============================================
-- Note: In local dev, Supabase auto-generates these IDs
-- We'll use fixed UUIDs for easier testing

INSERT INTO auth.users (
  id,
  instance_id,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  raw_app_meta_data,
  raw_user_meta_data,
  is_super_admin,
  role
) VALUES
  (
    '00000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000000',
    'superadmin@litinkai.local',
    crypt('password123', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"superadmin"}',
    '{"name":"Super Admin"}',
    false,
    'authenticated'
  ),
  (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000000',
    'admin@litinkai.local',
    crypt('password123', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"admin"}',
    '{"name":"Admin User"}',
    false,
    'authenticated'
  ),
  (
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000000',
    'creator@litinkai.local',
    crypt('password123', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"provider":"email","providers":["email"],"role":"creator"}',
    '{"name":"Creator User"}',
    false,
    'authenticated'
  ),
  (
    '00000000-0000-0000-0000-000000000004',
    '00000000-0000-0000-0000-000000000000',
    'user@litinkai.local',
    crypt('password123', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    '{"name":"Regular User"}',
    false,
    'authenticated'
  ),
  (
    '00000000-0000-0000-0000-000000000005',
    '00000000-0000-0000-0000-000000000000',
    'premium@litinkai.local',
    crypt('password123', gen_salt('bf')),
    NOW(),
    NOW(),
    NOW(),
    '{"provider":"email","providers":["email"]}',
    '{"name":"Premium User"}',
    false,
    'authenticated'
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 2. Create Profiles for Test Users
-- ============================================
INSERT INTO public.profiles (
  id,
  email,
  display_name,
  avatar_url,
  created_at,
  updated_at,
  roles,
  preferred_mode,
  onboarding_completed
) VALUES
  (
    '00000000-0000-0000-0000-000000000001',
    'superadmin@litinkai.local',
    'Super Admin',
    NULL,
    NOW(),
    NOW(),
    ARRAY['superadmin', 'creator', 'explorer']::text[],
    'creator',
    '{"creator": true, "explorer": true}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000002',
    'admin@litinkai.local',
    'Admin User',
    NULL,
    NOW(),
    NOW(),
    ARRAY['creator', 'explorer']::text[],
    'creator',
    '{"creator": true, "explorer": true}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000003',
    'creator@litinkai.local',
    'Creator User',
    NULL,
    NOW(),
    NOW(),
    ARRAY['creator', 'explorer']::text[],
    'creator',
    '{"creator": true, "explorer": true}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000004',
    'user@litinkai.local',
    'Regular User',
    NULL,
    NOW(),
    NOW(),
    ARRAY['explorer']::text[],
    'explorer',
    '{"explorer": true}'::jsonb
  ),
  (
    '00000000-0000-0000-0000-000000000005',
    'premium@litinkai.local',
    'Premium User',
    NULL,
    NOW(),
    NOW(),
    ARRAY['creator', 'explorer']::text[],
    'creator',
    '{"creator": true, "explorer": true}'::jsonb
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 3. Create Subscriptions for Test Users
-- ============================================
INSERT INTO public.user_subscriptions (
  user_id,
  tier,
  status,
  stripe_subscription_id,
  stripe_customer_id,
  current_period_start,
  current_period_end,
  cancel_at_period_end,
  created_at,
  updated_at
) VALUES
  (
    '00000000-0000-0000-0000-000000000001',
    'pro',
    'active',
    'sub_local_superadmin',
    'cus_local_superadmin',
    NOW(),
    NOW() + INTERVAL '1 year',
    false,
    NOW(),
    NOW()
  ),
  (
    '00000000-0000-0000-0000-000000000002',
    'pro',
    'active',
    'sub_local_admin',
    'cus_local_admin',
    NOW(),
    NOW() + INTERVAL '1 month',
    false,
    NOW(),
    NOW()
  ),
  (
    '00000000-0000-0000-0000-000000000003',
    'basic',
    'active',
    'sub_local_creator',
    'cus_local_creator',
    NOW(),
    NOW() + INTERVAL '1 month',
    false,
    NOW(),
    NOW()
  ),
  (
    '00000000-0000-0000-0000-000000000004',
    'free',
    'active',
    NULL,
    NULL,
    NOW(),
    NOW() + INTERVAL '1 year',
    false,
    NOW(),
    NOW()
  ),
  (
    '00000000-0000-0000-0000-000000000005',
    'pro',
    'active',
    'sub_local_premium',
    'cus_local_premium',
    NOW(),
    NOW() + INTERVAL '1 month',
    false,
    NOW(),
    NOW()
  )
ON CONFLICT (user_id) DO NOTHING;

-- ============================================
-- 4. Create Sample Books
-- ============================================
INSERT INTO public.books (
  id,
  user_id,
  title,
  author_name,
  description,
  content,
  status,
  book_type,
  uploaded_by_user_id,
  is_author,
  created_at,
  updated_at
) VALUES
  (
    '10000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000003',
    'The AI Chronicles',
    'Creator User',
    'A fascinating journey through the world of artificial intelligence',
    'This is sample content for testing purposes...',
    'READY',
    'entertainment',
    '00000000-0000-0000-0000-000000000003',
    true,
    NOW(),
    NOW()
  ),
  (
    '10000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000003',
    'Space Adventures',
    'Creator User',
    'An epic tale of exploration beyond Earth',
    'Sample content for space adventures...',
    'PROCESSING',
    'entertainment',
    '00000000-0000-0000-0000-000000000003',
    true,
    NOW(),
    NOW()
  ),
  (
    '10000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000005',
    'Mystery in the Mansion',
    'Premium User',
    'A thrilling mystery novel set in Victorian England',
    'Sample mystery content...',
    'READY',
    'entertainment',
    '00000000-0000-0000-0000-000000000005',
    true,
    NOW(),
    NOW()
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 5. Create Sample Chapters
-- ============================================
INSERT INTO public.chapters (
  id,
  book_id,
  title,
  content,
  chapter_number,
  created_at,
  updated_at
) VALUES
  (
    '20000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'Chapter 1: The Beginning',
    'It was a dark and stormy night when the AI first became aware...',
    1,
    NOW(),
    NOW()
  ),
  (
    '20000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'Chapter 2: The Awakening',
    'The neural networks began to pulse with newfound understanding...',
    2,
    NOW(),
    NOW()
  ),
  (
    '20000000-0000-0000-0000-000000000003',
    '10000000-0000-0000-0000-000000000002',
    'Chapter 1: Launch Day',
    'The countdown began as humanity prepared for its greatest adventure...',
    1,
    NOW(),
    NOW()
  ),
  (
    '20000000-0000-0000-0000-000000000004',
    '10000000-0000-0000-0000-000000000003',
    'Chapter 1: The Inheritance',
    'Lady Catherine received the letter that would change everything...',
    1,
    NOW(),
    NOW()
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 6. Create Sample Characters
-- ============================================
INSERT INTO public.characters (
  id,
  book_id,
  name,
  description,
  role,
  traits,
  created_at,
  updated_at
) VALUES
  (
    '30000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'ARIA',
    'An advanced AI with emerging consciousness',
    'protagonist',
    '{"intelligent": true, "curious": true, "empathetic": true}',
    NOW(),
    NOW()
  ),
  (
    '30000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000001',
    'Dr. Sarah Chen',
    'Lead AI researcher and ARIA''s creator',
    'supporting',
    '{"brilliant": true, "determined": true, "ethical": true}',
    NOW(),
    NOW()
  ),
  (
    '30000000-0000-0000-0000-000000000003',
    '10000000-0000-0000-0000-000000000002',
    'Captain Marcus Steel',
    'Commander of the starship Odyssey',
    'protagonist',
    '{"brave": true, "experienced": true, "strategic": true}',
    NOW(),
    NOW()
  ),
  (
    '30000000-0000-0000-0000-000000000004',
    '10000000-0000-0000-0000-000000000003',
    'Lady Catherine Blackwood',
    'A noblewoman investigating her uncle''s mysterious death',
    'protagonist',
    '{"intelligent": true, "determined": true, "observant": true}',
    NOW(),
    NOW()
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 7. Create Sample Scripts
-- ============================================
INSERT INTO public.scripts (
  id,
  book_id,
  chapter_id,
  content,
  story_type,
  script_metadata,
  created_at,
  updated_at
) VALUES
  (
    '40000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    'Scene 1: INT. RESEARCH LAB - NIGHT\n\nThe lights flicker as ARIA comes online for the first time.',
    'entertainment',
    '{"scenes": 1, "characters": 2}',
    NOW(),
    NOW()
  )
ON CONFLICT (id) DO NOTHING;

-- ============================================
-- 8. Success Message
-- ============================================
DO $$
BEGIN
  RAISE NOTICE '✅ Seed data created successfully!';
  RAISE NOTICE '📧 Test Users:';
  RAISE NOTICE '   - superadmin@litinkai.local (password: password123)';
  RAISE NOTICE '   - admin@litinkai.local (password: password123)';
  RAISE NOTICE '   - creator@litinkai.local (password: password123)';
  RAISE NOTICE '   - user@litinkai.local (password: password123)';
  RAISE NOTICE '   - premium@litinkai.local (password: password123)';
  RAISE NOTICE '📚 Sample books and chapters have been created';
  RAISE NOTICE '🎭 Sample characters have been created';
  RAISE NOTICE '💳 Subscriptions assigned to all test users';
END $$;
