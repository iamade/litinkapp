/*
  # Fix SECURITY DEFINER Functions Search Path Vulnerability

  ## Problem
  Supabase Security Advisor reports: "Function has a role mutable search_path"
  Functions using SECURITY DEFINER without SET search_path = '' are vulnerable to 
  search_path manipulation attacks where malicious users could create objects in 
  their schema to hijack function calls.

  ## Solution
  Add SET search_path = '' to all SECURITY DEFINER functions and use fully qualified
  table names (schema.table) in all function bodies.

  ## Functions Fixed
  1. add_role_to_user - Add/remove user roles
  2. remove_role_from_user - Remove user roles
  3. can_request_verification_email - Rate limiting for verification emails
  4. update_verification_token_sent - Update verification timestamp
  5. is_superadmin - Check if user is superadmin
  6. set_email_verified_at - Trigger function for email verification

  ## Security
  - Empty search_path prevents schema manipulation attacks
  - Fully qualified names ensure correct table references
  - SECURITY DEFINER still grants elevated privileges as needed
*/

-- Fix: add_role_to_user function
CREATE OR REPLACE FUNCTION public.add_role_to_user(user_id uuid, new_role text)
RETURNS void 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  UPDATE public.profiles
  SET roles = array_append(roles, new_role),
      updated_at = now()
  WHERE id = user_id
    AND NOT (new_role = ANY(roles));
END;
$$;

COMMENT ON FUNCTION public.add_role_to_user(uuid, text) IS 'Add a new role to user account (idempotent) - SECURITY DEFINER with empty search_path';

-- Fix: remove_role_from_user function
CREATE OR REPLACE FUNCTION public.remove_role_from_user(user_id uuid, role_to_remove text)
RETURNS void 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  current_roles text[];
BEGIN
  SELECT roles INTO current_roles FROM public.profiles WHERE id = user_id;
  
  -- Ensure at least one role remains
  IF array_length(current_roles, 1) <= 1 THEN
    RAISE EXCEPTION 'Cannot remove last role from user';
  END IF;
  
  UPDATE public.profiles
  SET roles = array_remove(roles, role_to_remove),
      updated_at = now()
  WHERE id = user_id;
END;
$$;

COMMENT ON FUNCTION public.remove_role_from_user(uuid, text) IS 'Remove a role from user account (prevents removing last role) - SECURITY DEFINER with empty search_path';

-- Fix: can_request_verification_email function
CREATE OR REPLACE FUNCTION public.can_request_verification_email(user_id uuid)
RETURNS boolean 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  last_sent timestamptz;
BEGIN
  SELECT verification_token_sent_at INTO last_sent
  FROM public.profiles
  WHERE id = user_id;
  
  -- Allow if never sent or if more than 5 minutes have passed
  RETURN last_sent IS NULL OR (now() - last_sent) > interval '5 minutes';
END;
$$;

COMMENT ON FUNCTION public.can_request_verification_email(uuid) IS 'Check if user can request a new verification email (5 minute cooldown) - SECURITY DEFINER with empty search_path';

-- Fix: update_verification_token_sent function
CREATE OR REPLACE FUNCTION public.update_verification_token_sent(user_id uuid)
RETURNS void 
LANGUAGE plpgsql 
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  UPDATE public.profiles
  SET verification_token_sent_at = now()
  WHERE id = user_id;
END;
$$;

COMMENT ON FUNCTION public.update_verification_token_sent(uuid) IS 'Update the timestamp of when verification email was sent - SECURITY DEFINER with empty search_path';

-- Fix: is_superadmin function
CREATE OR REPLACE FUNCTION public.is_superadmin()
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid()
    AND (role = 'superadmin' OR email = 'support@litinkai.com')
  );
END;
$$;

COMMENT ON FUNCTION public.is_superadmin() IS 'Check if current user is superadmin - SECURITY DEFINER with empty search_path';

-- Fix: set_email_verified_at trigger function
CREATE OR REPLACE FUNCTION public.set_email_verified_at()
RETURNS TRIGGER 
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  IF NEW.email_verified = true AND OLD.email_verified = false THEN
    NEW.email_verified_at = now();
  ELSIF NEW.email_verified = false THEN
    NEW.email_verified_at = NULL;
  END IF;
  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION public.set_email_verified_at() IS 'Trigger function to auto-set email_verified_at timestamp - with empty search_path for security';

-- Recreate the trigger to use the updated function
DROP TRIGGER IF EXISTS trigger_set_email_verified_at ON public.profiles;
CREATE TRIGGER trigger_set_email_verified_at
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW
  EXECUTE FUNCTION public.set_email_verified_at();
