"""
Test script to verify user registration fixes
Run this to test the registration endpoint after applying the fixes
"""
import os
import sys
import requests
import json
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEST_EMAIL = f"test_{datetime.now().timestamp()}@example.com"
TEST_PASSWORD = "SecureTestPass123!"
TEST_DISPLAY_NAME = "Test User"

def test_registration():
    """Test user registration endpoint"""
    print("=" * 60)
    print("Testing User Registration Fix")
    print("=" * 60)

    # Prepare registration data
    registration_data = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "display_name": TEST_DISPLAY_NAME,
        "roles": ["explorer"]
    }

    print(f"\n1. Testing registration endpoint...")
    print(f"   URL: {BACKEND_URL}/api/v1/auth/register")
    print(f"   Email: {TEST_EMAIL}")

    try:
        # Send registration request
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json=registration_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"\n2. Response Status: {response.status_code}")

        if response.status_code == 201:
            print("✅ SUCCESS! User registered successfully!")
            print("\nResponse Data:")
            print(json.dumps(response.json(), indent=2))

            # Verify response structure
            data = response.json()
            required_fields = ["id", "email", "display_name", "roles", "email_verified"]
            missing_fields = [f for f in required_fields if f not in data]

            if missing_fields:
                print(f"\n⚠️  WARNING: Missing fields in response: {missing_fields}")
            else:
                print("\n✅ All required fields present in response")

            print("\n3. Verification Status:")
            print(f"   Email Verified: {data.get('email_verified', 'N/A')}")
            print(f"   Roles: {data.get('roles', 'N/A')}")

            print("\n4. Next Steps:")
            print("   - Check your email for verification link")
            print("   - Verify email before attempting login")
            print("   - Try logging in after verification")

            return True

        elif response.status_code == 400:
            error_detail = response.json().get("detail", "Unknown error")
            print(f"❌ FAILED! Registration error: {error_detail}")

            if "Database error saving new user" in error_detail:
                print("\n🔍 Diagnosis:")
                print("   The 'Database error saving new user' error persists.")
                print("   Possible causes:")
                print("   1. Migrations not applied to Supabase database")
                print("   2. Service role key not configured correctly")
                print("   3. RLS policy not updated")
                print("\n   Check:")
                print("   - Supabase dashboard → Database → Migrations")
                print("   - Backend .env file has correct SUPABASE_SERVICE_ROLE_KEY")
                print("   - Run: supabase db push (if using local migrations)")

            return False

        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to backend")
        print(f"   Make sure backend is running at {BACKEND_URL}")
        print("   Start with: cd backend && uvicorn app.main:app --reload")
        return False

    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
        print("   Backend might be overloaded or not responding")
        return False

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        print("\nTraceback:")
        print(traceback.format_exc())
        return False

def check_database_policies():
    """Instructions to check database policies"""
    print("\n" + "=" * 60)
    print("Database Policy Verification")
    print("=" * 60)
    print("\nTo verify the RLS policies are correct, run this SQL in Supabase:")
    print("""
    SELECT policyname, cmd, qual, with_check
    FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'profiles' AND cmd = 'INSERT';
    """)
    print("\nExpected result:")
    print("  Policy: 'Users can insert own profile or service role can insert any'")
    print("  WITH CHECK: Contains 'auth.jwt()->>'role' = 'service_role'")

def check_security_definer_functions():
    """Instructions to check SECURITY DEFINER functions"""
    print("\n" + "=" * 60)
    print("Security Functions Verification")
    print("=" * 60)
    print("\nTo verify functions have search_path set, run this SQL:")
    print("""
    SELECT
      p.proname as function_name,
      CASE WHEN p.prosecdef THEN 'SECURITY DEFINER' ELSE 'SECURITY INVOKER' END as security,
      (SELECT setting FROM unnest(p.proconfig) setting WHERE setting LIKE 'search_path=%') as search_path
    FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'public'
      AND p.proname IN ('add_role_to_user', 'remove_role_from_user',
                        'can_request_verification_email', 'update_verification_token_sent',
                        'is_superadmin', 'set_email_verified_at')
    ORDER BY p.proname;
    """)
    print("\nAll functions should show: search_path=\"\"")

if __name__ == "__main__":
    print("\n")
    success = test_registration()

    if not success:
        print("\n" + "=" * 60)
        print("Troubleshooting Steps")
        print("=" * 60)
        check_database_policies()
        check_security_definer_functions()

        print("\n" + "=" * 60)
        print("Manual Testing")
        print("=" * 60)
        print("\nYou can also test manually with curl:")
        print(f"""
curl -X POST {BACKEND_URL}/api/v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "display_name": "Test User",
    "roles": ["explorer"]
  }}'
        """)

    sys.exit(0 if success else 1)
