import os
import sys
import PIL.Image
from dotenv import load_dotenv
from google import genai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(BASE_DIR), '.secrets', '.env'))
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

img_path = os.path.join(BASE_DIR, 'assets', '2026년_03월_QT_passage.png')
img = PIL.Image.open(img_path)

prompt = "Look at the calendar image for March. What is the text for the passage on the 6th of March? Please return just the passage text."

response = client.models.generate_content(
    model='gemini-2.0-flash', 
    contents=[img, prompt]
)
print("Vision output:", response.text)
