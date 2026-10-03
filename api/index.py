def get_ai_reply(prompt):
    # 1. GROQ - Naya Model jo 100% chalega
    try:
        if client_groq:
            r = client_groq.chat.completions.create(
                model="llama-3.1-8b-instant", # <-- YE CHANGE KIYA HAI
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
    except Exception as e:
        print(f"Groq fail: {e}")
        # Agar ye bhi fail ho to dusra model try karo
        try:
            r = client_groq.chat.completions.create(
                model="llama3-8b-8192",
                messages=[{"role":"user","content":prompt}]
            )
            return r.choices[0].message.content
        except Exception as e2:
            print(f"Groq 2nd fail: {e2}")

    # 2. Gemini Backup
    try:
        if client_gemini:
            r = client_gemini.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            return r.text
    except Exception as e:
        return f"Error: {e}"
