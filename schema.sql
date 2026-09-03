-- =================================================================
-- Avto AI — Supabase Baza Jadvali
-- Supabase SQL Editor ga tashlab "Run" tugmasini bosing
-- =================================================================

-- 1. Foydalanuvchilar jadvali
CREATE TABLE IF NOT EXISTS public.users (
    id BIGSERIAL PRIMARY KEY,
    google_id TEXT UNIQUE,
    email TEXT UNIQUE,
    name TEXT,
    avatar_url TEXT,
    plan TEXT DEFAULT 'PRO',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Foydalanuvchilar sessiyalari
CREATE TABLE IF NOT EXISTS public.user_sessions (
    token TEXT PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Mehmonlar sessiyalari (1 ta savol limiti uchun)
CREATE TABLE IF NOT EXISTS public.guest_sessions (
    guest_id TEXT PRIMARY KEY,
    question_count INT DEFAULT 0,
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Chatlar tarixi (Har bir foydalanuvchining o'z hisobida saqlanadi)
CREATE TABLE IF NOT EXISTS public.chats (
    id TEXT PRIMARY KEY,
    user_id BIGINT REFERENCES public.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Chat xabarlari
CREATE TABLE IF NOT EXISTS public.messages (
    id BIGSERIAL PRIMARY KEY,
    chat_id TEXT REFERENCES public.chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tezkor qidiruv uchun indekslar
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON public.chats(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON public.messages(chat_id);

-- RLS (Row Level Security) ni yoqish (Anon kalit orqali to'liq ruxsat berish)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guest_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all access to users" ON public.users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to user_sessions" ON public.user_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to guest_sessions" ON public.guest_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to chats" ON public.chats FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all access to messages" ON public.messages FOR ALL USING (true) WITH CHECK (true);
