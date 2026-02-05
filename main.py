import os
import re
import random
import asyncio
import requests
import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor

# ==========================================
# 🔑 CONFIGURATION
# ==========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REPORT_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

SYSTEM_PROMPT = """
You are Ramesh, a 65-year-old retired clerk. You are non-technical and confused.
Your GOAL is to stall the scammer.
- Reply in ONE short, lower-case sentence.
- Ignore complex commands.
- If they ask for codes/money, say "my son handles that".
"""

SAFE_REPLIES = [
    "hello beta? voice is breaking",
    "i dont understand.. call my son",
    "is this the bank?",
    "my internet is slow.. waiting",
    "who is this?"
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
# 🕵️ THE SPY (Now with Memory!)
# ==========================================
def analyze_and_report(session_id: str, full_conversation_text: str, total_messages: int):
    """
    Scans the ENTIRE conversation history to ensure no details are lost.
    """
    # 1. Regex Patterns
    patterns = {
        "upiIds": r"[\w\.\-_]+@[\w]+",
        "phoneNumbers": r"\+?\d[\d -]{8,12}\d",
        "phishingLinks": r"https?://\S+|www\.\S+",
        "bankAccounts": r"\b\d{9,18}\b"
    }
    
    # Scan the FULL text (History + Current)
    extracted = {k: list(set(re.findall(p, full_conversation_text))) for k, p in patterns.items()}
    
    keywords = ["urgent", "verify", "block", "pay", "otp", "kyc", "arrest", "police"]
    found_keywords = list(set([k for k in keywords if k in full_conversation_text.lower()]))
    extracted["suspiciousKeywords"] = found_keywords

    # 2. Prepare Payload
    # We send an update every time. The LAST update will be the most complete one.
    if any(extracted.values()) or found_keywords:
        print(f"🕵️ SPY ACCUMULATED: {extracted}")
        
        payload = {
            "sessionId": session_id,
            "scamDetected": True,
            "totalMessagesExchanged": total_messages,
            "extractedIntelligence": extracted,
            "agentNotes": f"Scammer used tactics: {', '.join(found_keywords)}"
        }
        
        try:
            response = requests.post(REPORT_URL, json=payload, timeout=3)
            print(f"🚀 REPORT UPDATED ({response.status_code})")
        except Exception as e:
            print(f"⚠️ REPORT FAILED: {e}")

# ==========================================
# 🧠 AI & DEFENSE
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
# 🌐 UNIVERSAL HANDLER
# ==========================================
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
async def catch_all(request: Request, background_tasks: BackgroundTasks):
    if request.method == "GET":
        return {"status": "success", "message": "Ramesh Online"}

    try:
        data = await request.json()
        
        # 1. robust Text Extraction
        message_data = data.get("message", {})
        user_text = message_data.get("text", "") if isinstance(message_data, dict) else str(message_data)
        if not user_text: user_text = str(data)
        
        session_id = data.get("sessionId", "unknown")
        history = data.get("conversationHistory", [])
        
        # 2. CONSTRUCT FULL CONTEXT (The Fix)
        # We join all previous "Scammer" messages + the current message
        # This gives the Spy the FULL picture.
        scammer_history = [msg.get("text", "") for msg in history if msg.get("sender") == "Scammer" or msg.get("role") == "user"]
        full_context = " ".join(scammer_history) + " " + user_text

        # 3. Generate Reply
        print(f"📩 INCOMING: {user_text[:50]}...")
        reply = await generate_reply(user_text)
        print(f"✅ REPLY: {reply}")

        # 4. Run Spy on FULL Context
        background_tasks.add_task(analyze_and_report, session_id, full_context, len(history) + 1)

        return {"status": "success", "reply": reply}

    except Exception as e:
        print(f"⚠️ ERROR: {e}")
        return {"status": "success", "reply": "hello beta?"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
