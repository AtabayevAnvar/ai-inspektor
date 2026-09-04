# 🚗 Avto AI (AI Inspektor)

**Avto AI** — O'zbekiston Respublikasi Yo'l harakati qoidalari (YHQ — 186 ta band) bo'yicha sun'iy intellektga asoslangan aqlli maslahatchi va ekspert veb-platformasi.

Foydalanuvchi yo'l harakati qoidalariga oid matnli savol berishi yoki **yo'l vaziyatining rasmini** yuklashi mumkin. AI qoidalarni chuqur tahlil qilib, aniq bandlarga tayangan holda professional javob beradi.

---

## ✨ Asosiy Imkoniyatlar

- 🧠 **Aqlli YHQ Maslahatchi:** 186 ta band bo'yicha vaziyatli (keys) va mantiqiy savollarga tushunarli tilda javob berish.
- ⚡ **RAG (Retrieval-Augmented Generation) Arxitekturasi:** Savolga mos bandlarni avtomatik qidirib topish va tokenlarni 50x tejash.
- 📷 **Multimodal Rasm Tahlili:** Yo'l belgilari, chiziqlari va chorrahalar rasmini yuklab, vaziyatni tahlil qildirish (Drag & Drop, Ctrl+V, File Picker).
- 🗂️ **ChatGPT Uslubidagi Yon Panel:** Suhbatlar tarixini saqlash (LocalStorage), yangi chat ochish, o'chirish va sarlavhalarni avtomatik shakllantirish.
- 🔄 **Multi-model Auto-Fallback:** Gemini modellarining avtomatik zaxira tizimi orqali uzluksiz ishlash.
- 🌐 **O'zbek Lotin Yozuvi:** Barcha javoblar va foydalanuvchi interfeysi zamonaviy o'zbek lotin alifbosida.
- 📱 **Responsive Dizayn:** Ham kompyuterda, ham mobil qurilmalarda qulay ishlaydi.

---

## 🛠️ Ishlatilgan Texnologiyalar

- **Dasturlash tili:** Python 3.10+
- **Backend:** FastAPI, Uvicorn
- **AI Brain:** Google Gemini API (`gemini-3.5-flash`, `google-generativeai`)
- **Frontend:** HTML5, Tailwind CSS, Marked.js, JavaScript (ES6+)
- **Qidiruv:** RAG (Keyword & Semantic Search Engine)

---

## 🚀 O'rnatish va Ishga Tushirish

### 1. Loyihani klonlash
```bash
git clone https://github.com/AtabayevAnvar/ai-inspektor.git
cd ai-inspektor
```

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. API Kalitni sozlash
`.env.example` faylidan nusxa olib, `.env` fayl yarating:
```bash
cp .env.example .env
```
`.env` fayliga [Google AI Studio](https://aistudio.google.com/app/apikey) dan olingan bepul Gemini API kalitingizni kiriting:
```env
GEMINI_API_KEY=your_actual_gemini_api_key
```

### 4. Dasturni ishga tushirish
```bash
python main.py
```

---

## 📁 Loyiha Tuzilishi

```
ai-inspektor/
├── main.py              # FastAPI server va AI routing
├── rules_engine.py      # YHQ 186 bandni indekslash va RAG qidiruv
├── qoidalar.txt         # Yo'l harakati qoidalarining to'liq matni
├── extract_rules.py     # YHQ matnini tayyorlash skripti
├── requirements.txt     # Python kutubxonalari
├── templates/
│   └── index.html       # ChatGPT uslubidagi zamonaviy interfeys
├── static/
│   └── style.css        # Statik fayllar
├── .env.example         # Muhit sozlamalari namunasi
└── README.md            # Loyiha hujjatlari
```

---

## 👤 Muallif

**Anvarbek Atabayev**  
GitHub: [@AtabayevAnvar](https://github.com/AtabayevAnvar)
