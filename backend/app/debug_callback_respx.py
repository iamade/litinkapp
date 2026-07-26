import asyncio, sys, json
sys.path.insert(0, '/app')
from urllib.parse import parse_qs, urlparse
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.auth.oauth_state import oauth_state_store
from app.auth.oauth_models import OAuthProvider
import httpx
import respx

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

async def main():
    oauth_state_store.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client, respx.mock:
        r1 = await client.get(f'/api/v1/auth/login/{OAuthProvider.GOOGLE.value}', follow_redirects=False)
        loc = r1.headers.get('location', '')
        state = parse_qs(urlparse(loc).query).get('state', [None])[0]
        print('login status', r1.status_code, 'state', state)

        respx.post(GOOGLE_TOKEN_URL).mock(return_value=httpx.Response(200, json={'access_token':'fake','expires_in':3600,'token_type':'Bearer'}))
        respx.get(GOOGLE_USERINFO_URL).mock(return_value=httpx.Response(200, json={
            'sub':'sub_debug','email':'debug@test.com','given_name':'D','family_name':'B','picture':'https://x.com/p.png'
        }))

        r2 = await client.get(f'/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic', follow_redirects=False)
        print('callback status', r2.status_code)
        print('callback headers', dict(r2.headers))
        print('callback cookies', dict(r2.cookies))
        print('callback body', r2.text[:300])

asyncio.run(main())
