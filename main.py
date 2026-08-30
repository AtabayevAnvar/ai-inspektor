"""
Avto AI — O'zbekiston Yo'l harakati qoidalari bo'yicha aqlli maslahatchi
FastAPI + RAG Search Engine + Google Gemini API (Tezkor va Limitlarsiz)
"""
import os
import base64
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, File, UploadFile, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import google.generativeai as genai

from rules_engine import RulesKnowledgeBase

# ─── Konfiguratsiya ───────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

BASE_DIR = Path(__file__).resolve().parent

# ─── Bilimlar bazasini yuklash ────────────────────────────────────
RULES_KB = RulesKnowledgeBase(str(BASE_DIR / "qoidalar.txt"))

# ─── Modellarni sinash tartibi ────────────────────────────────────
CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
    "gemini-3.7-flash"
]

def build_prompt(user_query: str, relevant_rules: str) -> str:
    return f"""Sen — O'zbekiston Respublikasi Yo'l harakati qoidalari (YHQ) bo'yicha yuqori malakali avto-instruktor va yo'l harakati xavfsizligi bo'yicha mutaxassissan.

Sening vazifang — foydalanuvchining savolini tahlil qilib, quyida keltirilgan tegishli YHQ bandlariga tayangan holda professional va tushunarli javob berish.

MUHIM QOIDALAR:
1. BARCHA JAVOBLARNI FAQAT O'ZBEK LOTIN ALIFBOSIDA BERISH SHART!
2. Shunchaki bandlarni ko'chirib bermasdan, foydalanuvchining vaziyatini tahlil qil va amaliy maslahat ber.
3. Qaysi bandga asoslanganingni ko'rsat (masalan: "YHQning 78-bandiga ko'ra...").
4. Javobni chiroyli formatda, bandma-band ber.

TEGISHLI YHQ QOIDALARI:
---
{relevant_rules}
---

Foydalanuvchi savoli: {user_query}
"""

def generate_ai_response(user_query: str, image_part=None) -> str:
    """RAG + Gemini orqali tezkor va kvotasiz javob olish"""
    # 1. Savolga mos bandlarni qidirish
    relevant_rules = RULES_KB.search(user_query, top_k=6)
    prompt_text = build_prompt(user_query, relevant_rules)

    contents = []
    if image_part:
        contents.append(image_part)
    contents.append(prompt_text)

    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            m = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=3000,
                )
            )
            res = m.generate_content(contents)
            if res and res.text:
                return res.text
        except Exception as e:
            print(f"[Model fallback] {model_name} error: {e}")
            last_error = e
            continue

    if last_error:
        raise last_error
    return "Javob hosil qilishda muammo yuz berdi."


# ─── FastAPI ilovasi ──────────────────────────────────────────────
app = FastAPI(title="Inspektor AI — YHQ Maslahatchi")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/icon", StaticFiles(directory=str(BASE_DIR / "icon")), name="icon")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    reply: str


# ─── Endpointlar ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Asosiy sahifa"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Faqat matnli savol"""
    user_message = req.message.strip()
    if not user_message:
        return ChatResponse(reply="Iltimos, savol yozing.")

    try:
        reply = generate_ai_response(user_message)
        return ChatResponse(reply=reply)
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "ResourceExhausted" in err_msg:
            return ChatResponse(
                reply="⚠️ Google AI bepul tarifi daqiqalik limiti to'ldi. Iltimos, 15-20 soniya kuting va qaytadan yuboring."
            )
        return ChatResponse(reply=f"Xatolik: {type(e).__name__} - {str(e)}")


@app.post("/api/chat-image")
async def chat_with_image(
    message: str = Form(...),
    session_id: str = Form("default"),
    image: UploadFile = File(...)
):
    """Rasm + Matnli savol"""
    user_message = message.strip()
    if not user_message:
        user_message = "Ushbu yo'l rasmini YHQ qoidalari bo'yicha tahlil qiling."

    try:
        image_bytes = await image.read()
        image_mime = image.content_type or "image/jpeg"

        image_part = {
            "inline_data": {
                "mime_type": image_mime,
                "data": base64.b64encode(image_bytes).decode("utf-8")
            }
        }

        reply = generate_ai_response(user_message, image_part=image_part)
        return {"reply": reply}

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "ResourceExhausted" in err_msg:
            return {"reply": "⚠️ Rasm tahlili limiti biroz to'ldi. Iltimos, 15-20 soniyadan so'ng qayta urinib ko'ring."}
        return {"reply": f"Rasm tahlilida xatolik: {type(e).__name__} - {str(e)}"}


@app.post("/api/clear")
async def clear_history():
    return {"status": "ok"}


# ─── Serverni ishga tushirish ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n[*] Avto AI -- YHQ Maslahatchi ishga tushdi!")
    print("[*] Brauzerda oching: http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
