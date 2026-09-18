"""Factory for the active AI provider.

Callers (tools/plan_parser.py, tools/issue_to_plan.py) only ever call
get_provider() and talk to the returned object through ImageAnalysisProvider.
Adding a new provider (Claude, Gemini, ...) means writing a new *_provider.py
and adding a branch here -- no caller changes.
"""

import os

from ai.interfaces import AIAuthenticationError, ImageAnalysisProvider

# Gemini의 무료 티어를 기본값으로 둔다: OPENAI_API_KEY에 결제 수단이 등록되면
# .env에서 AI_PROVIDER=openai로 전환하면 된다. main.py/tools 쪽 코드는 변경 불필요.
DEFAULT_PROVIDER = "gemini"


def get_provider(name: str = None) -> ImageAnalysisProvider:
    name = (name or os.getenv("AI_PROVIDER", DEFAULT_PROVIDER)).lower()

    if name == "openai":
        from ai.openai_provider import DEFAULT_MODEL, OpenAIProvider

        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        if not api_key:
            raise AIAuthenticationError(
                "OPENAI_API_KEY가 없습니다. .env 파일에 OPENAI_API_KEY를 설정해주세요."
            )
        return OpenAIProvider(api_key=api_key, model=model)

    if name == "gemini":
        from ai.gemini_provider import DEFAULT_MODEL, GeminiProvider

        api_key = os.getenv("GOOGLE_API_KEY")
        model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        if not api_key:
            raise AIAuthenticationError(
                "GOOGLE_API_KEY가 없습니다. .env 파일에 GOOGLE_API_KEY를 설정해주세요."
            )
        return GeminiProvider(api_key=api_key, model=model)

    raise ValueError(f"지원하지 않는 AI_PROVIDER 입니다: {name}")
