# Quick Start: Setting Up Your Superadmin Account

## What Was Fixed

✅ Database migration complete - removed old `role` column, using `roles` array
✅ All authentication code updated to use `roles` array
✅ Superadmin profile created in database
✅ 6 new API endpoints for user/role management
✅ Frontend updated to check roles correctly

## What You Need To Do Now

### Step 1: Create the Auth User (Required)

The superadmin **profile** exists in your database, but you need to create the corresponding **auth user** in Supabase.

Go to your **Supabase Dashboard**:
1. Click on **Authentication** in the left sidebar
2. Click on **Users**
3. Click **Add user** button
4. Fill in:
   - **Email**: `support@litinkai.com`
   - **Password**: `LitinkAdmin2024!` (or create your own secure password)
   - **Auto Confirm Email**: Toggle ON (or check "Email Confirmed")
5. Click **Create user**

### Step 2: Test Login

1. Go to your app's login page
2. Enter:
   - Email: `support@litinkai.com`
   - Password: `LitinkAdmin2024!` (or your password)
3. Click Login

**Expected Result**: You should be logged in and redirected to the dashboard. The navbar should show an "Admin" link.

### Step 3: Access Admin Dashboard

1. Click the **Admin** link in the navbar (or navigate to `/admin`)
2. You should see the admin dashboard with access to:
   - Cost tracking
   - Metrics
   - User verification management
   - User role management (NEW!)

### Step 4: Test Adding Roles to Users

Register a new test user first:
1. Logout
2. Go to registration page
3. Register as `testuser@example.com` with password `TestPass123!`
4. Note: You'll need to verify the email (check the admin panel to manually verify)

Then as superadmin:
1. Login as `support@litinkai.com`
2. Use the admin API to add author role:

```bash
POST http://localhost:8000/api/v1/admin/users/roles/add
Authorization: Bearer YOUR_SUPERADMIN_TOKEN
Content-Type: application/json

{
  "user_id": "USER_UUID_HERE",
  "role": "author"
}
```

Or use the browser console:
```javascript
// Get the user ID
const response = await fetch('/api/v1/admin/users/list?limit=10', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
});
const data = await response.json();
console.log('Users:', data.users);

// Add author role to a user
const addRoleResponse = await fetch('/api/v1/admin/users/roles/add', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    user_id: 'USER_UUID_HERE',
    role: 'author'
  })
});
const result = await addRoleResponse.json();
console.log('Result:', result);
```

## Available Admin Endpoints

All require superadmin authentication:

### User Management
- `GET /api/v1/admin/users/list` - List all users (with search, pagination, role filter)
- `GET /api/v1/admin/users/{user_id}` - Get user details
- `GET /api/v1/admin/users/{user_id}/roles` - Get user's roles

### Role Management
- `POST /api/v1/admin/users/roles/add` - Add role to user
  ```json
  { "user_id": "uuid", "role": "explorer|author|admin|superadmin" }
  ```
- `POST /api/v1/admin/users/roles/remove` - Remove role from user
  ```json
  { "user_id": "uuid", "role": "explorer|author|admin|superadmin" }
  ```
- `GET /api/v1/admin/roles/available` - List available roles

## Role System Overview

### Available Roles

1. **explorer** (default) - Basic user, can browse and consume content
2. **author** - Can create and publish content
3. **admin** - Can moderate content and manage users
4. **superadmin** - Full system access, can manage all roles

### Key Features

- **Multi-role Support**: Users can have multiple roles simultaneously
- **Role Validation**: Database constraint ensures only valid roles
- **Protected Operations**:
  - Only primary superadmin can grant superadmin role
  - Cannot remove superadmin from primary superadmin account
  - Cannot remove last role from any user

## Troubleshooting

### "Authentication failed" when logging in as superadmin

**Check 1**: Does the auth user exist?
- Go to Supabase Dashboard > Authentication > Users
- Look for `support@litinkai.com`
- If not found, create it (see Step 1 above)

**Check 2**: Is the email confirmed?
- In Supabase Dashboard > Authentication > Users
- Find `support@litinkai.com`
- Check "Email Confirmed" column
- If not confirmed, click the user and toggle "Email Confirmed" ON

**Check 3**: Does the profile have the superadmin role?
```sql
-- Run in Supabase SQL Editor
SELECT id, email, roles, email_verified
FROM profiles
WHERE email = 'support@litinkai.com';
```
Expected result: `roles` should be `["superadmin", "admin", "author", "explorer"]`

If roles don't include superadmin, run:
```sql
UPDATE profiles
SET roles = array_append(roles, 'superadmin')
WHERE email = 'support@litinkai.com'
AND NOT ('superadmin' = ANY(roles));
```

### User registration fails with "Database error"

The registration endpoint expects `roles` as an array in the request body. Check that:

1. The frontend is sending `roles` as an array: `["explorer"]`
2. The old `role` column has been dropped from the database
3. Run this to verify:
```sql
-- Check if role column exists (should return 0)
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_name = 'profiles'
AND column_name = 'role';

-- Check if roles column exists (should return 1)
SELECT COUNT(*)
FROM information_schema.columns
WHERE table_name = 'profiles'
AND column_name = 'roles';
```

### "Cannot add role" errors

Make sure you're authenticated as superadmin and your token is valid:

```javascript
// Check your current user in browser console
const response = await fetch('/api/v1/auth/me', {
  headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
});
const user = await response.json();
console.log('Current user:', user);
console.log('Has superadmin role?', user.roles?.includes('superadmin'));
```

## Security Best Practices

1. **Change the default password** immediately after first login
2. **Enable MFA** if your Supabase project supports it
3. **Grant superadmin role sparingly** - only to trusted administrators
4. **Use admin role** for most administrative tasks instead of superadmin
5. **Monitor role changes** via the admin logs

## Next Steps

1. ✅ Create auth user for superadmin (Step 1)
2. ✅ Test login (Step 2)
3. ✅ Access admin dashboard (Step 3)
4. ✅ Test role management (Step 4)
5. 🔐 Change default password
6. 🎨 Build a UI for user management in the admin dashboard (optional)
7. 📊 Add audit logging for role changes (optional)

---

**Questions or Issues?**

Check the full documentation in `AUTHENTICATION_FIX_SUMMARY.md` for detailed technical information about all the changes made.
