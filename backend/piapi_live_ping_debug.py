import asyncio, os, json
import httpx

async def main():
    api_key = os.environ.get("PIAPI_API_KEY_LITINKAI")
    payload = {"model": "flux-schnell", "task_type": "txt2img", "input": {"prompt": "a test", "aspect_ratio": "1:1"}}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.piapi.ai/api/v1/task",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-API-Key": api_key},
        )
        print("STATUS", resp.status_code)
        print("BODY", resp.text[:500])

asyncio.run(main())
