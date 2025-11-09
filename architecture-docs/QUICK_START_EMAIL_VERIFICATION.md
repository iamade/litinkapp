# Quick Start: Email Verification

## 🚀 Getting Started in 5 Minutes

### Step 1: Start Mailpit (Development)

```bash
cd backend
docker-compose up mailpit -d
```

Access Mailpit UI at: **http://localhost:8025**

### Step 2: Update Environment Variables

```bash
# backend/.env
MAIL_SERVICE=mailpit
MAILPIT_SMTP_HOST=localhost
MAILPIT_SMTP_PORT=1025
FRONTEND_URL=http://localhost:5173
```

### Step 3: Configure Supabase Dashboard

1. Go to **Authentication** → **Providers** → **Email**
2. ✅ Enable **"Confirm email"**
3. ✅ Disable **"Allow unverified email sign-ins"**
4. Add to **Redirect URLs**: `http://localhost:5173/auth/verify-email`

### Step 4: Test Registration

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "display_name": "Test User",
    "roles": ["explorer"]
  }'
```

### Step 5: Check Mailpit

1. Open http://localhost:8025
2. You'll see the verification email
3. Click the link to verify

### Step 6: Test Login

```bash
# Try to login (should work after verification)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!"
  }'
```

---

## 📧 What Changed

### Registration Fix

**Before**: ❌ Database error on registration
**After**: ✅ Successful registration with email verification

### Login Behavior

**Before**: Anyone could login without email verification
**After**: Must verify email to login

### Error Response

```json
{
  "detail": "Email not verified. Please check your email for the verification link."
}
```

---

## 🔧 Production Setup (Mailgun)

### 1. Get Mailgun Credentials

1. Sign up at https://www.mailgun.com
2. Add your domain
3. Verify DNS records
4. Get API key from dashboard

### 2. Update Production Environment

```bash
# Production .env
MAIL_SERVICE=mailgun
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=yourdomain.com
MAILGUN_SENDER_EMAIL=noreply@litinkai.com
FRONTEND_URL=https://www.litinkai.com
```

### 3. Update Supabase Redirect URL

Add to **Redirect URLs**: `https://www.litinkai.com/auth/verify-email`

---

## 🛠️ Admin Tools

### View Unverified Users

```bash
curl http://localhost:8000/api/v1/admin/users/unverified \
  -H "Authorization: Bearer <admin_token>"
```

### Manually Verify User

```bash
curl -X POST http://localhost:8000/api/v1/admin/users/verify-manually \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-uuid-here"}'
```

### Send Bulk Verification Emails

```bash
curl -X POST http://localhost:8000/api/v1/admin/users/send-verification-bulk \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"limit": 100}'
```

---

## 🐛 Troubleshooting

### "Database error saving new user"

✅ **FIXED** - This was the original issue. Registration now works correctly.

### Verification email not received

**Development**:
- Check Mailpit is running: `docker ps | grep mailpit`
- Check UI: http://localhost:8025

**Production**:
- Verify Mailgun API key is correct
- Check DNS records are configured
- Review Mailgun logs

### "Email not verified" on login

✅ This is expected! Users must verify their email before logging in.

**Solutions**:
1. Click verification link in email
2. Request new verification email
3. Admin can manually verify

### Can't resend verification email

⏱️ Rate limited to once every 5 minutes. Wait or ask admin to manually verify.

---

## 📚 Full Documentation

- **Setup Guide**: `EMAIL_VERIFICATION_SETUP.md`
- **Implementation Summary**: `../EMAIL_VERIFICATION_IMPLEMENTATION_SUMMARY.md`

---

## ✅ Verification Checklist

- [ ] Mailpit running on port 8025
- [ ] Environment variables configured
- [ ] Supabase email confirmation enabled
- [ ] Supabase redirect URLs added
- [ ] Test registration successful
- [ ] Verification email received in Mailpit
- [ ] Email verification link works
- [ ] Login works after verification
- [ ] Login blocked before verification

---

## 🎉 You're Done!

Your email verification system is now live! Users must verify their email addresses before they can log in.

**Need help?** Check the full documentation or contact support@litinkai.com
