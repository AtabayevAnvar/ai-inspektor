"""
Avto AI — Database Module (Supabase Cloud PostgreSQL + SQLite Fallback)
Foydalanuvchilar, Google autentifikatsiyasi, sessiyalar, mehmon limiti va chatlar tarixi
"""
import os
import uuid
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase_client = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[Database] Supabase bulutli bazasiga ulanish sozlandi.")
    except Exception as e:
        print(f"[Database] Supabase ulanish xatosi: {e}")

# ─── SQLite Fallback ─────────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent / "avto_ai.db"

def get_sqlite_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_sqlite_db():
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE,
                email TEXT UNIQUE,
                name TEXT,
                avatar_url TEXT,
                plan TEXT DEFAULT 'PRO',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guest_sessions (
                guest_id TEXT PRIMARY KEY,
                question_count INTEGER DEFAULT 0,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                role TEXT,
                text TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

init_sqlite_db()

# ─── Foydalanuvchi Amallari ──────────────────────────────────────────

def upsert_google_user(google_id: str, email: str, name: str, avatar_url: str) -> Dict[str, Any]:
    if supabase_client:
        try:
            res = supabase_client.table("users").select("*").or_(f"google_id.eq.{google_id},email.eq.{email}").execute()
            if res.data and len(res.data) > 0:
                user = res.data[0]
                up = supabase_client.table("users").update({"name": name, "avatar_url": avatar_url, "google_id": google_id}).eq("id", user["id"]).execute()
                return up.data[0] if up.data else user
            else:
                ins = supabase_client.table("users").insert({
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "avatar_url": avatar_url,
                    "plan": "PRO"
                }).execute()
                if ins.data:
                    return ins.data[0]
        except Exception as e:
            print(f"[Supabase upsert_user fallback]: {e}")

    # SQLite Fallback
    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE google_id = ? OR email = ?", (google_id, email))
        user = cursor.fetchone()
        if user:
            cursor.execute("UPDATE users SET name = ?, avatar_url = ?, google_id = ? WHERE id = ?", (name, avatar_url, google_id, user["id"]))
            user_id = user["id"]
        else:
            cursor.execute("INSERT INTO users (google_id, email, name, avatar_url, plan) VALUES (?, ?, ?, ?, 'PRO')", (google_id, email, name, avatar_url))
            user_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(cursor.fetchone())

def create_user_session(user_id: Any) -> str:
    token = str(uuid.uuid4())
    if supabase_client:
        try:
            supabase_client.table("user_sessions").insert({"token": token, "user_id": user_id}).execute()
            return token
        except Exception as e:
            print(f"[Supabase create_session fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()
    return token

def get_user_by_session(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None

    if supabase_client:
        try:
            res = supabase_client.table("user_sessions").select("user_id").eq("token", token).execute()
            if res.data and len(res.data) > 0:
                uid = res.data[0]["user_id"]
                ures = supabase_client.table("users").select("*").eq("id", uid).execute()
                if ures.data and len(ures.data) > 0:
                    return ures.data[0]
        except Exception as e:
            print(f"[Supabase get_user fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.* FROM users u
            JOIN user_sessions s ON s.user_id = u.id
            WHERE s.token = ?
        """, (token,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_user_session(token: Optional[str]):
    if not token:
        return

    if supabase_client:
        try:
            supabase_client.table("user_sessions").delete().eq("token", token).execute()
        except Exception as e:
            print(f"[Supabase delete_session fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()

# ─── Mehmon Foydalanuvchi Amallari ───────────────────────────────────

def get_or_create_guest(guest_id: Optional[str], ip_address: Optional[str] = "") -> Dict[str, Any]:
    if supabase_client and guest_id:
        try:
            res = supabase_client.table("guest_sessions").select("*").eq("guest_id", guest_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"[Supabase get_guest fallback]: {e}")

    if supabase_client and not guest_id:
        try:
            new_id = str(uuid.uuid4())
            ins = supabase_client.table("guest_sessions").insert({"guest_id": new_id, "question_count": 0, "ip_address": ip_address}).execute()
            if ins.data:
                return ins.data[0]
        except Exception as e:
            print(f"[Supabase create_guest fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        if guest_id:
            cursor.execute("SELECT * FROM guest_sessions WHERE guest_id = ?", (guest_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)

        new_id = str(uuid.uuid4())
        cursor.execute("INSERT INTO guest_sessions (guest_id, question_count, ip_address) VALUES (?, 0, ?)", (new_id, ip_address))
        conn.commit()
        cursor.execute("SELECT * FROM guest_sessions WHERE guest_id = ?", (new_id,))
        return dict(cursor.fetchone())

def can_guest_ask(guest_id: str) -> bool:
    if supabase_client:
        try:
            res = supabase_client.table("guest_sessions").select("question_count").eq("guest_id", guest_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]["question_count"] < 1
        except Exception as e:
            print(f"[Supabase can_ask fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT question_count FROM guest_sessions WHERE guest_id = ?", (guest_id,))
        row = cursor.fetchone()
        if not row:
            return True
        return row["question_count"] < 1

def increment_guest_count(guest_id: str):
    if supabase_client:
        try:
            res = supabase_client.table("guest_sessions").select("question_count").eq("guest_id", guest_id).execute()
            count = res.data[0]["question_count"] + 1 if res.data else 1
            supabase_client.table("guest_sessions").update({"question_count": count}).eq("guest_id", guest_id).execute()
            return
        except Exception as e:
            print(f"[Supabase increment_guest fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE guest_sessions SET question_count = question_count + 1, updated_at = CURRENT_TIMESTAMP WHERE guest_id = ?", (guest_id,))
        conn.commit()

# ─── Chatlar va Xabarlar Tarixi (Har bir user hisobiga) ───────────────

def get_user_chats(user_id: Any) -> List[Dict[str, Any]]:
    """Foydalanuvchining barcha chatlari ro'yxatini olish"""
    if supabase_client:
        try:
            res = supabase_client.table("chats").select("*").eq("user_id", user_id).order("updated_at", desc=True).execute()
            if res.data is not None:
                return res.data
        except Exception as e:
            print(f"[Supabase get_chats fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chats WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
        return [dict(r) for r in cursor.fetchall()]

def save_chat(chat_id: str, user_id: Any, title: str) -> Dict[str, Any]:
    """Yangi chat yaratish yoki nomini yangilash"""
    if supabase_client:
        try:
            res = supabase_client.table("chats").upsert({
                "id": chat_id,
                "user_id": user_id,
                "title": title
            }).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"[Supabase save_chat fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chats (id, user_id, title) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET title = excluded.title, updated_at = CURRENT_TIMESTAMP
        """, (chat_id, user_id, title))
        conn.commit()
        cursor.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))
        return dict(cursor.fetchone())

def save_message(chat_id: str, role: str, text: str, image_url: Optional[str] = ""):
    """Xabarni chatga qo'shish"""
    if supabase_client:
        try:
            supabase_client.table("messages").insert({
                "chat_id": chat_id,
                "role": role,
                "text": text,
                "image_url": image_url or ""
            }).execute()
            # Chatning updated_at vaqtini yangilash
            supabase_client.table("chats").update({"updated_at": "now()"}).eq("id", chat_id).execute()
            return
        except Exception as e:
            print(f"[Supabase save_message fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (chat_id, role, text, image_url) VALUES (?, ?, ?, ?)", (chat_id, role, text, image_url))
        cursor.execute("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))
        conn.commit()

def get_chat_messages(chat_id: str) -> List[Dict[str, Any]]:
    """Chatning barcha xabarlarini tartib bilan olish"""
    if supabase_client:
        try:
            res = supabase_client.table("messages").select("*").eq("chat_id", chat_id).order("created_at", desc=False).execute()
            if res.data is not None:
                return res.data
        except Exception as e:
            print(f"[Supabase get_messages fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC", (chat_id,))
        return [dict(r) for r in cursor.fetchall()]

def delete_user_chat(chat_id: str, user_id: Any):
    """Chatni o'chirish"""
    if supabase_client:
        try:
            supabase_client.table("chats").delete().eq("id", chat_id).eq("user_id", user_id).execute()
            return
        except Exception as e:
            print(f"[Supabase delete_chat fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        cursor.execute("DELETE FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id))
        conn.commit()

def clear_all_user_chats(user_id: Any):
    """Foydalanuvchining barcha chatlarini tozalash"""
    if supabase_client:
        try:
            supabase_client.table("chats").delete().eq("user_id", user_id).execute()
            return
        except Exception as e:
            print(f"[Supabase clear_all fallback]: {e}")

    with get_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM chats WHERE user_id = ?", (user_id,))
        cids = [r["id"] for r in cursor.fetchall()]
        for cid in cids:
            cursor.execute("DELETE FROM messages WHERE chat_id = ?", (cid,))
        cursor.execute("DELETE FROM chats WHERE user_id = ?", (user_id,))
        conn.commit()
