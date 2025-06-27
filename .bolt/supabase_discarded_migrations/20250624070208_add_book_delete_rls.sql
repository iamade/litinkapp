-- Enable RLS for the books table if not already enabled
ALTER TABLE public.books ENABLE ROW LEVEL SECURITY;

-- Drop existing delete policy if it exists, to prevent errors on re-run
DROP POLICY IF EXISTS "Users can delete their own book records" ON public.books;

-- Create the policy that allows users to delete their own book records
CREATE POLICY "Users can delete their own book records"
ON public.books
FOR DELETE
TO authenticated
USING (auth.uid() = author_id); 