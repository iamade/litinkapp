DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type t
    JOIN pg_enum e ON t.oid = e.enumtypid
    WHERE t.typname = 'user_role' AND e.enumlabel = 'superadmin') THEN
    ALTER TYPE user_role ADD VALUE 'superadmin';
  END IF;
END$$;

-- (Optional) Create the superadmin profile if it doesn't exist
INSERT INTO profiles (id, email, display_name, role)
SELECT
  gen_random_uuid(),
  'support@litinkai.com',
  'LitinkAI Super Admin',
  'superadmin'
WHERE NOT EXISTS (
  SELECT 1 FROM profiles WHERE email = 'support@litinkai.com'
); 