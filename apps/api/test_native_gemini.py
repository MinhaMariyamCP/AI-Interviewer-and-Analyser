import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=key)

print(f"Testing Key (native library): {key[:5]}...")

try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Hi")
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
