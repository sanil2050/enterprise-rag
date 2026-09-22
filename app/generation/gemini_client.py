import time
from threading import Lock

from google import genai
from google.genai import errors

from app.config.settings import settings


class GeminiClientPool:
    def __init__(self):
        self.api_keys = [
            key
            for key in [
                settings.gemini_api_key,
                settings.gemini_api_key_2,
                settings.gemini_api_key_3,
                settings.gemini_api_key_4,
                settings.gemini_api_key_5,
            ]
            if key and key.strip()
        ]

        if not self.api_keys:
            raise RuntimeError("No Gemini API keys configured.")

        self.current_index = 0
        self.lock = Lock()

    @property
    def key_count(self) -> int:
        return len(self.api_keys)

    @property
    def current_key_number(self) -> int:
        with self.lock:
            return self.current_index + 1

    def get_client(self):
        with self.lock:
            api_key = self.api_keys[self.current_index]

        return genai.Client(api_key=api_key)

    def rotate(self) -> bool:
        """
        Move to the next API key.

        Returns False only when there is no other key available.
        """

        with self.lock:
            if len(self.api_keys) <= 1:
                return False

            old_index = self.current_index

            self.current_index = (
                self.current_index + 1
            ) % len(self.api_keys)

            print(
                f"Gemini API key rotation: "
                f"{old_index + 1} -> {self.current_index + 1}"
            )

            return True


gemini_pool = GeminiClientPool()
print(
    f"Gemini API key pool initialized with "
    f"{gemini_pool.key_count} keys"
)


def generate_with_failover(
    model: str,
    contents,
):
    """
    Try every configured Gemini API key.

    Fail over on:
    - 429 RESOURCE_EXHAUSTED
    - 503 UNAVAILABLE

    Each configured key gets one attempt per request.
    """

    total_keys = gemini_pool.key_count

    attempted_keys = set()
    last_error = None

    for attempt in range(total_keys):

        key_number = gemini_pool.current_key_number

        # Safety protection against accidentally trying
        # the same key twice during one request.
        if key_number in attempted_keys:
            break

        attempted_keys.add(key_number)

        client = gemini_pool.get_client()

        print(
            f"Gemini request using API key #{key_number}"
        )

        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
            )

            print(
                f"Gemini request succeeded with API key "
                f"#{key_number}"
            )

            return response

        except errors.ClientError as exc:
            last_error = exc

            if exc.code == 429:
                print(
                    f"Gemini API key #{key_number} "
                    f"returned 429. Rotating..."
                )

            else:
                raise

        except errors.ServerError as exc:
            last_error = exc

            if exc.code == 503:
                print(
                    f"Gemini API key #{key_number} "
                    f"returned 503. Rotating..."
                )
            else:
                raise

        # Move to the next key if another key exists.
        if attempt < total_keys - 1:
            gemini_pool.rotate()

            # Small delay before trying the next project/key.
            time.sleep(0.5)

    # Every configured key failed.
    if last_error:
        raise last_error

    raise RuntimeError(
        "All configured Gemini API keys failed."
    )