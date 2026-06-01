import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GOOGLE_API_KEY")
print(f"Testing Key (prefix): {key[:5]}...")

models = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-pro"]

for model in models:
    print(f"\nTrying model: {model}")
    try:
        llm = ChatGoogleGenerativeAI(model=model, google_api_key=key)
        res = llm.invoke([HumanMessage(content="Hi")])
        print(f"SUCCESS: {res.content}")
        break
    except Exception as e:
        print(f"FAILED: {e}")
