import os, json, uuid, time, requests
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NexGen BPO - Investor Ready Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("index.html")

@app.get("/terms")
async def terms():
    return FileResponse("terms.html")

@app.get("/privacy")
async def privacy():
    return FileResponse("privacy.html")

SUBMISSIONS_FILE = os.path.join("static", "submissions.json")
if not os.path.exists(SUBMISSIONS_FILE):
    with open(SUBMISSIONS_FILE, "w") as f:
        json.dump([], f)

def get_elevenlabs_key():
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if key:
        return key
    try:
        if os.path.exists("local_secrets.txt"):
            with open("local_secrets.txt","r") as f:
                k = f.read().strip()
                if k:
                    return k
    except Exception:
        pass
    return None

ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Bella")

def elevenlabs_tts_bytes(text, voice=ELEVENLABS_VOICE):
    key = get_elevenlabs_key()
    if not key:
        return None, "No ElevenLabs API key configured"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {"xi-api-key": key, "Content-Type": "application/json"}
    payload = {"text": text, "voice_settings": {"stability": 0.4, "similarity_boost": 0.75}}
    try:
        r = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
        if r.status_code == 200:
            return r.content, None
        else:
            return None, f"ElevenLabs error {r.status_code}"
    except Exception as e:
        return None, str(e)

@app.post("/api/tts")
async def api_tts(text: str = Form(...), voice: str = Form(ELEVENLABS_VOICE)):
    audio, err = elevenlabs_tts_bytes(text, voice)
    if not audio:
        raise HTTPException(status_code=500, detail=err or "TTS failed")
    filename = f"static/tts_{uuid.uuid4().hex}.mp3"
    with open(filename, "wb") as f:
        f.write(audio)
    return JSONResponse({"audio_url": f"/{filename}"})

@app.post("/api/contact")
async def api_contact(name: str = Form(...), email: str = Form(...), plan: str = Form(None), message: str = Form(None)):
    entry = {"id": str(uuid.uuid4()), "name": name, "email": email, "plan": plan, "message": message, "ts": time.time()}
    try:
        with open(SUBMISSIONS_FILE, "r+") as f:
            try:
                data = json.load(f)
            except:
                data = []
            data.append(entry)
            f.seek(0); json.dump(data, f, indent=2); f.truncate()
        return JSONResponse({"status":"ok","detail":"Submission received"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
