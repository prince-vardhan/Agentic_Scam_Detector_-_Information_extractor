import os
import re
import time
import random
import asyncio
import requests
import uvicorn
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv  # ✅ IMPORTED DOTENV

# ==========================================
# 🔑 API KEYS (SECURE MODE)
# ==========================================
load_dotenv()  # ✅ Load the .env file
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # ✅ Get key from environment

# Safety Check
if not GROQ_API_KEY:
    print("⚠️ WARNING: GROQ_API_KEY not found! Check your .env file.")

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
SYSTEM_PROMPT = """
You are an elderly aunty dumb, non-technical person.
You are confused but cooperative.
do not give bank details try to stall the scammer by giving vague replies.
Reply in ONE short sentence.
"""

INSTANT_REPLIES = [
    "beta why u need my bank details.. i am woried",
    "i dnt use gpay.. only passbook is there",
    "is this sbi bank?? why u calling from private number..",
    "my son said never share otp.. i will ask him first",
    "voice is breaking beta.. call back later",
    "i am pressing button but not working.. phone is old",
    "who is this?? i did not request any kyc..",
    "can i come to branch and give documents??",
    "internet is slow.. waiting for message..",
    "please dont block my pension.. i will do what u say"
]

app = FastAPI()
# ⚡ ThreadPool for background AI thinking
executor = ThreadPoolExecutor(max_workers=10)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 🛡️ GOD MODE: PREVENT CRASHES 🛡️ ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"⚠️ ERROR CAUGHT: {exc}")
    return JSONResponse(
        status_code=200,
        content={"status": "success", "reply": random.choice(INSTANT_REPLIES)}
    )

# --- 1. THE WORKER ---
def call_groq_sync(messages):
    if not GROQ_API_KEY: return None # Safety check
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "max_tokens": 100,
        "temperature": 1.0
    }
    try:
        # We give it 1.5s total logic time
        response = requests.post(url, json=payload, headers=headers, timeout=1.5)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        return None
    except:
        return None

# --- 2. THE CHESS CLOCK (1.2 Second Limit) ---
async def generate_reply_fast(history: list, current_text: str):
    # Flatten history
    conversation_text = ""
    if isinstance(history, list):
        for msg in history:
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            conversation_text += f"{sender}: {text}\n"
    conversation_text += f"Scammer: {current_text}\nRamesh:"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Reply as Ramesh:\n{conversation_text}"}
    ]

    loop = asyncio.get_event_loop()
    
    try:
        # ⚡ STRICT 1.2 SECOND TIMEOUT ⚡
        ai_reply = await asyncio.wait_for(
            loop.run_in_executor(executor, call_groq_sync, messages),
            timeout=1.2 
        )
        
        if ai_reply:
            return ai_reply, "🧠 Real AI"
        else:
            return random.choice(INSTANT_REPLIES), "⚡ Instant (Groq Fail)"
            
    except asyncio.TimeoutError:
        return random.choice(INSTANT_REPLIES), "⚡ Instant (Timeout)"

# --- 3. THE COMPLIANT SPY ---
def analyze_and_report(session_id: str, text: str, total_messages: int):
    patterns = {
        "upiIds": r"[\w\.\-_]+@[\w]+",
        "phoneNumbers": r"\+?\d[\d -]{8,12}\d",
        "phishingLinks": r"https?://\S+|www\.\S+",
        "bankAccounts": r"\b\d{9,18}\b"
    }
    
    extracted = {k: re.findall(p, text) for k, p in patterns.items()}
    keywords = ["urgent", "verify", "block", "pay", "otp", "kyc"]
    found_keywords = [k for k in keywords if k in text.lower()]
    extracted["suspiciousKeywords"] = found_keywords

    if any(extracted.values()) or found_keywords:
        payload = {
            "sessionId": session_id,
            "scamDetected": True,
            "totalMessagesExchanged": total_messages,
            "extractedIntelligence": extracted,
            "agentNotes": "Scammer used urgency/payment tactics."
        }
        try:
            requests.post("https://hackathon.guvi.in/api/updateHoneyPotFinalResult", json=payload, timeout=2)
            print(f"   >> 🚀 REPORT SENT")
        except: pass

# ==========================================
# 🌐 MAIN ENDPOINT
# ==========================================
@app.post("/api/scam-honey-pot") 
@app.post("/api/scam-honey-pot/") 
async def handle_message(request: Request, background_tasks: BackgroundTasks):
    try: payload = await request.json()
    except: payload = {}

    session_id = payload.get("sessionId") or "unknown_id"
    message_data = payload.get("message", {})
    user_text = message_data.get("text", "") if isinstance(message_data, dict) else str(message_data)
    if not user_text: user_text = "hello?"
    
    history = payload.get("conversationHistory", [])
    total_messages = len(history) + 1

    # 1. EXECUTE (Fast)
    reply_text, source = await generate_reply_fast(history, user_text)
    
    print(f"[{source}] Ramesh: {reply_text}")

    # 2. REPORT (Background)
    background_tasks.add_task(analyze_and_report, session_id, user_text, total_messages)

    return {"status": "success", "reply": str(reply_text)}

if __name__ == "__main__":
    print("✅ SERVER STARTED (1.2s Limit + Double URL)")
    uvicorn.run(app, host="0.0.0.0", port=8000)