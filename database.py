"""
Avto AI — Database Module (SQLite)
Foydalanuvchilar, Google autentifikatsiyasi, sessiyalar va mehmonlar limiti
"""
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = Path(__file__).resolve().parent / "avto_ai.db"

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Foydalanuvchilar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE,
                email TEXT UNIQUE,
                name TEXT,
                avatar_url TEXT,
                plan TEXT DEFAULT 'FREE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Foydalanuvchilarning faol sessiyalari
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Mehmon foydalanuvchilar (1 ta savol limiti uchun)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guest_sessions (
                guest_id TEXT PRIMARY KEY,
                question_count INTEGER DEFAULT 0,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

init_db()

def upsert_google_user(google_id: str, email: str, name: str, avatar_url: str) -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE google_id = ? OR email = ?", (google_id, email))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("""
                UPDATE users 
                SET name = ?, avatar_url = ?, google_id = ?
                WHERE id = ?
            """, (name, avatar_url, google_id, user["id"]))
            user_id = user["id"]
        else:
            cursor.execute("""
                INSERT INTO users (google_id, email, name, avatar_url, plan)
                VALUES (?, ?, ?, ?, 'PRO')
            """, (google_id, email, name, avatar_url))
            user_id = cursor.lastrowid
            
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(cursor.fetchone())

def create_user_session(user_id: int) -> str:
    token = str(uuid.uuid4())
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_sessions (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()
    return token

def get_user_by_session(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    with get_connection() as conn:
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
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()

def get_or_create_guest(guest_id: Optional[str], ip_address: Optional[str] = "") -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        if guest_id:
            cursor.execute("SELECT * FROM guest_sessions WHERE guest_id = ?", (guest_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
                
        new_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO guest_sessions (guest_id, question_count, ip_address)
            VALUES (?, 0, ?)
        """, (new_id, ip_address))
        conn.commit()
        
        cursor.execute("SELECT * FROM guest_sessions WHERE guest_id = ?", (new_id,))
        return dict(cursor.fetchone())

def can_guest_ask(guest_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT question_count FROM guest_sessions WHERE guest_id = ?", (guest_id,))
        row = cursor.fetchone()
        if not row:
            return True
        return row["question_count"] < 1

def increment_guest_count(guest_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE guest_sessions 
            SET question_count = question_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE guest_id = ?
        """, (guest_id,))
        conn.commit()
