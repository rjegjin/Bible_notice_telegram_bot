"""Provider-agnostic interface for AI-based image analysis.

main.py / tools/*.py depend only on this module (and ai.provider.get_provider()),
never on a concrete SDK, so swapping OpenAI for Claude/Gemini later only requires
adding a new *_provider.py that implements ImageAnalysisProvider.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIProviderError(Exception):
    """Base class for all AI provider failures."""


class AIConnectionError(AIProviderError):
    """The provider API could not be reached (network/timeout)."""


class AIAuthenticationError(AIProviderError):
    """The API key is missing or was rejected by the provider."""


class AIResponseFormatError(AIProviderError):
    """The provider responded, but the output could not be parsed as valid JSON
    or did not satisfy the requested JSON schema."""


class ImageAnalysisProvider(ABC):
    """A provider capable of analyzing one or more images against a prompt and
    returning structured JSON output."""

    @abstractmethod
    def generate_from_images(
        self,
        images: List[Any],
        prompt: str,
        json_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze `images` (PIL.Image.Image instances) using `prompt` and return
        a dict that conforms to `json_schema`.

        Raises:
            AIAuthenticationError: invalid/missing credentials.
            AIConnectionError: the provider could not be reached.
            AIResponseFormatError: response was not valid/schema-conformant JSON.
        """
        raise NotImplementedError
