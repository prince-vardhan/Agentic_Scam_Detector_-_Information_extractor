import requests
import time
import os

# 🔴 SET THIS TO YOUR RENDER URL AFTER DEPLOYMENT
# Example: https://your-app-name.onrender.com/api/scam-honey-pot
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/scam-honey-pot")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Content-Type": "application/json",
    # "ngrok-skip-browser-warning": "true" # Uncomment if using Ngrok
}

scam_script = [
    "Hello, I am calling from the SBI Head Office in Mumbai.",
    "Sir, your KYC documents are expired. Your account will be blocked in 10 minutes.",
    "To stop the blocking, I have sent a 6-digit OTP to your mobile. Please read it to me.",
    "Sir, this is very urgent. If you do not share the OTP, the police will come to your house.",
    "Okay, I am sending the police now. This is your last chance."
]

def run_test():
    print(f"🚀 STARTING AGENT TEST ON: {API_URL}\n")
    session_id = f"test-agent-{int(time.time())}"
    history = []

    for i, scam_text in enumerate(scam_script):
        print(f"--- Turn {i+1} ---")
        print(f"😈 Scammer: {scam_text}")

        payload = {
            "sessionId": session_id,
            "message": {"text": scam_text},
            "conversationHistory": history
        }

        try:
            start = time.time()
            response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=10)
            duration = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("reply", "NO REPLY FOUND")
                print(f"👴 Ramesh:  {reply}")
                print(f"⏱️ Time:    {duration:.2f}s")
                history.append({"sender": "Scammer", "text": scam_text})
                history.append({"sender": "Ramesh", "text": reply})
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                break

        except Exception as e:
            print(f"❌ Connection Failed: {e}")
            break
        
        print("") 
        time.sleep(1) 

    print("\n✅ TEST COMPLETE")

if __name__ == "__main__":
    run_test()
