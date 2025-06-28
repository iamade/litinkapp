-- Migration: Add source and klingai_video_url fields to videos table
ALTER TABLE videos ADD COLUMN source text;
ALTER TABLE videos ADD COLUMN klingai_video_url text; 