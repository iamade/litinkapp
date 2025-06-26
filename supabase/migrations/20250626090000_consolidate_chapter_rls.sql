-- This migration replaces previous chapter RLS policies with a consolidated and corrected version.

-- Drop old policies to ensure a clean slate and avoid conflicts.
DROP POLICY IF EXISTS "Allow chapter access based on book ownership or ready status" ON public.chapters;
DROP POLICY IF EXISTS "Authors can manage chapters of own books" ON public.chapters;
DROP POLICY IF EXISTS "Allow chapter access based on book ownership or published status" ON public.chapters;


-- Consolidated RLS Policy for Chapters
CREATE POLICY "Users can manage their own book chapters and view ready chapters"
ON public.chapters
FOR ALL
TO authenticated
USING (
  -- The user is the owner of the book
  (EXISTS (SELECT 1 FROM books WHERE id = chapters.book_id AND user_id = auth.uid()))
  OR
  -- OR the book is in 'READY' state (for SELECT only)
  (EXISTS (SELECT 1 FROM books WHERE id = chapters.book_id AND status = 'READY'))
)
WITH CHECK (
  -- Users can only insert/update chapters for books they own.
  (EXISTS (SELECT 1 FROM books WHERE id = chapters.book_id AND user_id = auth.uid()))
); 