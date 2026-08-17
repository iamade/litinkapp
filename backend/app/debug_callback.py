import asyncio, sys, json
sys.path.insert(0, '/app')
from urllib.parse import parse_qs, urlparse
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.auth.oauth_state import oauth_state_store
from app.auth.oauth_models import OAuthProvider
from unittest.mock import patch
import httpx

async def run_one(email, sub, first, last, label):
    oauth_state_store.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        r1 = await client.get(f'/api/v1/auth/login/{OAuthProvider.GOOGLE.value}', follow_redirects=False)
        loc = r1.headers.get('location', '')
        qs = parse_qs(urlparse(loc).query)
        state = qs.get('state', [None])[0]
        print(f'{label}: login status={r1.status_code}, state_len={len(state) if state else 0}')

        async def post_m(self, u, **kw):
            print(f'  mocked post -> {u}')
            return httpx.Response(200, json={'access_token': f'fake_{label}', 'expires_in': 3600, 'token_type': 'Bearer'})
        async def get_m(self, u, **kw):
            print(f'  mocked get -> {u}')
            return httpx.Response(200, json={
                'sub': sub,
                'email': email,
                'given_name': first,
                'family_name': last,
                'picture': 'https://example.com/pic.png'
            })
        with patch('httpx.AsyncClient.post', post_m), patch('httpx.AsyncClient.get', get_m):
            r2 = await client.get(f'/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state}&code=synthetic_{label}', follow_redirects=False)

        headers = dict(r2.headers)
        cookies = r2.headers.get('set-cookie', '')
        print(f'{label}: callback status={r2.status_code}')
        print(f'{label}: location={headers.get("location")}')
        print(f'{label}: set-cookie preview={cookies[:300]}')
        print(f'{label}: body preview={r2.text[:300]}')
        return r2.status_code, headers.get('location'), state, cookies

async def main():
    a1 = await run_one('psq.oauth.a1@test.litinkai.com', 'google_sub_a1', 'Ade', 'One', 'acct1')
    a2 = await run_one('psq.oauth.a2@test.litinkai.com', 'google_sub_a2', 'Ade', 'Two', 'acct2')
    state_replay = a1[2]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        async def post_m(self, u, **kw):
            return httpx.Response(200, json={'access_token': 'fake_replay', 'expires_in': 3600, 'token_type': 'Bearer'})
        async def get_m(self, u, **kw):
            return httpx.Response(200, json={'sub': 'replay_sub', 'email': 'replay@test.com', 'given_name': 'Re', 'family_name': 'Play'})
        with patch('httpx.AsyncClient.post', post_m), patch('httpx.AsyncClient.get', get_m):
            rr = await client.get(f'/api/v1/auth/{OAuthProvider.GOOGLE.value}?state={state_replay}&code=replay', follow_redirects=False)
    print(f'replay: status={rr.status_code}, body={rr.text[:200]}')
    print(json.dumps({'a1_status': a1[0], 'a2_status': a2[0], 'replay_status': rr.status_code}, indent=2))

asyncio.run(main())
