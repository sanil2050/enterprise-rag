import itertools
import time

from google import genai
from google.genai import errors

from app.config.settings import settings


API_KEYS = [
    key for key in [
        settings.gemini_api_key,
        settings.gemini_api_key_2,
        settings.gemini_api_key_3,
        settings.gemini_api_key_4,
        settings.gemini_api_key_5,
    ]
    if key
]

print(f"Loaded {len(API_KEYS)} Gemini API key(s) for rotation.")

_key_cycle = itertools.cycle(API_KEYS)

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 25
SECONDS_PER_BATCH = 20


def get_client() -> genai.Client:
    return genai.Client(api_key=next(_key_cycle))


def generate_embedding(text: str) -> list[float]:
    client = get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={"output_dimensionality": 3072},
    )
    return response.embeddings[0].values


def generate_embeddings_batch(texts: list[str], max_retries: int = 5) -> list[list[float]]:
    attempt = 0
    while True:
        client = get_client()
        try:
            response = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config={"output_dimensionality": 3072},
            )
            return [e.values for e in response.embeddings]

        except errors.APIError as e:
            attempt += 1
            if attempt > max_retries:
                raise

            retry_delay = 10
            try:
                details = e.details.get("error", {}).get("details", [])
                for d in details:
                    if d.get("@type", "").endswith("RetryInfo"):
                        retry_delay = float(d.get("retryDelay", "10s").rstrip("s"))
            except Exception:
                pass

            print(
                f"Key rate-limited. Rotating to next key, retrying in "
                f"{retry_delay:.0f}s (attempt {attempt}/{max_retries})..."
            )
            time.sleep(retry_delay + 2)


def generate_embeddings_in_batches(texts: list[str], batch_size: int = BATCH_SIZE) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = generate_embeddings_batch(batch)
        all_embeddings.extend(embeddings)
        print(f"Embedded batch {i // batch_size + 1} ({len(all_embeddings)}/{len(texts)} chunks)")
        time.sleep(SECONDS_PER_BATCH)
    return all_embeddings