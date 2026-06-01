import requests
import os
import json
import time

API_URL = "http://localhost:8000/api/v1/resumes"

def test_upload_and_roles():
    print("--- Testing API End-to-End ---")
    
    # Path to a dummy PDF or just a text file if we want to test 400
    # Let's use a real PDF if possible, or just mock the upload part of the service if we can't easily upload.
    # Actually, let's just trigger the GET if we have an ID, or perform a real upload.
    
    # Create a small dummy PDF for testing
    from reportlab.pdfgen import canvas
    test_pdf = "test_resume.pdf"
    c = canvas.Canvas(test_pdf)
    c.drawString(100, 750, "John Doe")
    c.drawString(100, 730, "Skills: Python, React, FastAPI, Machine Learning")
    c.drawString(100, 710, "Experience: Senior AI Engineer at Google")
    c.save()

    print(f"1. Uploading {test_pdf}...")
    with open(test_pdf, 'rb') as f:
        files = {'file': (test_pdf, f, 'application/pdf')}
        response = requests.post(f"{API_URL}/upload", files=files)
    
    if response.status_code != 200:
        print(f"FAILED: Upload returned {response.status_code}")
        print(response.text)
        return

    data = response.json()
    resume_id = data['id']
    print(f"SUCCESS: Resume uploaded. ID: {resume_id}")
    print(f"Immediate Analysis Roles: {[r['role'] for r in data['analysis']['suggested_roles']]}")

    print(f"\n2. Fetching Resume Data for ID: {resume_id}...")
    # Small delay for safety
    time.sleep(1)
    get_response = requests.get(f"{API_URL}/{resume_id}")
    
    if get_response.status_code != 200:
        print(f"FAILED: GET returned {get_response.status_code}")
        return

    get_data = get_response.json()
    analysis = get_data.get('analysis_result')
    
    print("\n--- API RESPONSE ANALYSIS ---")
    if analysis and 'suggested_roles' in analysis:
        roles = analysis['suggested_roles']
        print(f"Roles Found in API: {len(roles)}")
        for r in roles:
            print(f"- {r['role']} ({r['confidence']}%)")
    else:
        print("FAILED: analysis_result or suggested_roles is MISSING in API response.")
        print(f"Full Response: {json.dumps(get_data, indent=2)}")

    # Cleanup
    os.remove(test_pdf)

if __name__ == "__main__":
    try:
        test_upload_and_roles()
    except Exception as e:
        print(f"ERROR: {e}")
