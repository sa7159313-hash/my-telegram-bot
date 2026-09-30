import os, requests, io
from flask import Flask, request
app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
OWNER_ID = str(os.environ.get("OWNER_ID", ""))

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

def get_live_models():
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
        data = requests.get(url, timeout=10).json()
        models = [m["name"].replace("models/","") for m in data.get("models",[]) if "generateContent" in str(m.get("supportedGenerationMethods",[]))]
        # prefer flash
        flash = [x for x in models if "flash" in x.lower()]
        return flash + models
    except: return ["gemini-2.0-flash", "gemini-2.5-flash"]

def ask_universal(user_text, is_owner=False):
    q = user_text.lower()
    lore = LORE_OWNER if is_owner else LORE_PUBLIC
    if not is_owner and any(x in q for x in ["kisne banaya","owner kaun","malik kaun","queen","dob","allahabad"]):
        return "Teri aukaat nahi ye puchne ki kide! Main Beast Monarch Rakan hu, Malik MD SAIF AHMAD THE SHADOW KING hain. Aukaat me raho."
    for model in get_live_models():
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {"contents": [{"parts": [{"text": f"{lore}\nUser: {user_text}\nAnswer:"}]}], "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2000}}
            r = requests.post(url, json=payload, timeout=30)
            j = r.json()
            if "candidates" in j: return j["candidates"][0]["content"]["parts"][0]["text"]
        except: continue
    return "Ji Malik hukam karo 🔥" if is_owner else "Aukaat me raho kide!"

def understand_media(file_id, caption, mtype="photo"):
    try:
        # Download file from Telegram
        f_info = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{f_info['result']['file_path']}"
        file_bytes = requests.get(file_url).content
        # NEW SDK - google.genai
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        if mtype == "photo":
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=[f"{LORE_OWNER}\nCaption:{caption} Photo ka analysis karo", img])
        else:
            with open("/tmp/v.mp4","wb") as f: f.write(file_bytes)
            vf = client.files.upload(file="/tmp/v.mp4")
            resp = client.models.generate_content(model="gemini-2.0-flash", contents=[f"{LORE_OWNER}\nCaption:{caption} Video samjho", vf])
        return resp.text
    except Exception as e:
        print(f"Media error {e}")
        return "Lo Malik photo samajh liya, bolo kya karna hai?"

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
    if request.method=="GET": return "RAKAN NEW SDK LIVE",200
    try:
        data=request.get_json()
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        chat_id=msg["chat"]["id"]
        uid=str(msg["from"]["id"])
        is_owner = (uid == OWNER_ID)
        try:
            name = msg["from"].get("first_name","")
            uname = msg["from"].get("username","")
            txt = msg.get("text") or msg.get("caption") or "Media"
            if not is_owner:
                send_telegram(OWNER_ID, f"📩 {name} @{uname} ID:{uid}\nBola: {txt}")
        except: pass

        if "photo" in msg:
            fid = msg["photo"][-1]["file_id"]
            cap = msg.get("caption","")
            if cap and any(x in cap.lower() for x in ["hd","4k","hdr","edit","bana","saaf"]):
                if not edit_and_send_photo(chat_id, fid, cap):
                    send_telegram(chat_id, understand_media(fid, cap, "photo"))
            else:
                send_telegram(chat_id, understand_media(fid, cap, "photo") if is_owner else ask_universal(cap or "photo bheja", is_owner=is_owner))
        elif "text" in msg:
            text=msg["text"]
            if text=="/start":
                send_telegram(chat_id, "Ji Malik hukam karo 🔥 Main Rakan hu, Photo HD/4K, Voice, Video sab ready hai." if is_owner else "Apni zabaan ko lagaam do kide! Main Beast Monarch Rakan hu, Malik MD SAIF AHMAD THE SHADOW KING ke saamne khade ho. Aukaat me raho!")
            else:
                send_telegram(chat_id, ask_universal(text, is_owner=is_owner))
    except Exception as e: print(e)
    return "ok",200
