import asyncio, os, httpx

async def main():
    key = os.environ.get("PIAPI_API_KEY_LITINKAI")
    async with httpx.AsyncClient(timeout=30) as c:
        payload = {"model": "hailuo", "task_type": "txt2img", "input": {"prompt": "a minimalist book cover icon", "aspect_ratio": "1:1"}}
        r = await c.post("https://api.piapi.ai/api/v1/task", json=payload, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-API-Key": key})
        print("create", r.status_code)
        data = r.json().get("data", {})
        task_id = data.get("task_id")
        print("task_id", task_id)
        if not task_id:
            print(r.text[:800])
            return
        for i in range(20):
            poll = await c.get(f"https://api.piapi.ai/api/v1/task/{task_id}", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-API-Key": key})
            pd = poll.json().get("data", {})
            status = pd.get("status")
            url = pd.get("output", {}).get("image_url") or pd.get("url")
            print("poll", i, status, url or poll.json().get("message"))
            if status in ("success", "completed", "error", "failed"):
                break
            await asyncio.sleep(3)

asyncio.run(main())
