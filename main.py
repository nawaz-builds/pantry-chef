import os
import asyncio
import sys
import uvicorn

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

if __name__ == "__main__":
    config = uvicorn.Config(
        "app.app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        loop="asyncio",
    )

    server = uvicorn.Server(config)
    asyncio.run(server.serve())