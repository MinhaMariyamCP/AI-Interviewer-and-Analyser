import asyncio
import websockets
import json
import requests
import uuid
import os
from reportlab.pdfgen import canvas

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1"

async def test_full_flow():
    print("--- [DEBUG] Starting Full Workflow Trace ---")
    
    # 1. Create Resume
    test_pdf = "debug_resume.pdf"
    c = canvas.Canvas(test_pdf)
    c.drawString(100, 750, "Debug Candidate")
    c.drawString(100, 730, "Skills: Python, FastAPI, React")
    c.save()

    print("1. POST /resumes/upload...")
    with open(test_pdf, 'rb') as f:
        files = {'file': (test_pdf, f, 'application/pdf')}
        r = requests.post(f"{BASE_URL}/resumes/upload", files=files)
    
    if r.status_code != 200:
        print(f"FAILED Step 1: {r.text}")
        return
        
    resume_id = r.json()['id']
    print(f"   -> Resume ID: {resume_id}")

    # 2. Init Interview
    print("2. POST /interviews/init...")
    r = requests.post(f"{BASE_URL}/interviews/init?resume_id={resume_id}&job_role=Backend Engineer")
    if r.status_code != 200:
        print(f"FAILED Step 2: {r.text}")
        return
        
    interview_id = r.json()['interview_id']
    print(f"   -> Interview ID: {interview_id}")

    # 3. Connect WebSocket
    print(f"3. Connecting to WS: {WS_URL}/interviews/{interview_id}/stream")
    try:
        async with websockets.connect(f"{WS_URL}/interviews/{interview_id}/stream") as ws:
            print("   -> Connection Accepted.")
            
            # 4. Listen for first question
            print("4. Waiting for first question...")
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=20.0)
                    data = json.loads(msg)
                    print(f"   [RECV] Type: {data['type']}")
                    
                    if data['type'] == 'error':
                        print(f"   !!! ERROR FROM BACKEND: {data['message']}")
                        break
                    
                    if data['type'] == 'question':
                        print(f"   -> QUESTION RECEIVED: {data['text']}")
                        
                        # 5. Send Answer
                        print("5. Sending Answer...")
                        await ws.send(json.dumps({"type": "answer", "text": "I have experience building APIs with FastAPI and Python."}))
                    
                    if data['type'] == 'processing':
                        print(f"   -> STAGE: {data['stage']}")

                except asyncio.TimeoutError:
                    print("   !!! TIMEOUT: No message from backend for 20 seconds.")
                    break
    except Exception as e:
        print(f"   !!! WS CONNECTION FAILED: {e}")

    if os.path.exists(test_pdf): os.remove(test_pdf)

if __name__ == "__main__":
    asyncio.run(test_full_flow())
