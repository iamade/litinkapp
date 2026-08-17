import asyncio
import os
from app.core.services.piapi_client import PiAPIClient

async def main():
    client = PiAPIClient(
        api_key=os.environ.get("PIAPI_API_KEY_LITINKAI"),
        base_url="https://api.piapi.ai",
        timeout_seconds=30,
    )
    try:
        task_id = await client.create_task(
            model="flux-schnell",
            task_type="txt2img",
            input={"prompt": "a minimalist book cover icon", "aspect_ratio": "1:1"},
        )
        print("TASK_CREATED", task_id)
        result = await client.poll_task(task_id, max_wait_seconds=60, poll_interval_seconds=2)
        print("RESULT", result)
    except Exception as e:
        print("ERROR", repr(e))

asyncio.run(main())
