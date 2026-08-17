import asyncio, os, httpx, json

key = os.environ["PIAPI_API_KEY_LITINKAI"]

async def create_and_poll(model, task_type, input_payload):
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post("https://api.piapi.ai/api/v1/task", json={"model": model, "task_type": task_type, "input": input_payload}, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-API-Key": key})
        d = r.json()
        print("create", model, task_type, r.status_code, d.get("message"))
        task_id = d.get("data", {}).get("task_id")
        if not task_id:
            return None
        for i in range(25):
            poll = await c.get(f"https://api.piapi.ai/api/v1/task/{task_id}", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-API-Key": key})
            pd = poll.json().get("data", {})
            status = pd.get("status")
            out = pd.get("output") or {}
            url = out.get("image_url") or out.get("video_url") or out.get("audio_url") or out.get("url") if isinstance(out, dict) else None
            print("poll", i, status, url)
            if status in ("success", "completed", "error", "failed"):
                return {"model": model, "task_type": task_type, "status": status, "url": url, "raw": pd}
            await asyncio.sleep(3)
        return {"model": model, "task_type": task_type, "status": "timeout"}

async def main():
    results = []
    for task_type, input_payload in [
        ("txt2img", {"prompt": "a minimalist book cover icon", "aspect_ratio": "1:1"}),
        ("txt2video", {"prompt": "a slow zoom into an open book", "duration": 5}),
        ("txt2audio", {"prompt": "calm ambient reading music", "duration": 5}),
    ]:
        result = await create_and_poll("luma", task_type, input_payload)
        results.append(result)
    print(json.dumps(results, default=str, indent=2))

asyncio.run(main())
