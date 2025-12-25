import asyncio
import httpx
import sys
import json
import jwt

# Configuration
API_URL = "http://localhost:8001"
API_V1_STR = "/api/v1"
BASE_URL = f"{API_URL}{API_V1_STR}"

# Test Credentials (ensure these exist or use registration)
TEST_EMAIL = "test_creator@example.com"
TEST_PASSWORD = "password123"


async def check_health():
    print(f"Checking health at {API_URL}/health...")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}/health")
            if response.status_code == 200:
                print("✅ Health Check Passed")
                print(json.dumps(response.json(), indent=2))
                return True
            else:
                print(f"❌ Health Check Failed: {response.status_code}")
                print(response.text)
                return False
        except Exception as e:
            print(f"❌ Health Check Error: {e}")
            return False


async def test_auth():
    print(f"\nTesting Auth at {BASE_URL}/auth/login...")
    async with httpx.AsyncClient() as client:
        try:
            # 1. Register (idempotent-ish)
            register_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD,
                "display_name": "Test Creator",
                "full_name": "Test Creator",
                "role": "creator",  # Requesting creator role
            }
            print(f"Attempting registration for {TEST_EMAIL}...")
            reg_response = await client.post(
                f"{BASE_URL}/auth/register", json=register_data
            )

            if reg_response.status_code == 201:
                print("✅ Registration Successful")
            elif (
                reg_response.status_code == 400
                and "already exists" in reg_response.text
            ):
                print("ℹ️ User already exists, proceeding to login")
            else:
                print(f"⚠️ Registration unexpected status: {reg_response.status_code}")
                print(reg_response.text)

            # 2. Login
            login_data = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
            print(f"Attempting login for {TEST_EMAIL}...")
            login_response = await client.post(
                f"{BASE_URL}/auth/login", json=login_data
            )

            if login_response.status_code == 200:
                print("✅ Login Successful")
                data = login_response.json()
                user = data.get("user")
                print(f"User Role: {user.get('roles')}")

                # Check cookies for tokens
                cookies = login_response.cookies
                access_token = cookies.get("access_token")

                if access_token:
                    print("✅ Access Token Cookie Found")
                    # Decode token to verify claims (without verification for simplicity here)
                    decoded = jwt.decode(
                        access_token, options={"verify_signature": False}
                    )
                    print(f"Token Claims: {decoded}")
                    return access_token
                else:
                    print("❌ No Access Token Cookie found")
                    return None
            else:
                print(f"❌ Login Failed: {login_response.status_code}")
                print(login_response.text)
                return None

        except Exception as e:
            print(f"❌ Auth Test Error: {e}")
            return None


async def test_protected_endpoint(access_token):
    print(f"\nTesting Protected Endpoint {BASE_URL}/users/me...")
    if not access_token:
        print("❌ Skipping: No access token")
        return

    async with httpx.AsyncClient() as client:
        # Set cookie
        client.cookies.set("access_token", access_token)

        try:
            response = await client.get(f"{BASE_URL}/users/me")
            if response.status_code == 200:
                print("✅ Protected Endpoint Access Successful")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"❌ Protected Endpoint Failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Protected Endpoint Error: {e}")


async def main():
    if await check_health():
        token = await test_auth()
        if token:
            await test_protected_endpoint(token)


if __name__ == "__main__":
    asyncio.run(main())
