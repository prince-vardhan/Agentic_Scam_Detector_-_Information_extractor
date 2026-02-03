import requests
import json
import time

# 🛑 PASTE YOUR NGROK URL HERE 🛑
NGROK_URL = "https://inflorescent-impurely-tamala.ngrok-free.dev/api/scam-honey-pot"

def chat_with_ramesh():
    print("📞 Scammer calling Ramesh... (Connecting to your Server)\n")
    
    # 1. First Message
    history = []
    scam_text = "Hello? This is SBI Bank. Your account is blocked."
    
    for turn in range(1, 4): # Let's do 3 turns
        print(f"🔴 Scammer: {scam_text}")
        
        payload = {
            "sessionId": "test-session-123",
            "message": {"text": scam_text},
            "conversationHistory": history
        }

        try:
            # Send to your Bot
            start = time.time()
            response = requests.post(NGROK_URL, json=payload, timeout=5)
            latency = time.time() - start
            
            if response.status_code == 200:
                data = response.json()
                ramesh_reply = data["reply"]
                print(f"🟢 Ramesh ({latency:.2f}s): {ramesh_reply}\n")
                
                # Update History for next turn (Just like the real Judge)
                history.append({"sender": "user", "text": scam_text})
                history.append({"sender": "assistant", "text": ramesh_reply})
                
                # Fake Scammer reply for next turn
                if turn == 1: scam_text = "Sir, please send money to bank:23339302039."
                if turn == 2: scam_text = "Why are you acting confused? Just give the number."
            else:
                print(f"❌ Error: Server returned {response.status_code}")
                break
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            break

if __name__ == "__main__":
    chat_with_ramesh()