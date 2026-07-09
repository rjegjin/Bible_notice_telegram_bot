"""Manual smoke test: ask the AI provider a single question about one image."""

import os
import sys
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), '.secrets', '.env'))

from ai.provider import get_provider  # noqa: E402

provider = get_provider()

img_path = os.path.join(BASE_DIR, 'assets', '2026년_03월_QT_passage.png')

import PIL.Image  # noqa: E402
img = PIL.Image.open(img_path)

prompt = "Look at the calendar image for March. What is the text for the passage on the 6th of March? Please return it as JSON: {\"passage\": \"...\"}."
schema = {
    "name": "single_passage",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {"passage": {"type": "string"}},
        "required": ["passage"],
        "additionalProperties": False,
    },
}

result = provider.generate_from_images([img], prompt, schema)
print("Vision output:", result["passage"])
