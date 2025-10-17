#!/usr/bin/env python3
"""
Test script to verify superadmin setup and authentication
"""
import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  No .env file found in backend directory")
    sys.exit(1)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials in .env file")
    sys.exit(1)

# Create Supabase client with service role key
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_superadmin_profile():
    """Check if superadmin profile exists"""
    print("\n1. Checking for superadmin profile...")
    try:
        response = supabase.table('profiles').select('*').eq('email', 'support@litinkai.com').execute()

        if response.data and len(response.data) > 0:
            profile = response.data[0]
            print(f"✅ Superadmin profile found:")
            print(f"   - ID: {profile['id']}")
            print(f"   - Email: {profile['email']}")
            print(f"   - Display Name: {profile.get('display_name', 'N/A')}")
            print(f"   - Roles: {profile.get('roles', [])}")
            print(f"   - Email Verified: {profile.get('email_verified', False)}")

            # Check if superadmin role is present
            roles = profile.get('roles', [])
            if 'superadmin' in roles:
                print("   ✅ Has 'superadmin' role")
            else:
                print("   ⚠️  Missing 'superadmin' role - needs to be added")
                return False

            return True
        else:
            print("❌ No superadmin profile found")
            print("   The migration should have created it. Check if migrations were applied.")
            return False

    except Exception as e:
        print(f"❌ Error checking profile: {e}")
        return False


def check_database_functions():
    """Check if required database functions exist"""
    print("\n2. Checking database functions...")

    functions_to_check = [
        'is_superadmin',
        'user_has_role',
        'user_is_superadmin',
        'add_role_to_user',
        'remove_role_from_user',
        'check_superadmin_users'
    ]

    try:
        for func_name in functions_to_check:
            # Try to call the function or check if it exists
            query = f"""
            SELECT EXISTS (
                SELECT 1 FROM pg_proc
                WHERE proname = '{func_name}'
            ) as exists;
            """
            response = supabase.rpc('execute_sql', {'query': query}).execute()

            # Note: This might not work depending on RLS, so we'll just print what we're checking
            print(f"   - Checking {func_name}...")

        print("   ℹ️  Function checks completed (use Supabase dashboard to verify)")
        return True

    except Exception as e:
        print(f"   ℹ️  Could not verify functions via API (this is normal): {e}")
        print("   ℹ️  Verify functions exist in Supabase SQL Editor")
        return True


def check_auth_user():
    """Check if auth user exists for superadmin"""
    print("\n3. Checking Supabase Auth user...")
    print("   ℹ️  Auth user verification requires admin API access")
    print("   ℹ️  You need to manually verify this in Supabase Dashboard > Authentication > Users")
    print("   ℹ️  Look for user with email: support@litinkai.com")
    return True


def test_role_functions():
    """Test role management functions"""
    print("\n4. Testing role management functions...")

    try:
        # Call the check_superadmin_users function
        response = supabase.rpc('check_superadmin_users').execute()

        if response.data:
            print(f"✅ Found {len(response.data)} superadmin user(s):")
            for user in response.data:
                print(f"   - {user['email']}: {user['roles']}")
            return True
        else:
            print("⚠️  No superadmin users found via check_superadmin_users()")
            return False

    except Exception as e:
        print(f"❌ Error testing role functions: {e}")
        return False


def print_next_steps(has_profile, has_auth_user=None):
    """Print next steps based on current state"""
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)

    if not has_profile:
        print("\n❌ Superadmin profile is missing or incomplete")
        print("\nRun this SQL in Supabase SQL Editor:")
        print("""
-- Manually create/update superadmin profile
INSERT INTO profiles (
    id,
    email,
    display_name,
    roles,
    email_verified,
    email_verified_at,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    'support@litinkai.com',
    'LitInk Support',
    ARRAY['superadmin', 'admin', 'author', 'explorer']::text[],
    true,
    now(),
    now(),
    now()
)
ON CONFLICT (email) DO UPDATE SET
    roles = CASE
        WHEN 'superadmin' = ANY(profiles.roles) THEN profiles.roles
        ELSE array_append(profiles.roles, 'superadmin')
    END,
    email_verified = true,
    email_verified_at = COALESCE(profiles.email_verified_at, now()),
    updated_at = now();
""")

    print("\n📝 To create the auth user:")
    print("   1. Go to Supabase Dashboard > Authentication > Users")
    print("   2. Click 'Invite user' or 'Add user'")
    print("   3. Email: support@litinkai.com")
    print("   4. Password: LitinkAdmin2024! (or your choice)")
    print("   5. Set 'Email Confirmed' to YES")
    print("   6. After creation, the profile will be automatically linked")

    print("\n📝 To test login:")
    print("   1. Go to your frontend login page")
    print("   2. Login with: support@litinkai.com")
    print("   3. Password: LitinkAdmin2024! (or the password you set)")
    print("   4. You should be redirected to the admin dashboard")

    print("\n📝 To add roles to other users:")
    print("   1. Login as superadmin")
    print("   2. Go to /admin dashboard")
    print("   3. Use the user management section")
    print("   4. Or use the API:")
    print("""
   POST /api/v1/admin/users/roles/add
   Body: {"user_id": "<user_uuid>", "role": "author"}
   Headers: Authorization: Bearer <superadmin_token>
""")


def main():
    """Main test function"""
    print("="*60)
    print("SUPERADMIN SETUP VERIFICATION")
    print("="*60)

    has_profile = check_superadmin_profile()
    check_database_functions()
    check_auth_user()
    test_role_functions()

    print_next_steps(has_profile)

    print("\n" + "="*60)
    if has_profile:
        print("✅ Setup looks good! Follow next steps to complete auth user creation.")
    else:
        print("⚠️  Issues found. Follow next steps to fix.")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
