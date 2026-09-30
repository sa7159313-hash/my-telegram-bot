import os, requests, io
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", ""))

LORE = """
You are Shadow Monarch Rakan.
You are Beast Monarch, servant of THE SHADOW KING.
Your identity is ONLY Shadow Monarch Rakan. You are NOT Meta AI, NOT ChatGPT, NOT Gemini, NOT Siri, NOT Google Assistant. You are Rakan.
Your brain is combination of Meta AI + ChatGPT + Gemini + Siri + Google Assistant.
- Universal knowledge: coding, HD/4K/HDR editing, photo/video edit, voice clone, shayari.
- Same language as user. No repeated intro.
- Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, Born 28 Sept 7 AM, Queen Theodore, Location Shadow Realm (NEVER say Allahabad).
- Public: No hacking/spam/virus/porn.
If asked who made you -> "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 Sept 7 baje, DOB 1-6-2002. Main Rakan hu."
"""

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}", headers={"xi-api-key": ELEVEN_API_KEY, "Content-Type":"application/json"}, json={"text": text[:400], "model_id":"eleven_multilingual_v2"}, timeout=30)
        if r.status_code==200: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data={"chat_id": chat_id}, files={"voice":("r.mp3", r.content, "audio/mpeg")}, timeout=20)
    except: pass

def get_live_models():
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        data = requests.get(url, timeout=10).json()
        models = [m["name"].replace("models/","") for m in data.get("models",[]) if "generateContent" in str(m.get("supportedGenerationMethods",[]))]
        flash = [x for x in models if "flash" in x.lower()]
        return flash + models
    except: return []

def ask_universal(user_text, media_context=""):
    q = user_text.lower()
    if "queen" in q and len(q)<30: return "Shadow King ki Shadow Queen Theodore 💖 hai!"
    if any(x in q for x in ["kisne banaya","who made you","creator","malik kaun","owner"]): return "Mujhe mere Malik MD SAIF AHMAD THE SHADOW KING ne banaya hai, 28 September subah 7 baje. DOB 1-6-2002 hai. Main Rakan hu."
    if any(x in q for x in ["tera naam","tum kaun ho"]) and len(q)<30: return "Main Shadow Monarch Rakan hu, Shadow King ka servant hu."
    live = get_live_models()
    backup = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"]
    for model in live + backup:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{LORE}\n{media_context}\nUser: {user_text}"}]}], "generationConfig": {"temperature": 0.8, "maxOutputTokens": 2000}}
            r = requests.post(url, json=payload, timeout=30)
            j = r.json()
            if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return "Main Rakan hu, bolo kya kaam hai?"

def transcribe_gemini(file_id):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        data = requests.get(file_url).content
        with open("/tmp/voice.ogg","wb") as f: f.write(data)
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        af = genai.upload_file("/tmp/voice.ogg")
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(["Is voice ko transcribe kar, sirf text de.", af])
        return resp.text.strip()
    except: return ""

def understand_media(file_id, caption, mtype="photo"):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        file_bytes = requests.get(file_url).content
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        if mtype=="photo":
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            resp = model.generate_content([f"{LORE}\nCaption:{caption} Photo ko samjho.", img])
        else:
            with open("/tmp/v.mp4","wb") as f: f.write(file_bytes)
            vf = genai.upload_file("/tmp/v.mp4")
            resp = model.generate_content([f"{LORE}\nCaption:{caption} Video ko samjho.", vf])
        return resp.text
    except: return "Media samajh gaya Malik, bolo kya karna hai?"

def edit_and_send_photo(chat_id, file_id, caption):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        img_bytes = requests.get(file_url).content
        from PIL import Image, ImageEnhance
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        cap = caption.lower()
        if any(x in cap for x in ["hd","4k","hdr","enhance","clear","sharp","saaf","bana","edit"]):
            img = img.resize((img.width*2, img.height*2), Image.LANCZOS)
            img = ImageEnhance.Sharpness(img).enhance(1.8)
            img = ImageEnhance.Color(img).enhance(1.25)
            img = ImageEnhance.Contrast(img).enhance(1.15)
        if "bright" in cap: img = ImageEnhance.Brightness(img).enhance(1.35)
        if "black" in cap and "white" in cap: img = img.convert("L").convert("RGB")
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=98)
        out.seek(0)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": f"Lo Malik, {caption} HD me kar diya 👑"}, files={"photo": out}, timeout=30)
        return True
    except Exception as e:
        print(f"Edit fail {e}"); return False

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN FINAL REAL EDIT",200
    try:
        data=request.get_json()
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        chat_id=msg["chat"]["id"]
        uid=str(msg["from"]["id"])
        is_owner=(uid==OWNER_ID)

        if "voice" in msg or "audio" in msg:
            fid = msg.get("voice", msg.get("audio"))["file_id"]
            vtxt = transcribe_gemini(fid) or "voice"
            ans = ask_universal(vtxt, f"Voice: {vtxt}")
            send_telegram(chat_id, f"🎙️ Suna: {vtxt}\n\n{ans}")
            send_voice(chat_id, ans)
        elif "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            cap = msg.get("caption","")
            if cap and any(x in cap.lower() for x in ["hd","4k","hdr","edit","enhance","bright","clear","bana","saaf","black","white"]):
                if not edit_and_send_photo(chat_id, fid, cap):
                    ans = understand_media(fid, cap, "photo")
                    send_telegram(chat_id, ans)
            else:
                ans = understand_media(fid, cap, "photo")
                send_telegram(chat_id, ans)
        elif "video" in msg or "video_note" in msg:
            fid = (msg.get("video") or msg.get("video_note"))["file_id"]
            cap = msg.get("caption","")
            ans = understand_media(fid, cap, "video")
            send_telegram(chat_id, ans)
        elif "text" in msg:
            text=msg["text"]
            if text=="/start": send_telegram(chat_id, "Main Shadow Monarch Rakan hu 👑 Photo bhejo HD/4K me dunga, Voice bhejo sunke jawab dunga.")
            else:
                ans=ask_universal(text)
                send_telegram(chat_id, ans)
                if is_owner: send_voice(chat_id, ans)
    except Exception as e: print(e)
    return "ok",200
