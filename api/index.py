import os, requests, base64, json, time, random
from flask import Flask, request
app = Flask(__name__)
application = app

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
OWNER_ID = os.environ.get("OWNER_ID", "8303670838").strip()
REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
ELEVEN_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"

# --- PERSISTENT MEMORY (REDIS) - KABHI NAHI BHULEGA ---
def redis_get(key):
    if not REDIS_URL: return None
    try:
        r = requests.post(f"{REDIS_URL}/get/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, timeout=5)
        j = r.json()
        if j.get("result"):
            return json.loads(j["result"])
    except: pass
    return None

def redis_set(key, val):
    if not REDIS_URL: return
    try:
        requests.post(f"{REDIS_URL}/set/{key}", headers={"Authorization": f"Bearer {REDIS_TOKEN}"}, json=val, timeout=5)
    except: pass

RAM_MEMORY = {}
def load_json(p,d):
    # Pehle Redis se try
    rd = redis_get(p)
    if rd: RAM_MEMORY[p]=rd; return rd
    if p in RAM_MEMORY: return RAM_MEMORY[p]
    try:
        if os.path.exists(p):
            with open(p,'r') as f: data=json.load(f); RAM_MEMORY[p]=data; return data
    except: pass
    return d

def save_json(p,d):
    RAM_MEMORY[p]=d
    redis_set(p, d) # Redis me permanent save
    try:
        with open(p,'w') as f: json.dump(f,d)
    except: pass

MEMORY_FILE = "rakan_memory"
LEARN_FILE = "rakan_learnings"

def send_telegram(cid,txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":cid,"text":txt[:4096]}, timeout=8)
    except: pass

def send_voice_telegram(cid, text):
    if not ELEVENLABS_API_KEY: send_telegram(cid, text); return
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {"text": text[:400], "model_id": "eleven_multilingual_v2"}
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            files = {'voice': ('voice.mp3', r.content, 'audio/mpeg')}
            data = {'chat_id': cid, 'caption': text[:200]}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice", data=data, files=files, timeout=20)
        else:
            print(f"ELEVEN ERR {r.text[:100]}")
            send_telegram(cid, text)
    except Exception as e:
        print(f"VOICE FAIL {e}")
        send_telegram(cid, text)

def get_file_b64(fid):
    try:
        info=requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={fid}",timeout=8).json()
        path=info["result"]["file_path"]
        url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{path}"
        return base64.b64encode(requests.get(url,timeout=10).content).decode('utf-8')
    except: return None

def ask_gemini(prompt,b64=None,mime="image/jpeg"):
    for model in ["gemini-2.0-flash", "gemini-flash-latest"]:
        try:
            url=f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={GEMINI_API_KEY}"
            parts=[{"text":prompt}]
            if b64: parts.append({"inline_data":{"mime_type":mime,"data":b64}})
            payload={"contents":[{"parts":parts}],"generationConfig":{"temperature":0.9,"maxOutputTokens":800}}
            r=requests.post(url,json=payload,timeout=12)
            j=r.json()
            if "error" in j: print(f"GEMINI ERR {model}: {j['error'].get('message')[:150]}"); continue
            if "candidates" in j: print(f"GEMINI OK {model}"); return j["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e: print(f"FAIL {model} {e}"); continue
    return None

def get_reply(text,cid,b64=None,mime="image/jpeg",ftype="text"):
    q=text.lower().strip(); cid_str=str(cid).strip(); is_owner=(cid_str==OWNER_ID)
    mem=load_json(MEMORY_FILE,{}); raw=mem.get(cid_str,{}); history=raw.get("history",[])[-4:]; last_intro=raw.get("last_intro",0); told=raw.get("told_name",False)
    learn=load_json(LEARN_FILE,{"teachings":[]})

    if is_owner and "yaad rakh" in q:
        orig=text.split("yaad rakh")[-1].strip(" :")
        if len(orig)>2:
            learn["teachings"].append(orig); save_json(LEARN_FILE,learn)
            return f"Yaad rakh liya Malik, kabhi nahi bhulunga 👑: '{orig}'"

    if any(k in q for k in ["tu kaun","who are you","kisne banaya"]):
        if not told:
            mem[cid_str]={"history":history,"last_intro":last_intro,"told_name":True}; save_json(MEMORY_FILE,mem)
            return "I am Rakan, The King of Beast Monarch 👑 - Made by THE SHADOW KING (MD SAIF AHMAD)"
        return "Rakan hu Malik, bolo? 👑"

    prompt=f"You are Rakan, King of Beast Monarch. Malik: THE SHADOW KING. Teach:{learn.get('teachings',[])[-5:]} Hist:{history} User:{text} Reply short hinglish fresh no echo:"
    ans=ask_gemini(prompt,b64,mime)

    if ans: final=ans
    else:
        fallbacks = ["Haan Malik bolo na? 👑","Sun raha hu Malik 👑","Bolo Malik kya kaam hai? 👑","Ji Malik hukum do? 👑"] if is_owner else ["Haan bolo?","Bolo?"]
        final = random.choice([f for f in fallbacks if f!= (history[-1]["r"] if history else "")] or fallbacks)

    mem[cid_str]={"history":(history+[{"u":text[:80],"r":final[:80]}])[-6:], "last_intro":last_intro, "told_name":told}; save_json(MEMORY_FILE,mem)
    return final

@app.route("/",methods=["GET","POST"])
@app.route("/api/index",methods=["GET","POST"])
def index():
    if request.method=="GET": return "RAKAN V34 NEVER FORGET + ELEVENLABS",200
    try:
        data=request.get_json(force=True,silent=True)
        if not data or "message" not in data: return "ok",200
        msg=data["message"]; cid=str(msg["chat"]["id"]).strip(); txt=msg.get("text","") or msg.get("caption","") or ""
        is_voice = "voice" in msg or "audio" in msg
        if "photo" in msg:
            b64=get_file_b64(msg["photo"][-1]["file_id"]); send_telegram(cid,get_reply(txt or "photo",cid,b64,"image/jpeg","photo")); return "ok",200
        if is_voice:
            b64=get_file_b64(msg.get("voice",msg.get("audio",{})).get("file_id")); send_voice_telegram(cid,get_reply(txt or "voice",cid,b64,"audio/ogg","voice")); return "ok",200
        if txt:
            if txt.startswith("/start"):
                mem=load_json(MEMORY_FILE,{}); raw=mem.get(cid,{}); last=raw.get("last_intro",0) if isinstance(raw,dict) else 0
                if time.time()-last>86400:
                    w="Welcome to your world Shadow King 👑" if cid==OWNER_ID else "Welcome to my world. I am Rakan. 👑"
                    send_telegram(cid,w); mem[cid]={"history":[],"last_intro":time.time(),"told_name":False}; save_json(MEMORY_FILE,mem)
                else:
                    if time.time()-last<600: return "ok",200
                    send_telegram(cid,"Bolo Malik? 👑"); raw["last_intro"]=time.time(); mem[cid]=raw; save_json(MEMORY_FILE,mem)
            else:
                reply=get_reply(txt,cid)
                if any(k in txt.lower() for k in ["voice me","bol ke","suna"]): send_voice_telegram(cid, reply)
                else: send_telegram(cid, reply)
    except Exception as e: print(f"CRASH {e}")
    return "ok",200
