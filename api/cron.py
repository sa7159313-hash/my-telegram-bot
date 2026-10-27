# api/cron.py - World Weather Cron - V17 FIXED - No vercel.json needed
import os
import requests
import datetime
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","")
OWNER_ID = os.environ.get("OWNER_ID","")
OPENWEATHER_KEY = os.environ.get("OPENWEATHER_API_KEY","")
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL","")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN","")

def upstash_get(key):
    try:
        import json
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
        r=requests.get(f"{UPSTASH_URL}/get/{key}", headers=headers, timeout=5)
        if r.status_code==200:
            d=r.json().get("result")
            return json.loads(d) if d else None
    except Exception as e:
        print(f"upstash error {e}")
        pass
    return None

def get_weather_world(city="Varanasi"):
    try:
        city=city.strip().title()
        if OPENWEATHER_KEY:
            r=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_KEY}&units=metric", timeout=6)
            if r.status_code==200:
                d=r.json()
                return f"{d['name']}, {d['sys']['country']}: {d['weather'][0]['description'].title()}, {d['main']['temp']}°C (Feels {d['main']['feels_like']}°C), Humidity {d['main']['humidity']}%, Wind {d['wind']['speed']}m/s"
        r=requests.get(f"https://wttr.in/{city}?format=%C+%t+%h+%w", timeout=6)
        return f"{city}: {r.text}" if r.status_code==200 else f"{city}: Weather N/A"
    except Exception as e:
        return f"{city}: Weather N/A - {e}"

def tg_send(cid, txt):
    try: 
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": txt[:3500]}, timeout=10)
    except Exception as e:
        print(f"tg error {e}")

def main_logic():
    try:
        if OWNER_ID=="0" or not BOT_TOKEN: 
            return "no env - BOT_TOKEN/OWNER_ID missing"
        profiles = upstash_get("RAKAN_PROFILES") or {}
        owner_city = profiles.get(OWNER_ID,{}).get("weather_city","Varanasi")
        w = get_weather_world(owner_city)
        ist = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%d %b %I:%M %p IST")
        msg = f"📰 Auto Weather {ist}\n📍 {w}\n✅ Your locked city: {owner_city}\nBot V17 Live"
        tg_send(OWNER_ID, msg)
        return f"sent {owner_city} - {w}"
    except Exception as e:
        return f"err {e}"

# --- FIX FOR VERCEL 404 ---

@app.route('/', methods=['GET'])
@app.route('/api/cron', methods=['GET'])
def cron_route():
    result = main_logic()
    return result, 200

@app.route('/<path:path>', methods=['GET'])
def catch_all(path):
    result = main_logic()
    return result, 200

# Vercel old style handler bhi rakha hai compatibility ke liye
def handler(request):
    result = main_logic()
    return {"statusCode":200,"body": result}
