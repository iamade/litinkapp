-- Step 1: Drop the incomplete function and trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;

-- Step 2: Create the COMPLETE function with all required parts
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
SECURITY DEFINER
SET search_path = public
LANGUAGE plpgsql
AS $$
BEGIN
  INSERT INTO public.profiles (
    id,
    email,
    display_name,
    roles,
    email_verified,
    account_status,
    is_active,
    failed_login_attempts,
    security_question,
    security_answer,
    first_name,
    last_name,
    is_superuser,
    created_at,
    updated_at
  )
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
    ARRAY['explorer']::TEXT[],
    FALSE,
    'pending',
    FALSE,
    0,
    'mother_maiden_name',
    '',
    COALESCE(NEW.raw_user_meta_data->>'first_name', ''),
    COALESCE(NEW.raw_user_meta_data->>'last_name', ''),
    FALSE,
    NOW(),
    NOW()
  )
  ON CONFLICT ON CONSTRAINT profiles_pkey DO UPDATE SET
    email = EXCLUDED.email,
    first_name = COALESCE(EXCLUDED.first_name, public.profiles.first_name),
    last_name = COALESCE(EXCLUDED.last_name, public.profiles.last_name),
    updated_at = NOW();

  RETURN NEW;
END;
$$;

-- Step 3: Recreate the trigger
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- Step 4: Verify function was created properly
SELECT 
  p.proname AS function_name,
  pg_get_function_arguments(p.oid) AS arguments,
  CASE 
    WHEN LENGTH(pg_get_functiondef(p.oid)) > 100 THEN 'Function created successfully (length: ' || LENGTH(pg_get_functiondef(p.oid)) || ' chars)'
    ELSE 'WARNING: Function may be incomplete'
  END AS status
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
  AND p.proname = 'handle_new_user';

-- Step 5: Verify trigger exists
SELECT 
  t.tgname AS trigger_name,
  p.proname AS function_name,
  CASE t.tgenabled
    WHEN 'O' THEN 'Enabled'
    ELSE 'Disabled'
  END AS status
FROM pg_trigger t
JOIN pg_proc p ON t.tgfoid = p.oid
WHERE t.tgrelid = 'auth.users'::regclass
  AND t.tgname = 'on_auth_user_created';
