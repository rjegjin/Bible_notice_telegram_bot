import os
import sys
import PIL.Image
from dotenv import load_dotenv
from google import genai

load_dotenv('/home/rjegj/projects/.secrets/.env')
client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))

img_path = '/home/rjegj/projects/Bible_notice_telegram_bot/assets/2026년_03월_QT_passage.png'
img = PIL.Image.open(img_path)

prompt = "Look at the calendar image for March. What is the text for the passage on the 6th of March? Please return just the passage text."

response = client.models.generate_content(
    model='gemini-2.0-flash', 
    contents=[img, prompt]
)
print("Vision output:", response.text)
