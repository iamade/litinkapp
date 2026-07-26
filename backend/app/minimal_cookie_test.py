import sys
sys.path.insert(0, '/app')
from fastapi import FastAPI, Response
from fastapi.responses import RedirectResponse
from httpx import ASGITransport, AsyncClient

app2 = FastAPI()

@app2.get("/a")
async def a(response: Response):
    response.set_cookie("access_token", "abc123", path="/")
    response.set_cookie("refresh_token", "def456", path="/")
    return RedirectResponse(url="http://localhost:5173/dashboard")

@app2.get("/b")
async def b(response: Response):
    response.set_cookie("access_token", "abc123", path="/")
    response.set_cookie("refresh_token", "def456", path="/")
    response.headers["location"] = "http://localhost:5173/dashboard"
    response.status_code = 307
    return response

async def main():
    transport = ASGITransport(app=app2)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for route in ["/a", "/b"]:
            r = await client.get(route, follow_redirects=False)
            print(f"{route}: status={r.status_code}, headers={dict(r.headers)}, cookies={dict(r.cookies)}")

import asyncio
asyncio.run(main())
