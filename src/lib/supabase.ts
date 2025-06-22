import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Database types
export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          email: string;
          display_name: string | null;
          role: 'author' | 'explorer';
          avatar_url: string | null;
          bio: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          email: string;
          display_name?: string | null;
          role?: 'author' | 'explorer';
          avatar_url?: string | null;
          bio?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          email?: string;
          display_name?: string | null;
          role?: 'author' | 'explorer';
          avatar_url?: string | null;
          bio?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      books: {
        Row: {
          id: string;
          title: string;
          author_name: string;
          author_id: string | null;
          description: string | null;
          cover_image_url: string | null;
          book_type: 'learning' | 'entertainment';
          difficulty: 'easy' | 'medium' | 'hard' | null;
          status: 'draft' | 'published' | 'archived';
          total_chapters: number | null;
          estimated_duration: number | null;
          tags: string[] | null;
          language: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          title: string;
          author_name: string;
          author_id?: string | null;
          description?: string | null;
          cover_image_url?: string | null;
          book_type: 'learning' | 'entertainment';
          difficulty?: 'easy' | 'medium' | 'hard' | null;
          status?: 'draft' | 'published' | 'archived';
          total_chapters?: number | null;
          estimated_duration?: number | null;
          tags?: string[] | null;
          language?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          title?: string;
          author_name?: string;
          author_id?: string | null;
          description?: string | null;
          cover_image_url?: string | null;
          book_type?: 'learning' | 'entertainment';
          difficulty?: 'easy' | 'medium' | 'hard' | null;
          status?: 'draft' | 'published' | 'archived';
          total_chapters?: number | null;
          estimated_duration?: number | null;
          tags?: string[] | null;
          language?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      chapters: {
        Row: {
          id: string;
          book_id: string;
          chapter_number: number;
          title: string;
          content: string;
          summary: string | null;
          duration: number | null;
          ai_generated_content: any | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          book_id: string;
          chapter_number: number;
          title: string;
          content: string;
          summary?: string | null;
          duration?: number | null;
          ai_generated_content?: any | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          book_id?: string;
          chapter_number?: number;
          title?: string;
          content?: string;
          summary?: string | null;
          duration?: number | null;
          ai_generated_content?: any | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      user_progress: {
        Row: {
          id: string;
          user_id: string;
          book_id: string;
          current_chapter: number | null;
          progress_percentage: number | null;
          time_spent: number | null;
          last_read_at: string | null;
          completed_at: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          book_id: string;
          current_chapter?: number | null;
          progress_percentage?: number | null;
          time_spent?: number | null;
          last_read_at?: string | null;
          completed_at?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          book_id?: string;
          current_chapter?: number | null;
          progress_percentage?: number | null;
          time_spent?: number | null;
          last_read_at?: string | null;
          completed_at?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      badges: {
        Row: {
          id: string;
          name: string;
          description: string;
          image_url: string | null;
          criteria: string;
          rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
          points: number | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          description: string;
          image_url?: string | null;
          criteria: string;
          rarity?: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
          points?: number | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          description?: string;
          image_url?: string | null;
          criteria?: string;
          rarity?: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';
          points?: number | null;
          created_at?: string;
        };
      };
      user_badges: {
        Row: {
          id: string;
          user_id: string;
          badge_id: string;
          earned_at: string;
          blockchain_asset_id: number | null;
          transaction_id: string | null;
        };
        Insert: {
          id?: string;
          user_id: string;
          badge_id: string;
          earned_at?: string;
          blockchain_asset_id?: number | null;
          transaction_id?: string | null;
        };
        Update: {
          id?: string;
          user_id?: string;
          badge_id?: string;
          earned_at?: string;
          blockchain_asset_id?: number | null;
          transaction_id?: string | null;
        };
      };
    };
  };
}