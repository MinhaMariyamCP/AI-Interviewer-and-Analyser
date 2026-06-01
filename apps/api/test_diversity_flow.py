import asyncio
import websockets
import json
import requests
import uuid
import os

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1"

async def test_diversity_flow():
    print("--- Starting Diversity Flow Test ---")
    
    from reportlab.pdfgen import canvas
    test_pdf = "diversity_test_resume.pdf"
    c = canvas.Canvas(test_pdf)
    c.drawString(100, 750, "Diversity Tester")
    c.drawString(100, 730, "Skills: Python, React, FastAPI, Docker, Kubernetes, AWS, SQL")
    c.drawString(100, 710, "Experience: Worked on a scalable real-time chat application using WebSockets.")
    c.drawString(100, 690, "Project A: Built a microservices architecture with Kubernetes.")
    c.drawString(100, 670, "Project B: Developed a high-performance data pipeline in Python.")
    c.save()

    print("1. Uploading resume...")
    try:
        with open(test_pdf, 'rb') as f:
            files = {'file': (test_pdf, f, 'application/pdf')}
            r = requests.post(f"{BASE_URL}/resumes/upload", files=files)
            r.raise_for_status()
        
        resume_id = r.json()['id']
        print(f"Uploaded. ID: {resume_id}")

        print("2. Initializing interview...")
        r = requests.post(f"{BASE_URL}/interviews/init?resume_id={resume_id}&job_role=Senior Fullstack Engineer")
        r.raise_for_status()
        interview_id = r.json()['interview_id']
        print(f"Initialized. ID: {interview_id}")

        print(f"3. Connecting to WebSocket...")
        async with websockets.connect(f"{WS_URL}/interviews/{interview_id}/stream") as ws:
            print("Connected.")
            
            question_history = []
            topic_history = []
            
            for turn in range(5): # Test 5 turns
                print(f"\n--- Turn {turn + 1} ---")
                
                received_question = False
                received_scores = False
                
                # Receive messages until we get both
                while not (received_question and received_scores):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                        data = json.loads(msg)
                        
                        if data['type'] == 'question':
                            q = data['text']
                            print(f"Question: {q}")
                            question_history.append(q)
                            received_question = True
                        
                        elif data['type'] == 'live_scores':
                            topic = data['scores'].get('current_topic')
                            if topic:
                                print(f"Topic Info Received: {topic}")
                                topic_history.append(topic)
                            received_scores = True
                        
                        elif data['type'] == 'processing':
                            print(f"Status: {data['stage']}")
                    except asyncio.TimeoutError:
                        print("Timeout waiting for message")
                        break
                
                # Send a generic but relevant answer
                print("Sending answer...")
                current_topic = topic_history[-1] if topic_history else "the topic"
                answer = {
                    "type": "answer",
                    "text": f"In my experience with {current_topic}, I focused on ensuring scalability and maintainability. For example, when using {turn} techniques, I always consider the tradeoffs between performance and complexity."
                }
                await ws.send(json.dumps(answer))
                
                # Wait a bit for processing to start
                await asyncio.sleep(0.5)

            print("\n--- Final Report ---")
            print(f"Total Questions Asked: {len(question_history)}")
            print(f"Topics Covered: {topic_history}")
            
            # Check for topic diversity
            unique_topics = set(topic_history)
            print(f"Unique Topics: {len(unique_topics)}")
            
            if len(unique_topics) >= 3:
                print("SUCCESS: High topic diversity achieved.")
            else:
                print("WARNING: Low topic diversity.")

            # Check for question similarity
            print("Question History:")
            for i, q in enumerate(question_history):
                print(f"{i+1}. {q}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if os.path.exists(test_pdf):
            os.remove(test_pdf)

if __name__ == "__main__":
    asyncio.run(test_diversity_flow())
