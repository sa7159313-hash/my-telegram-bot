def get_ai_reply(prompt):
    # Groq ke saare purane working models
    MODELS = ["llama3-8b-8192", "llama3-70b-8192", "gemma2-9b-it", "mixtral-8x7b-32768"]

    for model_name in MODELS:
        try:
            if GROQ_KEY:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}]
                }
                r = requests.post(url, headers=headers, json=data, timeout=20)
                if r.status_code == 200:
                    print(f"Success with {model_name}")
                    return r.json()['choices'][0]['message']['content']
                else:
                    print(f"Groq {model_name} Error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"Groq {model_name} fail: {e}")

    # Agar Groq ke saare models fail to Gemini
    try:
        if GEMINI_KEY:
            from google import genai
            client = genai.Client(api_key=GEMINI_KEY)
            res = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return res.text
    except Exception as e:
        print(f"Gemini fail: {e}")

    return "Malik, Groq aur Gemini dono fail ho gaye. Key check karo."
