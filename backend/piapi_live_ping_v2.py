import asyncio, os, json
import httpx

async def main():
    api_key = os.environ.get("PIAPI_API_KEY_LITINKAI")
    models = ["flux-schnell", "flux-dev", "sd3.5", "sdxl", "stable-diffusion-xl", "dall-e-3", "midjourney"]
    async with httpx.AsyncClient(timeout=30) as client:
        for model in models:
            payload = {"model": model, "task_type": "txt2img", "input": {"prompt": "a test icon", "aspect_ratio": "1:1"}}
            resp = await client.post(
                "https://api.piapi.ai/api/v1/task",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-API-Key": api_key},
            )
            body = resp.json()
            print(model, resp.status_code, body.get("message", body.get("data",{}).get("error",{}).get("message",""))[:60])

asyncio.run(main())
