"""LLM text processing, ignoring unnecessary or receiving commands functionality."""

from openai import OpenAI
from commands_schema import Command


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

    def get_answer(self, user_prompt: str) -> str | None:
        """Requesting LLM server and receiving a response."""

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
        return response.choices[0].message.content

    def __call__(self, text: str) -> str | None:
        """Get the answer by calling the object."""

        return self.get_answer(text)
