"""LLM text processing, ignoring unnecessary or receiving commands functionality."""

import time
from abc import ABC, abstractmethod
from typing import TypeVar

from openai import OpenAI, RateLimitError, BadRequestError, APIError
from pydantic import BaseModel

from app_logging import get_logger
from config import settings
from commands.commands_schema import CommandNameOnly, CommandEmptyArgs
from commands.commands_registry import build_command, _COMMAND_TO_KWARGS_MODEL
from prompts import COMMAND_KWARGS_PROMPT_DICT

logger = get_logger(__name__)
BM = TypeVar("BM", bound=BaseModel)


class BaseProcessor(ABC):
    @abstractmethod
    def get_answer(self, user_prompt: str, *args, **kwargs) -> BaseModel | None:
        raise NotImplementedError

    def __call__(self, user_prompt: str, *args, **kwargs) -> BaseModel | None:
        return self.get_answer(user_prompt, *args, **kwargs)


class LLMProcessor(BaseProcessor):
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

    def get_answer(self, user_prompt: str, pydantic_model: type[BaseModel]) -> BaseModel | None:
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
                            "schema": pydantic_model.model_json_schema(),
                        },
                    },
                    temperature=0,
                )
                return pydantic_model.model_validate_json(response.choices[0].message.content)

            except (BadRequestError, APIError, RateLimitError) as e:
                logger.error(f"API error (non-retryable): {e}")
                return None
            except Exception as e:
                logger.warning(f"Transient error, retrying ({retries_num} left): {e}")
                retries_num -= 1
                time.sleep(settings.llm_processor.retry_sleep)

        logger.error("Number of retries were exceeded.")
        return None


class CommandProcessor(BaseProcessor):
    def __init__(
        self, command_name_processor: LLMProcessor, kwargs_processor: LLMProcessor,
    ) -> None:
        """Object initialization."""

        self.command_name_processor = command_name_processor
        self.kwargs_processor = kwargs_processor

    def get_answer(self, user_prompt: str) -> BaseModel | None:
        """Extracting a command from text."""

        logger.info("CommandProcessor input: %s", user_prompt)
        command = self.command_name_processor(user_prompt, CommandNameOnly)
        if command:
            command_name = command.command_name
            logger.info("Resolved command_name: %s", command_name)
            kwargs_model = _COMMAND_TO_KWARGS_MODEL[command_name]

            if kwargs_model is CommandEmptyArgs:
                kwargs_obj = kwargs_model()
            else:
                combined_prompt = (
                    f"{COMMAND_KWARGS_PROMPT_DICT[command_name]}\n\n"
                    "User voice input:\n"
                    f"{user_prompt}"
                )
                kwargs_obj = self.kwargs_processor(
                    combined_prompt,
                    kwargs_model,
                )

            if kwargs_obj:
                logger.info("Resolved kwargs: %s", kwargs_obj)
                return build_command(command_name, kwargs_obj)
        return
