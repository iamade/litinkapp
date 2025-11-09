# Email Verification System Setup Guide

This guide will help you set up and configure the email verification system with Mailpit (development) and Mailgun (production).

## Overview

The system now requires all users to verify their email addresses before they can log in. This includes both new registrations and existing users.

### Email Service Providers

- **Development**: Mailpit (local SMTP testing tool)
- **Production**: Mailgun (transactional email service)

---

## 1. Supabase Dashboard Configuration

### Step 1: Enable Email Confirmation

1. Log in to your Supabase dashboard
2. Navigate to **Authentication** → **Providers** → **Email**
3. Enable **"Confirm email"** option
4. Set **"Secure email change"** to require verification for email updates
5. Disable **"Allow unverified email sign-ins"**

### Step 2: Configure Email Templates

1. Go to **Authentication** → **Email Templates**
2. Customize the following templates:
   - **Confirm signup**: Verification email sent to new users
   - **Magic Link**: (Optional) For passwordless login
   - **Change Email Address**: Sent when users update their email

### Step 3: Set Redirect URLs

1. In **Authentication** → **URL Configuration**
2. Add your frontend URL to **Site URL**: `https://www.litinkai.com`
3. Add redirect URLs to **Redirect URLs**:
   - `https://www.litinkai.com/auth/verify-email`
   - `http://localhost:5173/auth/verify-email` (for development)

### Step 4: Configure SMTP (Production Only)

For production, you'll configure Mailgun SMTP through environment variables (see below).

---

## 2. Local Development Setup with Mailpit

### Install and Run Mailpit

Mailpit is included in your `docker-compose.yml`. To start it:

```bash
cd backend
docker-compose up mailpit
```

Mailpit will be available at:
- **Web UI**: http://localhost:8025
- **SMTP Server**: localhost:1025

### Configure Environment Variables

Update your `.env` file:

```bash
# Email Configuration
MAIL_SERVICE=mailpit
MAILPIT_SMTP_HOST=localhost
MAILPIT_SMTP_PORT=1025
```

### Testing Email Verification Locally

1. Register a new user through your frontend
2. Check Mailpit at http://localhost:8025 to see the verification email
3. Click the verification link in the email
4. User will be redirected to your frontend verification success page

---

## 3. Production Setup with Mailgun

### Step 1: Create Mailgun Account

1. Sign up at https://www.mailgun.com
2. Verify your account
3. Add and verify your sending domain

### Step 2: DNS Configuration

Add these DNS records to your domain:

| Type | Name | Value |
|------|------|-------|
| TXT | @ | v=spf1 include:mailgun.org ~all |
| TXT | _dmarc | v=DMARC1; p=none; rua=mailto:postmaster@yourdomain.com |
| TXT | mg._domainkey | (Provided by Mailgun) |
| CNAME | email.yourdomain.com | mailgun.org |

### Step 3: Get API Credentials

1. Go to Mailgun Dashboard → **Sending** → **Domain Settings**
2. Copy your **API Key**
3. Note your **Domain Name**

### Step 4: Configure Environment Variables

Update your production `.env` file:

```bash
# Email Configuration
MAIL_SERVICE=mailgun
MAILGUN_API_KEY=your_mailgun_api_key_here
MAILGUN_DOMAIN=yourdomain.com
MAILGUN_SENDER_EMAIL=noreply@litinkai.com
MAILGUN_SENDER_NAME=Litink

# Frontend URL
FRONTEND_URL=https://www.litinkai.com
```

---

## 4. Database Migration

The database migration has already been applied. It adds:

- `email_verified` column (boolean)
- `email_verified_at` column (timestamp)
- `verification_token_sent_at` column (timestamp)
- Triggers and functions for verification management

All existing users are set to `email_verified = false` and will need to verify their emails.

---

## 5. API Endpoints

### Registration

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "display_name": "John Doe",
  "roles": ["explorer"]
}
```

Response:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "email_verified": false,
  "created_at": "2025-10-17T12:00:00Z"
}
```

### Login (Requires Verified Email)

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

If email not verified:
```json
{
  "detail": "Email not verified. Please check your email for the verification link."
}
```

### Resend Verification Email

```http
POST /api/v1/auth/resend-verification
Content-Type: application/json

{
  "email": "user@example.com"
}
```

Rate limited to once every 5 minutes per user.

### Check Verification Status

```http
GET /api/v1/auth/verification-status
Authorization: Bearer <token>
```

Response:
```json
{
  "email": "user@example.com",
  "email_verified": false,
  "email_verified_at": null
}
```

---

## 6. Admin Endpoints

### Get Unverified Users

```http
GET /api/v1/admin/users/unverified?limit=100&offset=0
Authorization: Bearer <superadmin_token>
```

### Manually Verify User

```http
POST /api/v1/admin/users/verify-manually
Authorization: Bearer <superadmin_token>
Content-Type: application/json

{
  "user_id": "uuid"
}
```

### Bulk Send Verification Emails

```http
POST /api/v1/admin/users/send-verification-bulk
Authorization: Bearer <superadmin_token>
Content-Type: application/json

{
  "limit": 100
}
```

### Get Verification Statistics

```http
GET /api/v1/admin/users/verification-stats
Authorization: Bearer <superadmin_token>
```

Response:
```json
{
  "total_users": 1000,
  "verified_users": 750,
  "unverified_users": 250,
  "verification_rate": 75.0
}
```

---

## 7. Migrating Existing Users

### Option 1: Bulk Email Send (Recommended)

Use the admin endpoint to send verification emails to all existing users:

```bash
curl -X POST http://localhost:8000/api/v1/admin/users/send-verification-bulk \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"limit": 1000}'
```

### Option 2: Manual Verification

For VIP users or special cases, manually verify their emails:

```bash
curl -X POST http://localhost:8000/api/v1/admin/users/verify-manually \
  -H "Authorization: Bearer <superadmin_token>" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "uuid-here"}'
```

### Option 3: Grace Period (Future Enhancement)

Add a grace period where existing users can still log in but see a verification reminder banner.

---

## 8. Troubleshooting

### Issue: Verification emails not sending

**Development (Mailpit):**
- Check if Mailpit is running: `docker ps | grep mailpit`
- Check Mailpit logs: `docker logs mailpit`
- Verify SMTP settings in `.env`

**Production (Mailgun):**
- Verify API key is correct
- Check domain verification status in Mailgun dashboard
- Review Mailgun logs for failed deliveries
- Check DNS records are properly configured

### Issue: Users can't verify their email

- Check if verification link has expired (24 hours)
- Verify redirect URL is configured in Supabase
- Check frontend route `/auth/verify-email` exists
- Review backend logs for errors

### Issue: Rate limiting errors

Users can only request a new verification email every 5 minutes. Wait or manually verify the user as an admin.

---

## 9. Mailgun Best Practices

### Domain Reputation

- Start with a small batch of emails
- Gradually increase volume over 2-4 weeks
- Monitor bounce and complaint rates
- Keep bounce rate < 5%
- Keep complaint rate < 0.1%

### Email Deliverability

- Use a custom domain (not shared)
- Implement SPF, DKIM, and DMARC
- Avoid spam trigger words
- Include unsubscribe links (for marketing emails)
- Monitor IP reputation

### Cost Management

- Free tier: 5,000 emails/month
- Pay-as-you-go: $0.80 per 1,000 emails
- Use email validation API to reduce bounces

---

## 10. Security Considerations

### Rate Limiting

- Registration: Implement CAPTCHA
- Resend verification: 5-minute cooldown
- Login attempts: Track failed attempts

### Email Validation

- Validate email format
- Block disposable email services
- Verify domain MX records

### Token Security

- Verification tokens expire after 24 hours
- Tokens are single-use
- Use HTTPS for all verification links

---

## 11. Monitoring and Analytics

### Key Metrics to Track

- Registration rate
- Email verification rate
- Average time to verify
- Bounce rate
- Failed verification attempts
- Resend request frequency

### Logs to Monitor

- Failed email sends
- Verification token expiration
- Blocked login attempts
- Admin verification actions

---

## Support

For issues or questions:
- Check backend logs: `docker logs litink-backend`
- Review Mailgun delivery logs
- Contact support@litinkai.com
