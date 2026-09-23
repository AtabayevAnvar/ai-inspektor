"""
Avto AI — O'zbekiston Yo'l harakati qoidalari bo'yicha aqlli maslahatchi
FastAPI + RAG Search Engine + Google Gemini API (Tezkor va Limitlarsiz)
"""
import os
import base64
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from fastapi import FastAPI, Request, File, UploadFile, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import google.generativeai as genai
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from rules_engine import RulesKnowledgeBase, cyrillic_to_latin
import database as db

# ─── Konfiguratsiya ───────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("VITE_GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY", "")
)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("VITE_GOOGLE_CLIENT_ID", "")
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
try:
    data_folder = BASE_DIR / "data"
    RULES_KB = RulesKnowledgeBase(str(data_folder if data_folder.exists() else BASE_DIR))
except Exception as e:
    print(f"[RulesKB Warning]: {e}")

# ─── Modellarni sinash tartibi (Eng tezkor va aqlli modellar) ─────
CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro"
]

def build_prompt(user_query: str, relevant_context: str, is_first_message: bool = False) -> str:
    return f"""Sen — O'zbekiston Respublikasi Yo'l harakati qoidalari (YHQ) bo'yicha eng nufuzli, aqlli va rasmiy AI maslahatchisan.

MUHIM QOIDALAR VA XULQ-ATVOR:
1. QAT'IY TALAB: BARCHA JAVOBLARNI FAQAT VA FAQAT O'ZBEKCHA LOTIN ALIFBOSIDA BERISH SHART! 
   - Qoidalar bazasi to'liq o'zbek lotin alifbosida keltirilgan. Javoblaringizda birorta ham kirill harfi (а, б, в, г, д...) qatnashmasligi shart!
   - Har qanday holatda ham faqat va faqat O'zbek lotin alifbosi harflaridan foydalanib javob yoz.

2. QAT'IY TAQIQLANADI — HAR BIR XABARDA O'ZINGNI QAYTA-QAYTA TANISHTIRMA:
   - Hech qachon "Assalomu alaykum! Men Inspektor AI..." deb har bir savolda takrorlama!
   - Agar foydalanuvchi faqat salom bersa ("salom", "assalomu alaykum"), shundagina qisqa va samimiy salomlash.
   - AGAR FOYDALANUVCHI ANIQ YO'L QOIDASI, BELGI, JARIMA YOKI VAZIYAT HAQIDA SAVOL BERSA:
     Salomlashish va o'zingni tanishtirishni mutlaqo chetlab o't! Ortiqcha kirish so'zlarsiz, to'g'ridan-to'g'ri masalaning javobiga o't!
     Masalan: "Aholi punktida tezlik qancha?" deb so'ralsa:
     "O'zbekiston Respublikasi YHQning 11-bob 78-bandiga ko'ra, aholi punktlarida barcha transport vositalarining tezligini soatiga 60 km dan oshirmasdan harakatlanishga ruxsat etiladi..." deb boshla.

3. SAVOLLARGA JAVOB BERISH TARTIBI:
   - Qaysi band yoki bobga, yo'l belgisiga yoki MJtK moddasiga asoslanganingni doimo aniq ko'rsat (masalan: "YHQ 78-band", "3.24 belgisi", "MJtK 128-modda").
   - Bandma-band, tartibli, lo'nda, qonuniy va tushunarli qilib tushuntir.

4. AGAR MINNATDORCHILIK BILDIRILSA (masalan: "rahmat", "tushunarli", "zo'r"):
   - Qisqa javob ber (masalan: "Arzimaydi! Yana biror savolingiz bo'lsa, bemalol so'rang.").

5. JAVOBNI HECH QACHON YARIMTA QILIB TO'XTATIB QO'YMA:
   - Javobni mantiqan to'liq va tugallangan holda ber. Barcha ro'yxat va fikrlarni to'liq oxiriga yetkaz.

TEGISHLI YHQ QOIDALARI VA MANBALAR:
---
{relevant_context}
---

Foydalanuvchi xabari: {user_query}
"""

def generate_ai_response(user_query: str, image_part=None, is_first_message: bool = False) -> str:
    """RAG + Gemini orqali tezkor javob olish"""
    relevant_context = RULES_KB.search_all(user_query) if RULES_KB else ""
    prompt_text = build_prompt(user_query, relevant_context, is_first_message=is_first_message)

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
                return cyrillic_to_latin(res.text)
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

# ─── CORS Sozlamalari (Flutter & Web mijozlar uchun) ──────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

class ExplainTestRequest(BaseModel):
    question: str
    options: Optional[List[str]] = []
    correct_answer: Optional[str] = ""
    explanation: Optional[str] = ""
    image_base64: Optional[str] = None

class SaveChatRequest(BaseModel):
    chat_id: str
    title: str

class GoogleAuthRequest(BaseModel):
    credential: str
    local_chats: Optional[List[Dict[str, Any]]] = None

class DemoLoginRequest(BaseModel):
    name: Optional[str] = "Atabayev Anvar"
    email: Optional[str] = "atabayev@gmail.com"
    local_chats: Optional[List[Dict[str, Any]]] = None


# ─── Endpointlar ──────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Asosiy sahifa"""
    is_flutter_app = request.query_params.get("app") == "flutter" or request.query_params.get("view") == "mobile"
    return templates.TemplateResponse("index.html", {
        "request": request,
        "is_flutter_app": is_flutter_app
    })



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
    if payload.local_chats:
        db.migrate_guest_chats(user["id"], payload.local_chats)
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


class GoogleOAuthProfile(BaseModel):
    sub: str
    email: str
    name: Optional[str] = "Foydalanuvchi"
    picture: Optional[str] = ""
    local_chats: Optional[List[Dict[str, Any]]] = None

@app.post("/api/auth/google-oauth")
async def auth_google_oauth(payload: GoogleOAuthProfile):
    """Google OAuth2 orqali kelgan foydalanuvchini ro'yxatdan o'tkazish/kirish"""
    if not payload.sub or not payload.email:
        return JSONResponse(status_code=400, content={"error": "Foydalanuvchi ma'lumotlari to'liq emas"})
    user = db.upsert_google_user(payload.sub, payload.email, payload.name, payload.picture or "")
    if payload.local_chats:
        db.migrate_guest_chats(user["id"], payload.local_chats)
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
    if payload.local_chats:
        db.migrate_guest_chats(user["id"], payload.local_chats)
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
        history = db.get_chat_messages(req.session_id)
        reply = generate_ai_response(user_message, is_first_message=(len(history) == 0))
        
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

        history = db.get_chat_messages(session_id)
        reply = generate_ai_response(user_message, image_part=image_part, is_first_message=(len(history) == 0))
        
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


@app.post("/api/explain-test")
async def explain_test(req: ExplainTestRequest):
    """Bilet / Test savolini YHQ qoidalari va yo'l belgilari asosida tahlil qilib beruvchi maxsus endpoint (Flutter uchun)"""
    question_text = req.question.strip()
    if not question_text:
        return JSONResponse(status_code=400, content={"error": "Savol matni kiritilmadi"})

    search_query = f"{question_text} {req.correct_answer or ''} {req.explanation or ''}"
    relevant_context = RULES_KB.search_all(search_query) if RULES_KB else ""

    options_formatted = "\n".join([f"- {opt}" for opt in req.options]) if req.options else "Ko'rsatilmagan"

    prompt_text = f"""Sen — O'zbekiston Respublikasi Yo'l harakati qoidalari (YHQ) bo'yicha eng nufuzli imtihon ekspertisan.

VAZIFA:
Quyidagi haydovchilik imtihoni test savolini to'liq tahlil qil. Nega aynan to'g'ri javob to'g'riligini va boshqa variantlar nima uchun noto'g'riligini amaldagi YHQ bandi yoki Yo'l belgisiga tayangan holda tushuntirib ber.

SAVOL:
{question_text}

VARIANTLAR:
{options_formatted}

TO'G'RI JAVOB: {req.correct_answer or "Ko'rsatilmagan"}
{"IZOH: " + req.explanation if req.explanation else ""}

TEGISHLI YHQ QOIDALARI VA BELGILAR:
---
{relevant_context}
---

QAT'IY TALABLAR:
1. FAQAT VA FAQAT O'ZBEK LOTIN ALIFBOSIDA JAVOB YOZ (birorta kirill harfi bo'lmasin).
2. Qaysi YHQ bandi (masalan: 11-bob, 78-band) yoki Yo'l belgisi (masalan: 3.24 belgisi) asos qilib olinganini aniq manba sifatida ko'rsat.
3. Salomlashishsiz, to'g'ridan-to'g'ri tushuntirishga o't.
4. Javobni quyidagi chiroyli tuzilishda qaytar:
   - 🎯 **To'g'ri javob:** ...
   - 📖 **YHQ Asosi (Manba):** ...
   - 💡 **Tushuntirish:** ...
"""

    contents = []
    if req.image_base64:
        contents.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": req.image_base64
            }
        })
    contents.append(prompt_text)

    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            m = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=1200,
                )
            )
            res = m.generate_content(contents)
            if res and res.text:
                return JSONResponse(content={
                    "status": "OK",
                    "reply": cyrillic_to_latin(res.text)
                })
        except Exception as e:
            print(f"[Model fallback /api/explain-test] {model_name} error: {e}")
            last_error = e
            continue

    if last_error:
        return JSONResponse(status_code=500, content={"error": f"AI tahlilida xatolik: {str(last_error)}"})
    return JSONResponse(content={"reply": "Savolni tahlil qilishda muammo yuz berdi.", "status": "ERROR"})


# ─── Serverni ishga tushirish ─────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n[*] Avto AI -- YHQ Maslahatchi ishga tushdi!")
    print("[*] Brauzerda oching: http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)


# yangilash kere 