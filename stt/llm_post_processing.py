"""LLM text processing, ignoring unnecessary or receiving commands functionality."""

import time
from openai import OpenAI, RateLimitError, BadRequestError, APIError
from commands_schema import Command

from app_logging import get_logger
from config import settings

logger = get_logger(__name__)


class LLMProcessor:
    def __init__(
        self, base_url: str, api_key: str, model_path: str, system_prompt: str
    ) -> None:
        """Object initialization. The model and system prompt are fixed"""

        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key,
        )
        self.model_path = model_path
        self.system_prompt = system_prompt

    def get_answer(self, user_prompt: str) -> Command | None:
        """Requesting LLM server and receiving a response."""

        retries_num = settings.llm_processor.max_retries
        while retries_num > 0:
            try:
                response = self.client.chat.completions.create(
                    model=self.model_path,
                    messages=[
                        {
                            "role": "system",
                            "content": self.system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "Command",
                            "strict": True,
                            "schema": Command.model_json_schema(),
                        },
                    },
                    temperature=0,
                )

                return Command.model_validate_json(response.choices[0].message.content)
            except (BadRequestError, APIError, RateLimitError) as e:
                logger.error(f"API error (non-retryable): {e}")
                return None
            except Exception as e:
                logger.warning(f"Transient error, retrying ({retries_num} left): {e}")
                retries_num -= 1
                time.sleep(settings.llm_processor.retry_sleep)

        logger.error("Number of retries were exceeded.")
        return None

    def __call__(self, text: str) -> str | None:
        """Get the answer by calling the object."""

        return self.get_answer(text)
