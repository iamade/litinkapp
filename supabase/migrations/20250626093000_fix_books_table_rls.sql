-- This migration fixes the root cause of the chapter visibility issue
-- by creating a comprehensive RLS policy on the 'books' table.

-- Drop the old, insufficient policy.
DROP POLICY IF EXISTS "Anyone can read published books" ON public.books;

-- Create a new, comprehensive policy for the 'books' table.
CREATE POLICY "Users can manage own books and view ready books"
ON public.books
FOR ALL
TO authenticated
USING (
  -- The user is the owner of the book.
  (user_id = auth.uid())
  OR
  -- OR the book is in 'READY' state (for SELECT only).
  (status = 'READY')
)
WITH CHECK (
  -- Users can only insert/update books they own.
  (user_id = auth.uid())
); 