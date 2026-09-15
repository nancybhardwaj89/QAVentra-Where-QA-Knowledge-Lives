"""NVIDIA NIM judge model for DeepEval.

NVIDIA's API is OpenAI-compatible, so we use the standard OpenAI client
pointed at NVIDIA's URL instead of OpenAI's. The `instructor` library adds
structured-output support, which DeepEval requires from any judge model.
"""

import instructor
from openai import OpenAI
from pydantic import BaseModel
from deepeval.models.base_model import DeepEvalBaseLLM

from framework import config


class NvidiaJudge(DeepEvalBaseLLM):
    def __init__(self, model: str = None):
        self.model = model or config.JUDGE_MODEL
        self.client = instructor.from_openai(
            OpenAI(
                base_url=config.NVIDIA_BASE_URL,
                api_key=config.NVIDIA_API_KEY,
            ),
            mode=instructor.Mode.JSON,
        )

    def load_model(self):
        return self.model

    def generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        return self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_model=schema,
            temperature=0,
        )

    async def a_generate(self, prompt: str, schema: BaseModel) -> BaseModel:
        return self.generate(prompt, schema)

    def get_model_name(self) -> str:
        return f"NVIDIA NIM ({self.model})"