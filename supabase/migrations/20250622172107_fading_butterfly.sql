/*
  # Initial Litink Database Schema

  1. New Tables
    - `profiles` - User profile information
    - `books` - Book content and metadata
    - `chapters` - Individual book chapters
    - `user_progress` - Track user reading progress
    - `quizzes` - AI-generated quizzes
    - `quiz_attempts` - User quiz attempts and scores
    - `badges` - Achievement badges
    - `user_badges` - User earned badges
    - `nft_collectibles` - Story NFT collectibles
    - `user_collectibles` - User owned NFTs
    - `story_choices` - Interactive story choices
    - `user_story_progress` - User story progression

  2. Security
    - Enable RLS on all tables
    - Add policies for authenticated users
*/

-- Create custom types
CREATE TYPE user_role AS ENUM ('author', 'explorer');
CREATE TYPE book_type AS ENUM ('learning', 'entertainment');
CREATE TYPE difficulty_level AS ENUM ('easy', 'medium', 'hard');
CREATE TYPE badge_rarity AS ENUM ('common', 'uncommon', 'rare', 'epic', 'legendary');
CREATE TYPE book_status AS ENUM ('draft', 'published', 'archived');

-- Profiles table
CREATE TABLE IF NOT EXISTS profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text UNIQUE NOT NULL,
  display_name text,
  role user_role NOT NULL DEFAULT 'explorer',
  avatar_url text,
  bio text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Books table
CREATE TABLE IF NOT EXISTS books (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title text NOT NULL,
  author_name text NOT NULL,
  author_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  description text,
  cover_image_url text,
  book_type book_type NOT NULL,
  difficulty difficulty_level DEFAULT 'medium',
  status book_status DEFAULT 'draft',
  total_chapters integer DEFAULT 0,
  estimated_duration integer, -- in minutes
  tags text[],
  language text DEFAULT 'en',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Chapters table
CREATE TABLE IF NOT EXISTS chapters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id uuid REFERENCES books(id) ON DELETE CASCADE,
  chapter_number integer NOT NULL,
  title text NOT NULL,
  content text NOT NULL,
  summary text,
  duration integer, -- in minutes
  ai_generated_content jsonb, -- Store AI-generated lessons, quizzes, etc.
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(book_id, chapter_number)
);

-- User progress table
CREATE TABLE IF NOT EXISTS user_progress (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  book_id uuid REFERENCES books(id) ON DELETE CASCADE,
  current_chapter integer DEFAULT 1,
  progress_percentage integer DEFAULT 0,
  time_spent integer DEFAULT 0, -- in minutes
  last_read_at timestamptz DEFAULT now(),
  completed_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, book_id)
);

-- Quizzes table
CREATE TABLE IF NOT EXISTS quizzes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id uuid REFERENCES chapters(id) ON DELETE CASCADE,
  title text NOT NULL,
  questions jsonb NOT NULL, -- Array of question objects
  difficulty difficulty_level DEFAULT 'medium',
  created_at timestamptz DEFAULT now()
);

-- Quiz attempts table
CREATE TABLE IF NOT EXISTS quiz_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  quiz_id uuid REFERENCES quizzes(id) ON DELETE CASCADE,
  answers jsonb NOT NULL, -- User's answers
  score integer NOT NULL,
  completed_at timestamptz DEFAULT now(),
  time_taken integer -- in seconds
);

-- Badges table
CREATE TABLE IF NOT EXISTS badges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text UNIQUE NOT NULL,
  description text NOT NULL,
  image_url text,
  criteria text NOT NULL,
  rarity badge_rarity DEFAULT 'common',
  points integer DEFAULT 0,
  created_at timestamptz DEFAULT now()
);

-- User badges table
CREATE TABLE IF NOT EXISTS user_badges (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  badge_id uuid REFERENCES badges(id) ON DELETE CASCADE,
  earned_at timestamptz DEFAULT now(),
  blockchain_asset_id bigint,
  transaction_id text,
  UNIQUE(user_id, badge_id)
);

-- NFT collectibles table
CREATE TABLE IF NOT EXISTS nft_collectibles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text NOT NULL,
  image_url text,
  animation_url text,
  story_moment text NOT NULL,
  rarity badge_rarity DEFAULT 'common',
  book_id uuid REFERENCES books(id) ON DELETE CASCADE,
  chapter_id uuid REFERENCES chapters(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now()
);

-- User collectibles table
CREATE TABLE IF NOT EXISTS user_collectibles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  collectible_id uuid REFERENCES nft_collectibles(id) ON DELETE CASCADE,
  earned_at timestamptz DEFAULT now(),
  blockchain_asset_id bigint,
  transaction_id text,
  UNIQUE(user_id, collectible_id)
);

-- Story choices table (for entertainment mode)
CREATE TABLE IF NOT EXISTS story_choices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id uuid REFERENCES chapters(id) ON DELETE CASCADE,
  choice_text text NOT NULL,
  consequence text NOT NULL,
  next_chapter_id uuid REFERENCES chapters(id),
  choice_order integer NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- User story progress table
CREATE TABLE IF NOT EXISTS user_story_progress (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES profiles(id) ON DELETE CASCADE,
  book_id uuid REFERENCES books(id) ON DELETE CASCADE,
  current_branch text NOT NULL,
  choices_made jsonb DEFAULT '[]',
  story_state jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, book_id)
);

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quiz_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_badges ENABLE ROW LEVEL SECURITY;
ALTER TABLE nft_collectibles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_collectibles ENABLE ROW LEVEL SECURITY;
ALTER TABLE story_choices ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_story_progress ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can read own profile"
  ON profiles
  FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON profiles
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

-- Books policies
CREATE POLICY "Anyone can read published books"
  ON books
  FOR SELECT
  TO authenticated
  USING (status = 'published');

CREATE POLICY "Authors can read own books"
  ON books
  FOR SELECT
  TO authenticated
  USING (author_id = auth.uid());

CREATE POLICY "Authors can create books"
  ON books
  FOR INSERT
  TO authenticated
  WITH CHECK (author_id = auth.uid());

CREATE POLICY "Authors can update own books"
  ON books
  FOR UPDATE
  TO authenticated
  USING (author_id = auth.uid());

-- Chapters policies
CREATE POLICY "Users can read chapters of accessible books"
  ON chapters
  FOR SELECT
  TO authenticated
  USING (
    book_id IN (
      SELECT id FROM books 
      WHERE status = 'published' OR author_id = auth.uid()
    )
  );

CREATE POLICY "Authors can manage chapters of own books"
  ON chapters
  FOR ALL
  TO authenticated
  USING (
    book_id IN (
      SELECT id FROM books WHERE author_id = auth.uid()
    )
  );

-- User progress policies
CREATE POLICY "Users can read own progress"
  ON user_progress
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can manage own progress"
  ON user_progress
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid());

-- Quiz policies
CREATE POLICY "Users can read quizzes for accessible chapters"
  ON quizzes
  FOR SELECT
  TO authenticated
  USING (
    chapter_id IN (
      SELECT c.id FROM chapters c
      JOIN books b ON c.book_id = b.id
      WHERE b.status = 'published' OR b.author_id = auth.uid()
    )
  );

-- Quiz attempts policies
CREATE POLICY "Users can read own quiz attempts"
  ON quiz_attempts
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "Users can create own quiz attempts"
  ON quiz_attempts
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Badges policies
CREATE POLICY "Anyone can read badges"
  ON badges
  FOR SELECT
  TO authenticated;

-- User badges policies
CREATE POLICY "Users can read own badges"
  ON user_badges
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "System can award badges"
  ON user_badges
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- NFT collectibles policies
CREATE POLICY "Anyone can read collectibles"
  ON nft_collectibles
  FOR SELECT
  TO authenticated;

-- User collectibles policies
CREATE POLICY "Users can read own collectibles"
  ON user_collectibles
  FOR SELECT
  TO authenticated
  USING (user_id = auth.uid());

CREATE POLICY "System can award collectibles"
  ON user_collectibles
  FOR INSERT
  TO authenticated
  WITH CHECK (user_id = auth.uid());

-- Story choices policies
CREATE POLICY "Users can read story choices for accessible chapters"
  ON story_choices
  FOR SELECT
  TO authenticated
  USING (
    chapter_id IN (
      SELECT c.id FROM chapters c
      JOIN books b ON c.book_id = b.id
      WHERE b.status = 'published' OR b.author_id = auth.uid()
    )
  );

-- User story progress policies
CREATE POLICY "Users can manage own story progress"
  ON user_story_progress
  FOR ALL
  TO authenticated
  USING (user_id = auth.uid());

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_books_author_id ON books(author_id);
CREATE INDEX IF NOT EXISTS idx_books_type_status ON books(book_type, status);
CREATE INDEX IF NOT EXISTS idx_chapters_book_id ON chapters(book_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_user_id ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_book_id ON user_progress(book_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_user_id ON quiz_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_badges_user_id ON user_badges(user_id);
CREATE INDEX IF NOT EXISTS idx_user_collectibles_user_id ON user_collectibles(user_id);