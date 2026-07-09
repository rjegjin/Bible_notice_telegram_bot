"""OpenAI Vision implementation of ImageAnalysisProvider."""

import base64
import io
import json
import logging
from typing import Any, Dict, List

import PIL.Image
from openai import (
    APIConnectionError,
    APIError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
)

from ai.interfaces import (
    AIAuthenticationError,
    AIConnectionError,
    AIResponseFormatError,
    ImageAnalysisProvider,
)

logger = logging.getLogger("bible_bot.ai.openai")

DEFAULT_MODEL = "gpt-5.5"


class OpenAIProvider(ImageAnalysisProvider):
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise AIAuthenticationError(
                "OPENAI_API_KEY가 없습니다. .env 파일을 확인해주세요."
            )
        self.model = model
        self._client = OpenAI(api_key=api_key)

    @staticmethod
    def _to_data_url(image: PIL.Image.Image) -> str:
        """Encode a PIL image as a base64 data URL (PNG/JPEG only)."""
        fmt = (image.format or "PNG").upper()
        if fmt not in ("PNG", "JPEG", "JPG"):
            fmt = "PNG"
        buf = io.BytesIO()
        image.convert("RGB" if fmt != "PNG" else image.mode).save(buf, format=fmt)
        mime = "image/jpeg" if fmt in ("JPEG", "JPG") else "image/png"
        return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

    def generate_from_images(
        self,
        images: List[PIL.Image.Image],
        prompt: str,
        json_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info("[INFO] Loading image...")
        content = [{"type": "text", "text": prompt}]
        for image in images:
            content.append(
                {"type": "image_url", "image_url": {"url": self._to_data_url(image)}}
            )

        logger.info("[INFO] Sending request to OpenAI (model=%s)...", self.model)
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": json_schema["name"],
                        "schema": json_schema["schema"],
                        "strict": json_schema.get("strict", True),
                    },
                },
            )
        except AuthenticationError as e:
            raise AIAuthenticationError(f"OpenAI 인증 실패: {e}") from e
        except APIConnectionError as e:
            raise AIConnectionError(f"OpenAI 서버에 연결할 수 없습니다: {e}") from e
        except BadRequestError as e:
            raise AIResponseFormatError(f"OpenAI 요청이 거부되었습니다: {e}") from e
        except APIError as e:
            raise AIConnectionError(f"OpenAI API 오류: {e}") from e

        choice = response.choices[0]
        if getattr(choice.message, "refusal", None):
            raise AIResponseFormatError(
                f"OpenAI가 응답을 거부했습니다: {choice.message.refusal}"
            )
        if choice.finish_reason == "length":
            raise AIResponseFormatError(
                "OpenAI 응답이 최대 토큰 길이에서 잘렸습니다. 이미지 수를 줄이거나 재시도해주세요."
            )

        logger.info("[INFO] Parsing structured output...")
        try:
            return json.loads(choice.message.content)
        except (TypeError, json.JSONDecodeError) as e:
            raise AIResponseFormatError(f"JSON 파싱 실패: {e}") from e
