/*
  # Seed Initial Data for Litink

  1. Create default badges
  2. Create sample books and chapters
  3. Create sample NFT collectibles
*/

-- Insert default badges
INSERT INTO badges (name, description, image_url, criteria, rarity, points) VALUES
('First Steps', 'Complete your first lesson', 'https://images.pexels.com/photos/1029141/pexels-photo-1029141.jpeg?auto=compress&cs=tinysrgb&w=200', 'Complete any chapter', 'common', 10),
('Bookworm', 'Read 5 books', 'https://images.pexels.com/photos/159711/books-bookstore-book-reading-159711.jpeg?auto=compress&cs=tinysrgb&w=200', 'Complete 5 different books', 'uncommon', 50),
('Quiz Master', 'Score 90% or higher on 10 quizzes', 'https://images.pexels.com/photos/5428836/pexels-photo-5428836.jpeg?auto=compress&cs=tinysrgb&w=200', 'Achieve 90%+ score on 10 quizzes', 'rare', 100),
('AI Explorer', 'Use all AI features', 'https://images.pexels.com/photos/8386434/pexels-photo-8386434.jpeg?auto=compress&cs=tinysrgb&w=200', 'Use quiz, voice, and video features', 'rare', 75),
('Story Master', 'Complete 10 interactive stories', 'https://images.pexels.com/photos/1029621/pexels-photo-1029621.jpeg?auto=compress&cs=tinysrgb&w=200', 'Complete 10 entertainment mode books', 'epic', 150),
('Perfect Score', 'Achieve 100% on any quiz', 'https://images.pexels.com/photos/5428836/pexels-photo-5428836.jpeg?auto=compress&cs=tinysrgb&w=200', 'Score 100% on any quiz', 'uncommon', 25),
('Speed Reader', 'Complete 5 books in one week', 'https://images.pexels.com/photos/159711/books-bookstore-book-reading-159711.jpeg?auto=compress&cs=tinysrgb&w=200', 'Complete 5 books within 7 days', 'epic', 200),
('Knowledge Seeker', 'Earn perfect scores on 20 quizzes', 'https://images.pexels.com/photos/5428836/pexels-photo-5428836.jpeg?auto=compress&cs=tinysrgb&w=200', 'Score 100% on 20 different quizzes', 'legendary', 500);

-- Note: Sample books and chapters will be created through the application
-- when authors upload content, as they require user authentication

-- Add new columns for book processing status tracking
ALTER TABLE books 
ADD COLUMN IF NOT EXISTS error_message TEXT,
ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_steps INTEGER DEFAULT 4,
ADD COLUMN IF NOT EXISTS progress_message TEXT;