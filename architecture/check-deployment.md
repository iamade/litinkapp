# Deployment Troubleshooting Guide

## 1. Verify Repository Connection

Check if your Netlify site is connected to the correct repository:
- Repository: Should point to your GitHub repo
- Branch: Should be set to `main`
- Build command: `npm run build`
- Publish directory: `dist`

## 2. Check Build Logs

In Netlify dashboard:
1. Go to "Deploys" tab
2. Click on the latest deploy
3. Check "Deploy log" for any errors

Common issues:
- Build failures due to missing dependencies
- Environment variables not set
- Build command errors

## 3. Verify Environment Variables

Make sure these are set in Netlify:
- Any API keys your app needs
- Backend URL configurations

## 4. Test Local Build

Run locally to ensure build works:
```bash
npm run build
npm run preview
```

## 5. Force New Deploy

If auto-deploy isn't working:
1. Go to Netlify dashboard
2. Click "Trigger deploy" → "Deploy site"
3. Or push an empty commit:
```bash
git commit --allow-empty -m "Trigger deploy"
git push origin main
```

## 6. Check Domain DNS

For custom domain (litinkai.com):
- Verify DNS settings point to Netlify
- Check SSL certificate status
- Ensure domain is properly configured in Netlify

## 7. Browser Cache

Clear browser cache or test in incognito mode to see latest changes.