-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table for RAG functionality
CREATE TABLE IF NOT EXISTS chapter_embeddings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id uuid REFERENCES chapters(id) ON DELETE CASCADE,
  book_id uuid REFERENCES books(id) ON DELETE CASCADE,
  content_chunk text NOT NULL,
  embedding vector(1536), -- OpenAI embeddings are 1536 dimensions
  chunk_index integer NOT NULL,
  chunk_size integer NOT NULL,
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(chapter_id, chunk_index)
);

-- Create embeddings table for book-level content
CREATE TABLE IF NOT EXISTS book_embeddings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  book_id uuid REFERENCES books(id) ON DELETE CASCADE,
  content_chunk text NOT NULL,
  embedding vector(1536),
  chunk_index integer NOT NULL,
  chunk_size integer NOT NULL,
  chunk_type text NOT NULL, -- 'title', 'description', 'content', 'summary'
  metadata jsonb DEFAULT '{}',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(book_id, chunk_type, chunk_index)
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS idx_chapter_embeddings_embedding 
ON chapter_embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_book_embeddings_embedding 
ON book_embeddings USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_chapter_embeddings_chapter_id ON chapter_embeddings(chapter_id);
CREATE INDEX IF NOT EXISTS idx_chapter_embeddings_book_id ON chapter_embeddings(book_id);
CREATE INDEX IF NOT EXISTS idx_book_embeddings_book_id ON book_embeddings(book_id);

-- Enable RLS on embeddings tables
ALTER TABLE chapter_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_embeddings ENABLE ROW LEVEL SECURITY;

-- RLS policies for chapter embeddings (user-facing: READY, author upload: PUBLISHED)
CREATE POLICY "Users can read embeddings for accessible chapters"
  ON chapter_embeddings
  FOR SELECT
  TO authenticated
  USING (
    chapter_id IN (
      SELECT c.id FROM chapters c
      JOIN books b ON c.book_id = b.id
      WHERE b.status = 'READY' OR b.user_id = auth.uid()
    )
  );

CREATE POLICY "Authors can manage embeddings for own chapters"
  ON chapter_embeddings
  FOR ALL
  TO authenticated
  USING (
    book_id IN (
      SELECT id FROM books WHERE user_id = auth.uid()
    )
  );

-- RLS policies for book embeddings (user-facing: READY, author upload: PUBLISHED)
CREATE POLICY "Users can read embeddings for accessible books"
  ON book_embeddings
  FOR SELECT
  TO authenticated
  USING (
    book_id IN (
      SELECT id FROM books 
      WHERE status = 'READY' OR user_id = auth.uid()
    )
  );

CREATE POLICY "Authors can manage embeddings for own books"
  ON book_embeddings
  FOR ALL
  TO authenticated
  USING (
    book_id IN (
      SELECT id FROM books WHERE user_id = auth.uid()
    )
  );

-- Add function for similarity search
CREATE OR REPLACE FUNCTION match_chapter_embeddings(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  chapter_id uuid,
  book_id uuid,
  content_chunk text,
  chunk_index integer,
  similarity float
)
LANGUAGE plpgsql
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

-- Add function for book-level similarity search
CREATE OR REPLACE FUNCTION match_book_embeddings(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  book_id uuid,
  content_chunk text,
  chunk_type text,
  chunk_index integer,
  similarity float
)
LANGUAGE plpgsql
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