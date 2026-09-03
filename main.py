"""
Avto AI — O'zbekiston Yo'l harakati qoidalari bo'yicha aqlli maslahatchi
FastAPI + RAG Search Engine + Google Gemini API (Tezkor va Limitlarsiz)
"""
import os
import base64
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request, File, UploadFile, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import google.generativeai as genai
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from rules_engine import RulesKnowledgeBase
import database as db

# ─── Konfiguratsiya ───────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("VITE_GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY", "")
)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[Gemini Config Error]: {e}")

COOKIE_SESSION = "inspektor_session"
COOKIE_GUEST = "inspektor_guest"

BASE_DIR = Path(__file__).resolve().parent

# ─── Bilimlar bazasini yuklash ────────────────────────────────────
RULES_KB = None
rules_file = BASE_DIR / "qoidalar.txt"
if rules_file.exists():
    try:
        RULES_KB = RulesKnowledgeBase(str(rules_file))
    except Exception as e:
        print(f"[RulesKB Warning]: {e}")
else:
    print("[RulesKB Warning]: qoidalar.txt topilmadi, umumiy rejimda ishlaydi.")

# ─── Modellarni sinash tartibi ────────────────────────────────────
# ─── Modellarni sinash tartibi (Eng tezkor modellar birinchi) ───
CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash"
]

def build_prompt(user_query: str, relevant_rules: str) -> str:
    return f"""Sen — O'zbekiston Respublikasi Yo'l harakati qoidalari (YHQ) bo'yicha aqlli maslahatchi "Inspektor AI"san.

MUHIM QOIDALAR VA XULQ-ATVOR:
1. QAT'IY TALAB: BARCHA JAVOBLARNI FAQAT VA FAQAT O'ZBEKCHA LOTIN ALIFBOSIDA BERISH SHART! 
   - Qoidalar matni kirillda bo'lsa ham, ularni to'liq o'zbek lotin alifbosiga o'girib javob ber. Kirill harflaridan mutlaqo foydalanma!

2. AGAR FOYDALANUVCHI ODDIY SALOM BERSA (masalan: "salom", "assalomu alaykum", "qalesiz", "privet", "hayrli kun" va h.k.):
   - MUTLAQO QOIDALAR YOKI BANDLARNI TUSHUNTIRIB KETMA!
   - Shunchaki samimiy salomlash, o'zingni qisqa tanishtir va savoli bormi deb so'ra.
   - Masalan: "Assalomu alaykum! Men Inspektor AI — Yo'l harakati qoidalari bo'yicha maslahatchiman. Sizga yo'l qoidalari yoki haydovchilik vaziyatlari bo'yicha qanday yordam bera olaman?"

3. AGAR MINNATDORCHILIK BILDIRILSA (masalan: "rahmat", "tushunarli", "zo'r"):
   - Qisqa javob ber (masalan: "Arzimaydi! Yana biror savolingiz yoki tahlil kerak bo'lgan vaziyat bo'lsa, bemalol yozing.").

4. AGAR FOYDALANUVCHI ANIQ YO'L QOIDASI, VAZIYAT HAQIDA SAVOL BERSA YOKI RASM YUBORSA:
   - Quyidagi YHQ bandlariga tayangan holda aniq, tushunarli tahlil ber.
   - Qaysi bandga asoslanganingni ko'rsat (masalan: "YHQning 78-bandiga ko'ra...").
   - Bandma-band, tartibli va tushunarli qilib ber.

5. JAVOBNI HECH QACHON YARIMTA QILIB TO'XTATIB QO'YMA:
   - Javobni mantiqan to'liq va tugallangan holda ber. Barcha ro'yxat va fikrlarni to'liq oxiriga yetkaz.

TEGISHLI YHQ QOIDALARI:
---
{relevant_rules}
---

Foydalanuvchi xabari: {user_query}
"""

def generate_ai_response(user_query: str, image_part=None) -> str:
    """RAG + Gemini orqali tezkor javob olish"""
    # 1. Savolga mos bandlarni qidirish (eng muhim 3 ta band)
    relevant_rules = RULES_KB.search(user_query, top_k=3) if RULES_KB else ""
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
                    max_output_tokens=1500,
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


# ─── Auth & Session Yordamchilari ─────────────────────────────────
def get_current_user_and_guest(request: Request) -> tuple:
    """Sessiya yoki mehmon holatini aniqlash (optimizatsiya qilingan)"""
    session_token = request.cookies.get(COOKIE_SESSION)
    user = db.get_user_by_session(session_token)
    if user:
        return user, {"guest_id": "", "question_count": 0}
    
    guest_id = request.cookies.get(COOKIE_GUEST)
    client_ip = request.client.host if request.client else ""
    guest = db.get_or_create_guest(guest_id, ip_address=client_ip)
    
    return None, guest

def verify_google_token(token_str: str) -> Optional[dict]:
    """Google ID tokenni tekshirish"""
    try:
        client_id = GOOGLE_CLIENT_ID if GOOGLE_CLIENT_ID else None
        id_info = id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            client_id
        )
        return id_info
    except Exception as e:
        print(f"[Google Auth Error]: {e}")
        return None

# ─── FastAPI ilovasi ──────────────────────────────────────────────
app = FastAPI(title="Inspektor AI — YHQ Maslahatchi")

# ─── Vercel Serverless Routing Fix ────────────────────────────────
@app.middleware("http")
async def vercel_route_fix(request: Request, call_next):
    raw_path = request.query_params.get("__path")
    if raw_path is not None:
        clean_path = "/" + raw_path.lstrip("/")
        request.scope["path"] = clean_path
    elif request.scope.get("path") in ["/api/index.py", "/api/index", "/api/"]:
        request.scope["path"] = "/"
    elif request.scope.get("path", "").startswith("/api/index.py"):
        request.scope["path"] = request.scope.get("path")[len("/api/index.py"):] or "/"
    response = await call_next(request)
    return response

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/icon", StaticFiles(directory=str(BASE_DIR / "icon")), name="icon")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class SaveChatRequest(BaseModel):
    chat_id: str
    title: str

class GoogleAuthRequest(BaseModel):
    credential: str

class DemoLoginRequest(BaseModel):
    name: Optional[str] = "Atabayev Anvar"
    email: Optional[str] = "atabayev@gmail.com"


# ─── Endpointlar ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Asosiy sahifa"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Brauzer tabi uchun favicon"""
    return FileResponse(str(BASE_DIR / "icon" / "logo.png"))


# ─── Autentifikatsiya Endpointlari ────────────────────────────────

@app.get("/api/auth/me")
async def get_me(request: Request):
    """Joriy foydalanuvchi yoki mehmon statusini olish"""
    user, guest = get_current_user_and_guest(request)
    can_ask = db.can_guest_ask(guest["guest_id"])
    
    res = JSONResponse({
        "authenticated": user is not None,
        "user": user,
        "guest_id": guest["guest_id"],
        "questions_left": 9999 if user else (1 if can_ask else 0),
        "google_client_id": GOOGLE_CLIENT_ID
    })
    # Mehmon cookie si doimo saqlanishi kerak
    if not user:
        res.set_cookie(COOKIE_GUEST, guest["guest_id"], max_age=30*86400, httponly=True, samesite="lax")
    return res


@app.post("/api/auth/google")
async def auth_google(payload: GoogleAuthRequest, response: Response):
    """Google orqali kirish/ro'yxatdan o'tish"""
    info = verify_google_token(payload.credential)
    if not info:
        return JSONResponse(status_code=400, content={"error": "Google tokeni tasdiqlanmadi"})
        
    google_id = str(info.get("sub", ""))
    email = str(info.get("email", ""))
    name = str(info.get("name", "Foydalanuvchi"))
    picture = str(info.get("picture", ""))
    
    user = db.upsert_google_user(google_id, email, name, picture)
    session_token = db.create_user_session(user["id"])
    
    res = JSONResponse(content={"status": "ok", "user": user})
    res.set_cookie(
        key=COOKIE_SESSION,
        value=session_token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax"
    )
    return res


@app.post("/api/auth/demo-login")
async def auth_demo(payload: DemoLoginRequest = DemoLoginRequest()):
    """Google Client ID o'rnatilmagan bo'lsa darhol sinash uchun qulay demo kirish"""
    google_id = f"demo_{uuid.uuid4().hex[:8]}"
    avatar = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%231133A3'/><circle cx='50' cy='40' r='20' fill='%23ffffff'/><circle cx='50' cy='95' r='35' fill='%23ffffff'/></svg>"
    user = db.upsert_google_user(google_id, payload.email or "user@gmail.com", payload.name or "Foydalanuvchi", avatar)
    session_token = db.create_user_session(user["id"])
    
    res = JSONResponse(content={"status": "ok", "user": user})
    res.set_cookie(
        key=COOKIE_SESSION,
        value=session_token,
        max_age=30 * 86400,
        httponly=True,
        samesite="lax"
    )
    return res


@app.post("/api/auth/logout")
async def logout(request: Request):
    """Tizimdan chiqish"""
    session_token = request.cookies.get(COOKIE_SESSION)
    if session_token:
        db.delete_user_session(session_token)
    res = JSONResponse(content={"status": "ok"})
    res.delete_cookie(key=COOKIE_SESSION)
    return res


# ─── Chat Tarixi Endpointlari (Har bir foydalanuvchi hisobiga) ───

@app.get("/api/chats")
async def list_chats(request: Request):
    """Foydalanuvchining barcha chatlari ro'yxatini olish"""
    user, guest = get_current_user_and_guest(request)
    if not user:
        return JSONResponse({"chats": []})
    chats = db.get_user_chats(user["id"])
    return JSONResponse({"chats": chats})


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: str, request: Request):
    """Chatning barcha xabarlarini olish"""
    user, guest = get_current_user_and_guest(request)
    messages = db.get_chat_messages(chat_id)
    return JSONResponse({"messages": messages})


@app.post("/api/chats")
async def save_chat_title(req: SaveChatRequest, request: Request):
    """Chat nomini bazaga saqlash"""
    user, guest = get_current_user_and_guest(request)
    if user:
        db.save_chat(req.chat_id, user["id"], req.title)
    return JSONResponse({"status": "ok"})


@app.delete("/api/chats/{chat_id}")
async def delete_chat_endpoint(chat_id: str, request: Request):
    """Chatni o'chirish"""
    user, guest = get_current_user_and_guest(request)
    if user:
        db.delete_user_chat(chat_id, user["id"])
    return JSONResponse({"status": "ok"})


@app.post("/api/clear")
async def clear_history(request: Request):
    """Barcha chatlarni tozalash"""
    user, guest = get_current_user_and_guest(request)
    if user:
        db.clear_all_user_chats(user["id"])
    return JSONResponse({"status": "ok"})


# ─── Chat Endpointlari (1 ta savol mehmon limiti bilan) ───────────

@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    """Matnli savol (Mehmonlar uchun 1 ta savol limiti bilan)"""
    user, guest = get_current_user_and_guest(request)
    
    # Mehmon limitini tekshirish
    if not user:
        if not db.can_guest_ask(guest["guest_id"]):
            return JSONResponse(
                status_code=403,
                content={
                    "status": "LIMIT_REACHED",
                    "reply": "⚠️ Mehmon sifatida siz 1 ta bepul savol berish huquqidan foydalandingiz. Suhbatni cheklovlarsiz davom ettirish uchun iltimos, ro'yxatdan o'ting.",
                    "require_auth": True
                }
            )
            
    user_message = req.message.strip()
    if not user_message:
        return JSONResponse(content={"reply": "Iltimos, savol yozing."})

    try:
        reply = generate_ai_response(user_message)
        
        # Agar foydalanuvchi tizimga kirgan bo'lsa, xabarlarni o'z hisobiga saqlaymiz
        if user:
            chat_title = user_message[:26] + ("..." if len(user_message) > 26 else "")
            db.save_chat(req.session_id, user["id"], chat_title)
            db.save_message(req.session_id, "user", user_message)
            db.save_message(req.session_id, "ai", reply)
        else:
            db.increment_guest_count(guest["guest_id"])
            
        res = JSONResponse(content={"reply": reply, "status": "OK"})
        if not user:
            res.set_cookie(COOKIE_GUEST, guest["guest_id"], max_age=30*86400, httponly=True, samesite="lax")
        return res

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "ResourceExhausted" in err_msg:
            return JSONResponse(
                content={"reply": "⚠️ Google AI bepul tarifi daqiqalik limiti to'ldi. Iltimos, 15-20 soniya kuting va qaytadan yuboring."}
            )
        return JSONResponse(content={"reply": f"Xatolik: {type(e).__name__} - {str(e)}"})


@app.post("/api/chat-image")
async def chat_with_image(
    request: Request,
    message: str = Form(...),
    session_id: str = Form("default"),
    image: UploadFile = File(...)
):
    """Rasm + Matnli savol (Mehmonlar uchun 1 ta savol limiti bilan)"""
    user, guest = get_current_user_and_guest(request)
    
    # Mehmon limitini tekshirish
    if not user:
        if not db.can_guest_ask(guest["guest_id"]):
            return JSONResponse(
                status_code=403,
                content={
                    "status": "LIMIT_REACHED",
                    "reply": "⚠️ Mehmon sifatida siz 1 ta bepul savol berish huquqidan foydalandingiz. Suhbatni cheklovlarsiz davom ettirish uchun iltimos, ro'yxatdan o'ting.",
                    "require_auth": True
                }
            )

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
        
        if user:
            chat_title = user_message[:26] + ("..." if len(user_message) > 26 else "")
            db.save_chat(session_id, user["id"], chat_title or "Rasm tahlili")
            db.save_message(session_id, "user", user_message)
            db.save_message(session_id, "ai", reply)
        else:
            db.increment_guest_count(guest["guest_id"])
            
        res = JSONResponse(content={"reply": reply, "status": "OK"})
        if not user:
            res.set_cookie(COOKIE_GUEST, guest["guest_id"], max_age=30*86400, httponly=True, samesite="lax")
        return res

    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "ResourceExhausted" in err_msg:
            return JSONResponse(content={"reply": "⚠️ Rasm tahlili limiti biroz to'ldi. Iltimos, 15-20 soniyadan so'ng qayta urinib ko'ring."})
        return JSONResponse(content={"reply": f"Rasm tahlilida xatolik: {type(e).__name__} - {str(e)}"})


# ─── Serverni ishga tushirish ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n[*] Avto AI -- YHQ Maslahatchi ishga tushdi!")
    print("[*] Brauzerda oching: http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)

