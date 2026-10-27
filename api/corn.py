# api/cron.py - World Weather Cron - No vercel.json needed
import os, requests, datetime

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
    except: pass
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
    except: return f"{city}: Weather N/A"

def tg_send(cid, txt):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": cid, "text": txt[:3500]}, timeout=10)
    except: pass

def handler(request):
    try:
        if OWNER_ID=="0" or not BOT_TOKEN: return {"statusCode":200,"body":"no env"}
        profiles = upstash_get("RAKAN_PROFILES") or {}
        owner_city = profiles.get(OWNER_ID,{}).get("weather_city","Varanasi")
        # Owner ko uski locked city ka weather
        w = get_weather_world(owner_city)
        ist = (datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)).strftime("%d %b %I:%M %p IST")
        msg = f"📰 Auto Weather {ist}\n📍 {w}\n✅ Your locked city: {owner_city}\nBot V17 Live"
        tg_send(OWNER_ID, msg)
        return {"statusCode":200,"body":f"sent {owner_city}"}
    except Exception as e:
        return {"statusCode":200,"body":f"err {e}"}
