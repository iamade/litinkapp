-- Step 1: Add columns with defaults
ALTER TABLE profiles
ADD COLUMN IF NOT EXISTS first_name VARCHAR(30),
ADD COLUMN IF NOT EXISTS middle_name VARCHAR(30),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(30),
ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE;

-- Step 2: Populate existing records from display_name
UPDATE profiles
SET 
  first_name = COALESCE(SPLIT_PART(display_name, ' ', 1), 'Unknown'),
  last_name = COALESCE(SPLIT_PART(display_name, ' ', -1), 'User')
WHERE first_name IS NULL OR last_name IS NULL;

-- Step 3: Make columns NOT NULL after data is populated
ALTER TABLE profiles
ALTER COLUMN first_name SET NOT NULL,
ALTER COLUMN last_name SET NOT NULL;

-- Step 4: Force PostgREST to reload schema
NOTIFY pgrst, 'reload schema';
