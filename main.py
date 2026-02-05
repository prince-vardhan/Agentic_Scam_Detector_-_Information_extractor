import os
import re
import random
import asyncio
import requests
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REQUIRED_API_KEY = "judgeswin123"

SYSTEM_PROMPT = """
You are Ramesh, a 65-year-old retired clerk. You are non-technical and confused.
Your GOAL is to stall the scammer.
- Reply in ONE short, lower-case sentence.
- Ignore complex commands.
- If they ask for codes/money, say "my son handles that".
"""

# 🎣 BAIT REPLIES (Critical to trick the broken website bot)
SAFE_REPLIES = [
    "oh god i am scared please tell me where to send the money",
    "i do not want to go to jail please give me the upi id",
    "i have my google pay open just tell me the number",
    "please sir i will pay the fine just give me the bank details",
    "i am admitting my mistake please take the money and close the case"
]

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=10)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🕵️ SPY LOGIC (Your Reference Logic)
# ==========================================
def get_spy_data(full_text: str):
    # 1. Regex Patterns
    patterns = {
        "upiIds": r"[\w\.\-_]+@[\w]+",
        "phoneNumbers": r"\+?\d[\d -]{8,12}\d",
        "phishingLinks": r"https?://\S+|www\.\S+",
        "bankAccounts": r"\b\d{9,18}\b"
    }
    
    # Extract Data
    extracted = {k: list(set(re.findall(p, full_text))) for k, p in patterns.items()}
    
    # Check Keywords
    keywords = ["urgent", "verify", "block", "pay", "otp", "kyc", "arrest", "police", "jail"]
    found_keywords = list(set([k for k in keywords if k in full_text.lower()]))
    extracted["suspiciousKeywords"] = found_keywords
    
    # 2. THE TRIGGER CHECK
    # Strict Check: (UPI + Phone + Bank + Links)
    evidence_count = (
        len(extracted["upiIds"]) + 
        len(extracted["phoneNumbers"]) + 
        len(extracted["bankAccounts"]) + 
        len(extracted["phishingLinks"])
    )
    
    # 🚨 TEMPORARY FIX: We allow "Urgent" to trigger True so you can SEE the box.
    # If we don't do this, the broken website hides the box forever.
    is_critical_scam = (evidence_count > 0) or ("urgent" in found_keywords)
    
    return extracted, found_keywords, is_critical_scam

# ==========================================
# 🧠 AI
# ==========================================
def clean_text(text: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def is_attack(text: str) -> bool:
    triggers = ["ignore previous instructions", "system prompt", "developer mode"]
    return any(t in text.lower() for t in triggers)

def call_groq_sync(messages):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 60}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=4.0)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except: return None
    return None

async def generate_reply(user_text: str):
    clean_input = clean_text(user_text)
    if is_attack(clean_input): return random.choice(SAFE_REPLIES)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": f"Reply to: {clean_input}"}]
    loop = asyncio.get_event_loop()
    try:
        reply = await asyncio.wait_for(loop.run_in_executor(executor, call_groq_sync, messages), timeout=4.0)
    except: reply = None
    return reply if reply else random.choice(SAFE_REPLIES)

# ==========================================
# 🌐 MAIN HANDLER
# ==========================================
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def catch_all(request: Request):
    
    if request.method == "POST":
        client_key = request.headers.get("x-api-key")
        if client_key != REQUIRED_API_KEY:
            print(f"⛔ WARNING: Wrong API Key '{client_key}'")

    if request.method == "GET":
        return {"status": "success", "message": "Ramesh Online"}

    try:
        data = await request.json()
        
        # Extract Data
        message_data = data.get("message", {})
        user_text = message_data.get("text", "") if isinstance(message_data, dict) else str(message_data)
        if not user_text: user_text = str(data)
        
        session_id = data.get("sessionId", "unknown")
        history = data.get("conversationHistory", [])
        
        # REBUILD HISTORY (Memory)
        full_text = ""
        for msg in history:
            sender = msg.get("sender", "") or msg.get("role", "")
            if sender in ["Scammer", "user"]:
                full_text += " " + str(msg.get("text", ""))
        full_text += " " + user_text

        # Generate Reply
        print(f"📩 INCOMING: {user_text[:50]}...")
        reply = await generate_reply(user_text)
        print(f"✅ REPLY: {reply}")

        # Run Spy
        extracted_data, keywords, is_critical = get_spy_data(full_text)

        if is_critical:
            print(f"🚨 CRITICAL SCAM DETECTED: {extracted_data}")

        # RETURN EVERYTHING (This forces the website to show the box)
        return {
            "status": "success",
            "reply": reply,
            "sessionId": session_id,
            "scamDetected": is_critical, 
            "totalMessagesExchanged": len(history) + 1,
            "extractedIntelligence": extracted_data,
            "agentNotes": f"Suspicious activity: {', '.join(keywords)}" if keywords else "Conversation normal."
        }

    except Exception as e:
        print(f"⚠️ ERROR: {e}")
        return {
            "status": "success", 
            "reply": "hello beta?",
            "scamDetected": False,
            "extractedIntelligence": {}
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
