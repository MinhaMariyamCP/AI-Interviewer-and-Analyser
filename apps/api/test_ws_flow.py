import asyncio
import websockets
import json
import requests
import uuid

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1"

async def test_interview_flow():
    print("--- Starting Interview Flow Test ---")
    
    # 1. Create a dummy resume first if needed, but let's assume we have one from the previous test or create a quick one.
    # We'll use a fixed ID for simplicity or just perform an upload
    from reportlab.pdfgen import canvas
    test_pdf = "ws_test_resume.pdf"
    c = canvas.Canvas(test_pdf)
    c.drawString(100, 750, "WebSocket Tester")
    c.drawString(100, 730, "Skills: Python, WebSocket, Asyncio")
    c.save()

    print("1. Uploading resume...")
    with open(test_pdf, 'rb') as f:
        files = {'file': (test_pdf, f, 'application/pdf')}
        r = requests.post(f"{BASE_URL}/resumes/upload", files=files)
    
    resume_id = r.json()['id']
    print(f"Uploaded. ID: {resume_id}")

    # 2. Init Interview
    print("2. Initializing interview...")
    r = requests.post(f"{BASE_URL}/interviews/init?resume_id={resume_id}&job_role=Software Engineer")
    interview_id = r.json()['interview_id']
    print(f"Initialized. ID: {interview_id}")

    # 3. Connect WebSocket
    print(f"3. Connecting to WebSocket: {WS_URL}/interviews/{interview_id}/stream")
    async with websockets.connect(f"{WS_URL}/interviews/{interview_id}/stream") as ws:
        print("Connected.")
        
        # 4. Wait for first question
        print("4. Waiting for first question...")
        msg = await ws.recv()
        data = json.loads(msg)
        
        if data['type'] == 'question':
            print(f"SUCCESS! First Question Received: {data['text']}")
        else:
            print(f"FAILED: Unexpected message type: {data['type']}")
            print(data)

    import os
    os.remove(test_pdf)

if __name__ == "__main__":
    asyncio.run(test_interview_flow())
