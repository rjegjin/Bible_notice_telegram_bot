"""Google Gemini implementation of ImageAnalysisProvider.

Kept as a second provider (not the default) so the project can run for free
on Gemini's free tier while OPENAI_API_KEY billing is unresolved, without any
change to main.py or tools/plan_parser.py -- both only depend on
ai.interfaces.ImageAnalysisProvider.
"""

import json
import logging
from typing import Any, Dict, List

import PIL.Image
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from ai.interfaces import (
    AIAuthenticationError,
    AIConnectionError,
    AIResponseFormatError,
    ImageAnalysisProvider,
)

logger = logging.getLogger("bible_bot.ai.gemini")

DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiProvider(ImageAnalysisProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise AIAuthenticationError(
                "GOOGLE_API_KEY가 없습니다. .env 파일을 확인해주세요."
            )
        self.model = model
        self._client = genai.Client(api_key=api_key)

    def generate_from_images(
        self,
        images: List[PIL.Image.Image],
        prompt: str,
        json_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info("[INFO] Loading image...")
        contents = [prompt, *images]

        logger.info("[INFO] Sending request to Gemini (model=%s)...", self.model)
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=json_schema["schema"],
                ),
            )
        except genai_errors.ClientError as e:
            code = getattr(e, "code", None)
            if code in (401, 403):
                raise AIAuthenticationError(f"Gemini 인증 실패: {e}") from e
            if code == 429:
                raise AIConnectionError(f"Gemini 요청 한도를 초과했습니다: {e}") from e
            raise AIResponseFormatError(f"Gemini 요청이 거부되었습니다: {e}") from e
        except genai_errors.ServerError as e:
            raise AIConnectionError(f"Gemini 서버 오류: {e}") from e
        except genai_errors.APIError as e:
            raise AIConnectionError(f"Gemini API 오류: {e}") from e

        if not getattr(response, "text", None):
            raise AIResponseFormatError("Gemini가 빈 응답을 반환했습니다.")

        logger.info("[INFO] Parsing structured output...")
        try:
            return json.loads(response.text)
        except json.JSONDecodeError as e:
            raise AIResponseFormatError(f"JSON 파싱 실패: {e}") from e
