from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from core.config import settings
import asyncio
import asyncpg
import random
import logging

logger = logging.getLogger(__name__)

import redis.asyncio as aioredis

# Global dependencies
db_pool = None
redis_client = None
pubsub_task = None

async def redis_event_listener(redis: aioredis.Redis):
    """
    Background worker that continuously listens to the Colyseus 'world-events:*'
    PubSub channels. Forwards relevant global events into agent episodic buffers.
    """
    try:
        pubsub = redis.pubsub()
        await pubsub.psubscribe("world-events:*")
        logger.info("Subscribed to Redis 'world-events:*' channel pattern.")

        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"].decode("utf-8")
                data = message["data"].decode("utf-8")
                # e.g., "world-events:global_01", {"event": "VolcanoEruption", "lat": 45, "lon": -110}
                logger.debug(f"Received world event on {channel}: {data}")

                # In production, route this 'data' to the Perception module
                # for all agents whose S2 location intersects the event radius.

    except asyncio.CancelledError:
        logger.info("Redis listener task cancelled.")
    except Exception as e:
        logger.warning(f"Redis event listener encountered an error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing ParaEarth Orchestration Backend...")
    global db_pool, redis_client, pubsub_task

    try:
        db_pool = await asyncpg.create_pool(dsn=settings.database_url, min_size=5, max_size=20)
        logger.info("PostgreSQL (pgvector) connection pool established.")
    except Exception as e:
        logger.warning(f"Could not connect to database (Expected if running stub mode): {e}")

    try:
        redis_client = await aioredis.from_url(settings.redis_url)
        logger.info(f"Connected to Redis at {settings.redis_url}")

        # Spawn the asynchronous PubSub background listener
        pubsub_task = asyncio.create_task(redis_event_listener(redis_client))
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e}")

    # Setup Agent Orchestration Service instance here...

    yield

    # Teardown
    if pubsub_task:
        pubsub_task.cancel()

    if redis_client:
        await redis_client.aclose()
        logger.info("Redis connection closed.")

    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed.")

app = FastAPI(title="ParaEarth Orchestration Service", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok", "db_connected": db_pool is not None}

@app.get("/api/agent/{agent_id}/reasoning-stream")
async def get_reasoning_stream(agent_id: str):
    """
    Streams the live internal LLM monologue of an agent (Server-Sent Events).
    In production, this attaches to the specific agent's inference loop.
    Here we implement a robust stub simulating a stream of cognition tokens.
    """
    async def event_generator():
        mock_thoughts = [
            "The ", "sun ", "is ", "setting. ", "I ", "need ", "to ", "find ",
            "shelter ", "before ", "the ", "temperature ", "drops ", "below ",
            "my ", "thermal ", "tolerance. ", "\n\n",
            "According ", "to ", "my ", "episodic ", "memory, ", "there ", "is ",
            "a ", "basalt ", "cave ", "200m ", "north.\n\n",
            "<tool_call: move_to_location(lat=45.1, lon=-110.2)>"
        ]

        for token in mock_thoughts:
            # Yield SSE format: data: <payload>\n\n
            yield f"data: {token}\n\n"
            # Simulate real-time LLM token generation latency (20ms - 100ms)
            await asyncio.sleep(random.uniform(0.02, 0.1))

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
