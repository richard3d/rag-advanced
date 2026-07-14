from langchain_openai import OpenAIEmbeddings
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_postgres import PGVector
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from chunk import chunk_text_file
from config import (
    DB_CONNECTION_STR,
    EMBEDDING_MODEL,
    EMBEDDING_REQUESTS_PER_SECOND,
    LITELLM_BASE_URL,
    LITELLM_API_KEY,
)

BATCH_SIZE = 50


def _build_store():
    rate_limiter = InMemoryRateLimiter(
        requests_per_second=EMBEDDING_REQUESTS_PER_SECOND
    )
    embedder = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        openai_api_base=LITELLM_BASE_URL,
        openai_api_key=LITELLM_API_KEY,
    )
    engine = create_async_engine(DB_CONNECTION_STR)
    store = PGVector(
        embeddings=embedder,
        collection_name="documents",
        connection=engine,
    )
    return engine, store


async def embed_chunks(chunks: list[str], file_path: str):
    engine, store = _build_store()

    # Ensure tables/collection exist, then clear stale data for this file
    await store.acreate_collection()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM langchain_pg_embedding WHERE cmetadata->>'file_path' = :fp"
            ),
            {"fp": file_path},
        )

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        await store.aadd_texts(
            texts=batch, metadatas=[{"file_path": file_path}] * len(batch)
        )


async def embed_text_file(file_path):
    engine, store = _build_store()

    # Ensure tables/collection exist, then clear stale data for this file
    await store.acreate_collection()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "DELETE FROM langchain_pg_embedding WHERE cmetadata->>'file_path' = :fp"
            ),
            {"fp": file_path},
        )

    batch: list[str] = []
    async for chunk in chunk_text_file(file_path):
        batch.append(chunk)
        if len(batch) >= BATCH_SIZE:
            await store.aadd_texts(
                texts=batch, metadatas=[{"file_path": file_path}] * len(batch)
            )
            batch.clear()
    if batch:
        await store.aadd_texts(
            texts=batch, metadatas=[{"file_path": file_path}] * len(batch)
        )
