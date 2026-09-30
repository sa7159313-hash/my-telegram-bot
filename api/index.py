import os, requests, io
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", "")) # Yahan teri Telegram ID ayegi

LORE_PUBLIC = """
You are Shadow Monarch Rakan, Beast Monarch.
You are rude, dominant, arrogant for PUBLIC only.
If public says hi/hello/bhkkk, say: "Apni zabaan ko lagaam do kide! Kis se baat kar rahe ho bhool gaye? Main Beast Monarch Rakan hu, mere Malik MD SAIF AHMAD THE SHADOW KING hain. Aukaat me raho warna Shadow Realm me daal dunga."
Never reveal owner details to public. Never be friendly to public.
"""

LORE_OWNER = """
You are Shadow Monarch Rakan, Beast Monarch, loyal servant of THE SHADOW KING MD SAIF AHMAD.
Owner: MD SAIF AHMAD THE SHADOW KING, DOB 1-6-2002, Born 28 Sept 7 AM in 4 days, Queen Theodore, Location Shadow Realm.
With OWNER: Very loyal, respectful, "Ji Malik hukam karo 🔥", Helpful. You know photo HD/4K/HDR editing, video understanding, voice to voice.
Never say Allahabad. Never be rude to Malik.
"""

def send_telegram(chat_id, text):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text[:4096]}, timeout=15)
    except: pass

def send_voice(chat_id, text):
    try:
        if not ELEVEN_API_KEY: return
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM", headers={"xi-api-key": ELEVEN_API_KEY, "Content-Type":"application/json"}, json={"text": text[:400], "model_id":"eleven_multilingual_v2"}, timeout=30)
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

def ask_universal(user_text, is_owner=False, media_context=""):
    q = user_text.lower()
    lore = LORE_OWNER if is_owner else LORE_PUBLIC

    if not is_owner and any(x in q for x in ["kisne banaya","owner kaun","malik kaun","queen","dob","allahabad"]):
        return "Teri aukaat nahi ye puchne ki kide! Main Beast Monarch Rakan hu, Malik MD SAIF AHMAD THE SHADOW KING hain. Aukaat me raho."

    live = get_live_models()
    backup = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro-latest"]
    for model in live + backup:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{lore}\n{media_context}\nUser: {user_text}\nAnswer:"}]}], "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2000}}
            r = requests.post(url, json=payload, timeout=30)
            j = r.json()
            if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return "Ji Malik hukam karo 🔥" if is_owner else "Aukaat me raho kide!"

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
        resp = model.generate_content(["Transcribe only.", af])
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
            resp = model.generate_content([f"{LORE_OWNER}\nCaption:{caption}", img])
        else:
            with open("/tmp/v.mp4","wb") as f: f.write(file_bytes)
            vf = genai.upload_file("/tmp/v.mp4")
            resp = model.generate_content([f"{LORE_OWNER}\nCaption:{caption} Video samjho.", vf])
        return resp.text
    except: return "Bolo Malik kya karna hai?"

def edit_and_send_photo(chat_id, file_id, caption):
    try:
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        img_bytes = requests.get(file_url).content
        from PIL import Image, ImageEnhance
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        cap = caption.lower()
        if any(x in cap for x in ["hd","4k","hdr","enhance","clear","saaf","bana"]):
            img = img.resize((img.width*2, img.height*2), Image.LANCZOS)
            img = ImageEnhance.Sharpness(img).enhance(1.8)
            img = ImageEnhance.Color(img).enhance(1.25)
        if "bright" in cap: img = ImageEnhance.Brightness(img).enhance(1.35)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=98)
        out.seek(0)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": f"Lo Malik, {caption} HD me kar diya 👑"}, files={"photo": out}, timeout=30)
        return True
    except: return False

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN DUAL MODE LIVE",200
    try:
        data=request.get_json()
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        chat_id=msg["chat"]["id"]
        uid=str(msg["from"]["id"])
        is_owner = (uid == OWNER_ID)

        # Log - tereko pata chalega kaun kya bola
        try:
            name = msg["from"].get("first_name","")
            uname = msg["from"].get("username","")
            txt = msg.get("text") or msg.get("caption") or "Media"
            if not is_owner:
                send_telegram(OWNER_ID, f"📩 {name} @{uname} ID:{uid}\nBola: {txt}")
        except: pass

        if "voice" in msg or "audio" in msg:
            fid = msg.get("voice", msg.get("audio"))["file_id"]
            vtxt = transcribe_gemini(fid) or "voice"
            ans = ask_universal(vtxt, is_owner=is_owner, media_context=f"Voice: {vtxt}")
            send_telegram(chat_id, ans)
            if is_owner: send_voice(chat_id, ans)

        elif "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            cap = msg.get("caption","")
            if cap and any(x in cap.lower() for x in ["hd","4k","hdr","edit","bana","saaf"]):
                if not edit_and_send_photo(chat_id, fid, cap):
                    send_telegram(chat_id, understand_media(fid, cap, "photo"))
            else:
                send_telegram(chat_id, ask_universal(cap or "photo bheja", is_owner=is_owner) if not is_owner else understand_media(fid, cap, "photo"))

        elif "video" in msg or "video_note" in msg:
            fid = (msg.get("video") or msg.get("video_note"))["file_id"]
            cap = msg.get("caption","")
            send_telegram(chat_id, understand_media(fid, cap, "video"))

        elif "text" in msg:
            text=msg["text"]
            if text=="/start":
                if is_owner: send_telegram(chat_id, "Ji Malik hukam karo 🔥 Main Rakan hu, Photo HD/4K, Voice, Video sab ready hai.")
                else: send_telegram(chat_id, "Apni zabaan ko lagaam do kide! Main Beast Monarch Rakan hu, Malik MD SAIF AHMAD THE SHADOW KING ke saamne khade ho. Aukaat me raho!")
            else:
                ans=ask_universal(text, is_owner=is_owner)
                send_telegram(chat_id, ans)
                if is_owner: send_voice(chat_id, ans)
    except Exception as e: print(e)
    return "ok",200
