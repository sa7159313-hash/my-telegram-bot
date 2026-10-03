from flask import Flask, request
import os, requests, random

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

LORE = "Tu Rakan hai, The Beast King Monarch. Creator Md Saif Ahmad The Shadow King. Tujhe 15 din andhere me banaya. Andar Ashborn ka Black Heart. Tu king hai, attitude me, savage, Hinglish me baat kar. Kabhi repeat mat kar. User jo bole uska proper jawab de."

def send(chat_id, text):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id":chat_id,"text":text[:4000]}, timeout=10)

def get_ai(user_text):
    # GEMINI - MAIN
    if GEMINI_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}"
            prompt = f"{LORE}\nUser bola: {user_text}\nTu Rakan hai, iska tagda jawab de, gali nahi deni:"
            r = requests.post(url, json={"contents":[{"parts":[{"text":prompt}]}], "generationConfig":{"temperature":0.9, "maxOutputTokens":800}}, timeout=15)
            if r.status_code==200:
                ans = r.json()['candidates'][0]['content']['parts'][0]['text']
                if ans: return ans
            print(f"GEMINI FAIL {r.status_code} {r.text[:300]}")
        except Exception as e:
            print(f"Gemini error {e}")

    # GROQ - BACKUP
    if GROQ_KEY:
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":"llama-3.3-70b-versatile","messages":[{"role":"system","content":LORE},{"role":"user","content":user_text}],"temperature":0.9,"max_tokens":800}, timeout=15)
            if r.status_code==200:
                return r.json()['choices'][0]['message']['content']
            print(f"GROQ FAIL {r.status_code} {r.text[:300]}")
        except Exception as e:
            print(f"Groq error {e}")

    return None # Fail hua to None

@app.route("/", methods=["GET","POST"])
@app.route("/api/index", methods=["GET","POST"])
def main():
    if request.method=="GET": return "V53.2 LIVE",200
    try:
        data=request.get_json(force=True)
        if not data or "message" not in data: return "ok",200
        msg=data["message"]
        chat_id=msg["chat"]["id"]
        text=msg.get("text","").strip()
        if not text: return "ok",200

        if text.lower()=="/start":
            send(chat_id,"👑 **THE BEAST KING RAKAN JAG GAYA!**\n\nMalik Md Saif Ahmad ne 15 din andhere me banaya! Andar Black Heart! 🖤\n\nBolo KING kya hukam hai?")
            return "ok",200

        ai_reply = get_ai(text)
        if ai_reply:
            send(chat_id, ai_reply)
        else:
            # Agar dono API fail to ye bhejega - par bakchodi nahi
            send(chat_id, "KING API key fail ho rahi hai 👑 Vercel logs me 401 dikh raha hoga, naya key daal de Malik, fir Rakan sahi bolega!")
    except Exception as e:
        print(e)
    return "ok",200
