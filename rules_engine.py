"""
Avto AI — O'zbekiston Yo'l Harakati Qoidalari (YHQ) Mustaqil Aqlli Ekspert Tizimi
YHQ qoidalarini, Yo'l belgilarini, Jarimalarni va Biletlar tahlilini aqlli qidiruv moduli (To'liq Lotin alifbosida).
Tashqi AI / API kalitsiz 100% mustaqil, tezkor (0.01s) va aniq javob beruvchi dvigatel.
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import bhm_service

CYR_TO_LAT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': "'", 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ў': "o'", 'ғ': "g'", 'қ': 'q', 'ҳ': 'h',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'J', 'З': 'Z', 'I': 'I', 'Й': 'Y', 'К': 'K', 'L': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sh',
    'Ъ': "'", 'Ы': 'I', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'Ў': "O'", 'Ғ': "G'", 'Қ': 'Q', 'Ҳ': 'H'
}

def cyrillic_to_latin(text: str) -> str:
    """Har qanday kirill matnini benuqson lotin alifbosiga o'girish"""
    if not text:
        return ""
    t = re.sub(r'(?<=\b)Е(?=[А-ЯЁA-Z])', 'YE', text)
    t = re.sub(r'(?<=\b)Е', 'Ye', t)
    t = re.sub(r'(?<=\b)е', 'ye', t)
    t = re.sub(r'([аеёиоуэюяАЕЁИОУЭЮЯaeiouyAEIOUY])е', r'\1ye', t)
    t = re.sub(r'([аеёиоуэюяАЕЁИОУЭЮЯaeiouyAEIOUY])Е', r'\1Ye', t)

    res = [CYR_TO_LAT_MAP.get(ch, ch) for ch in t]
    return "".join(res)

def normalize_text(text: str) -> str:
    """Qidiruv uchun matnni me'yorlashtirish (apostroflar, registrlarni tozalash)"""
    if not text:
        return ""
    if re.search(r'[\u0400-\u04FF]', text):
        text = cyrillic_to_latin(text)
    t = text.lower()
    t = t.replace("‘", "'").replace("’", "'").replace("`", "'").replace("ʻ", "'").replace("ʼ", "'")
    return t

# ─── MAVZULAR BO'YICHA AMALIY ESLATMALAR VA TAHLILLAR ─────────────
THEMATIC_GUIDES = {
    "speed": {
        "title": "Aholi punktlarida va yo'llarda ruxsat etilgan tezlik me'yorlari",
        "primary_band": 78,
        "related_bands": [78, 79, 80, 81],
        "response": """### ⚡ Harakatlanish tezligi me'yorlari (YHQ 11-bob, 78-band)

O'zbekiston Respublikasi Yo'l harakati qoidalariga asosan ruxsat etilgan maksimal tezlik:

| Hudud / Sharoit | Ruxsat etilgan tezlik |
| :--- | :--- |
| **Toshkent, Nukus shaharlari va viloyat/tuman markazlarida** | **60 km/soat** |
| **Boshqa aholi punktlarida** (agar belgilar bo'lmasa) | **70 km/soat** |
| **Maktablar va bolalar bog'chalari oldida** | **30 km/soat** |
| **Turar joy daxalarida (aholi yashash massivlarida)** | **20 km/soat** |
| **Aholi punktlaridan tashqarida** (yengil avtomobillar) | **100 km/soat** |
| **Avtomagistralda** (yengil avtomobillar) | **110 km/soat** |
| **Tirkamali transport vositalarida** | Yuqoridagi me'yordan **20 km/soat kam** |

---

💡 **Haydovchi uchun amaliy eslatma:**
1. Shahar va tuman markazlarida yangi qonuniy me'yor — **60 km/soat**.
2. Maktab, bolalar muassasalari yaqinida belgi bo'lishidan qat'i nazar doimo **30 km/soat** dan oshirmang.
3. Tezlikni belgilanganidan soatiga 20 km gacha oshirish eng kam jarimaga, 40 km dan ortiq oshirish esa ancha yuqori jarimaga sabab bo'ladi.

🔗 **Tegishli bandlar:** 78-band (Aholi punktlarida tezlik), 79-band (Punktlardan tashqarida tezlik), 80-band (Maxsus transport tezligi)."""
    },

    "overtaking": {
        "title": "Quvib o'tish qoidalari va taqiqlangan joylar",
        "primary_band": 82,
        "related_bands": [82, 83, 84, 85, 86, 87],
        "response": """### 🚗 Quvib o'tish qoidalari (YHQ 12-bob, 82- va 85-bandlar)

**Quvib o'tish nima?**  
Quvib o'tish — oldinda ketayotgan transport vositasini **qarama-qarshi harakatlanish tasmasiga chiqib**, so'ngra ilgari egallagan qatoriga qaytib o'tish bilan bog'liq bo'lgan o'zib ketishdir (YHQ 6-band).

---

⚠️ **Quvib o'tish qat'iyan taqiqlangan joylar (85-band):**
1. **Tartibga solinadigan chorrahalarda**, shuningdek, asosiy yo'l hisoblanmagan yo'llardagi chorrahalarda;
2. **Piyodalar o'tish joylarida** (piyoda bor-yo'qligidan qat'i nazar);
3. **Temir yo'l kesishmalarida** va ularga **100 metrdan kam** masofa qolganda;
4. **Ko'priklarda, yo'l o'tkazgichlarda, estakadalarda** va ularning tagida, shuningdek tonnellarda;
5. **Tik qiyaliklarning oxirida**, yo'lning xavfli burilishlarida va ko'rish masofasi cheklangan boshqa joylarda;
6. Oldinda ketayotgan transport vositasi quvib o'tish yoki chapga burilish ishorasini berayotgan bo'lsa.

---

💡 **Haydovchi uchun amaliy maslahat:**
- Quvib o'tishni boshlashdan oldin chap burilish chirog'ini yoqing, qarama-qarshi yo'l yetarlicha masofada bo'sh ekanligiga va orqangizdagi mashina quvib o'tishni boshlamaganligiga to'liq ishonch hosil qiling.
- Quvib o'tilayotgan haydovchiga tezlikni oshirish yoki boshqa harakatlar bilan xalaqit berish qat'iyan taqiqlanadi (84-band).

🔗 **Tegishli bandlar:** 82-band (Quvib o'tish shartlari), 84-band (Xalaqit bermaslik), 85-band (Taqiqlangan joylar)."""
    },

    "stopping_parking": {
        "title": "To'xtash va to'xtab turish qoidalari hamda taqiqlangan joylar",
        "primary_band": 88,
        "related_bands": [88, 89, 90, 91, 92, 93],
        "response": """### 🛑 To'xtash va To'xtab turish qoidalari (YHQ 13-bob, 88-91 bandlar)

**Farqi nima? (YHQ 6-band):**
- **To'xtash** — transport vositasi harakatini **10 daqiqagacha** bo'lgan muddatga to'xtatish (odam tushirish/chiqarish, yuk ortish/tushirish).
- **To'xtab turish** — harakatni **10 daqiqadan ko'proq** vaqtga atayin to'xtatib qo'yish (parkovka).

---

🚫 **To'xtash taqiqlangan joylar (91-band):**
1. **Tramvay yo'llarida** va ularga yaqin masofada;
2. **Temir yo'l kesishmalarida**, tonnellarda, estakada va ko'priklarda (harakat yo'nalishida 3 tadan kam tasma bo'lsa);
3. To'xtagan transport vositasi bilan yo'l cheti orasidagi masofa **3 metrdan kam** bo'lsa;
4. **Piyodalar o'tish joylarida** va ulardan oldin **5 metrdan kam** masofada;
5. **Qatnov qismlari kesishmasida** va kesishuvchi qatnov qismi chetiga **5 metrdan kam** masofada;
6. **Yo'nalishli transport bekatlariga 15 metrdan kam** masofada;
7. Yo'l belgilarini yoki svetofor ishoralarini to'sib qo'yadigan joylarda.

---

🚫 **To'xtab turish (parkovka) taqiqlanadi:**
- To'xtash taqiqlangan barcha joylarda;
- Aholi punktlaridan tashqarida xavfli burilishlarda;
- Temir yo'l kesishmalariga **50 metrdan kam** masofada.

🔗 **Tegishli bandlar:** 88-band (To'xtash joylari), 91-band (To'xtash taqiqlangan joylar), 92-band (To'xtab turish taqiqlari)."""
    },

    "intersections": {
        "title": "Chorrahalardan o'tish tartibi (Tartibga solingan va solinmagan)",
        "primary_band": 100,
        "related_bands": [100, 101, 102, 103, 104, 105, 106, 107],
        "response": """### 🚦 Chorrahalardan o'tish tartibi (YHQ 14-bob, 100-109 bandlar)

Chorrahalar 2 turga bo'linadi: **Tartibga solingan** (svetofor yoki tartibga soluvchi bor) va **Tartibga solinmagan**.

---

**1. Teng ahamiyatli bo'lmagan chorrahalar (Bosh yo'l va Ikkilamchi yo'l):**
- Ikkilamchi yo'lda kelayotgan haydovchi asosiy yo'ldan (bosh yo'ldan) kelayotgan har qanday transportga **yo'l berishi shart** (105-band).

**2. Teng ahamiyatli yo'llar chorrahasi ("O'ng qo'l qoidasi"):**
- Teng ahamiyatli yo'llar kesishmasida haydovchi **o'ng tomondan** kelayotgan transport vositasiga yo'l berishi shart (107-band).
- O'ng tomonda hech kim bo'lmasa, birinchi bo'lib o'tish huquqiga egasiz.

**3. Chapga burilish va qayrilib olishda (102- va 108-bandlar):**
- Chapga burilayotgan yoki qayrilib olayotgan haydovchi qarama-qarshi tomondan **to'g'riga yoki o'ngga** harakatlanayotgan transport vositalariga yo'l berishi shart!

**4. Tramvaylar imtiyozi:**
- Teng sharoitda (ikkala yo'l ham asosiy bo'lsa yoki ikkalasi ham teng bo'lsa) **tramvay relssiz transportga nisbatan harakatlanish ustunligiga ega** (101-band).

---

💡 **Oltin qoida:** Agar chorrahada svetofor ishlayotgan bo'lsa, ustunlik belgilari (bosh yo'l, yo'l bering) o'z kuchini yo'qotadi! Faqat svetofor ishorasiga amal qilinadi.

🔗 **Tegishli bandlar:** 100-band (Umumiy qoidalar), 102-band (Chapga burilish), 105-band (Bosh yo'l ustunligi), 107-band (O'ng qo'l qoidasi)."""
    },

    "seatbelt": {
        "title": "Xavfsizlik kamaridan foydalanish tartibi",
        "primary_band": 9,
        "related_bands": [9],
        "response": """### 🦺 Xavfsizlik kamaridan foydalanish qoidalari (YHQ 9-band)

Konstruktsiyasida xavfsizlik kamarlari nazarda tutilgan transport vositasida harakatlanishdan oldin **haydovchi va oldingi o'rindiqdagi yo'lovchilar xavfsizlik kamarini taqib olishlari shart**.

---

**Kimlar xavfsizlik kamarini taqmaslikka ruxsat etiladi?**
1. Orqaga harakatlanayotgan haydovchilar;
2. Homilador ayollar, salomatligi xavfsizlik kamari taqish imkonini bermaydigan bemor yo'lovchilar (tibbiy ma'lumotnoma mavjud bo'lganda);
3. O'quvchi boshqarayotgan vaqtda avtomaktab instruktori;
4. Tezkor va maxsus xizmatlarning ko'k yoki qizil chiroq-mayoqchali transport vositalari haydovchilari va yo'lovchilari;
5. Aholi punktlarida yo'nalishsiz taksi haydovchilari (oldingi o'rindiqda yo'lovchi bo'lmaganda).

---

💡 **Eslatma:** Bolalarni avtomobilning oldingi o'rindig'ida maxsus bolalar o'rindig'isiz (avtokreslosiz) olib yurish taqiqlanadi."""
    },

    "phone": {
        "title": "Harakat vaqtida telefondan foydalanish",
        "primary_band": 12,
        "related_bands": [12],
        "response": """### 📱 Harakat vaqtida telefondan foydalanish qoidasi (YHQ 12-band)

Haydovchiga transport vositasini boshqarish vaqtida **telefondan (qo'l bilan ushlab turib)** foydalanish qat'iyan taqiqlanadi.

---

✅ **Qachon ruxsat beriladi?**
- Faqat **"Hands-free"** (qo'llarni bo'sh qoldiruvchi) minigarnituralar, bluetooth yoki avtomobilning audio-tizimi orqali qo'l tegizmasdan so'zlashganda;
- Avtomobil to'liq to'xtatilgan va xavfsiz joyga qo'yilgandan so'ng.

🚫 **Harakat vaqtida ekranga qarab video ko'rish, xabar yozish yoki ijtimoiy tarmoqlardan foydalanish qat'iyan man etiladi!**"""
    },

    "pedestrian": {
        "title": "Piyodalar o'tish joylari va piyodalarga yo'l berish",
        "primary_band": 112,
        "related_bands": [112, 113, 114, 115],
        "response": """### 🚶 Piyodalar o'tish joylari va yo'l berish qoidalari (YHQ 15-bob, 112-115 bandlar)

1. **Piyodalarga yo'l berish (112-band):**  
   Tartibga solinmagan piyodalar o'tish joyiga yaqinlashayotgan haydovchi qatnov qismini kesib o'tayotgan (yoki o'tish uchun yo'lga qadam qo'ygan) **piyodalarga yo'l berishi shart**.

2. **Qo'shni tasmadagi transport to'xtasa (113-band):**  
   Agar piyodalar o'tish joyi oldida biror transport vositasi sekinlashsa yoki to'xtasa, qo'shni tasmada kelayotgan haydovchilar ham **faqat piyoda yo'qligiga ishonch hosil qilgandan keyingina** harakatni davom ettirishlari shart!

3. **Chorrahada burilishda (100-band):**  
   Chorrahada o'ngga yoki chapga burilayotgan haydovchi o'zi burilayotgan qatnov qismini kesib o'tayotgan piyodalar va velosipedchilarga **yo'l berishi shart**.

---

💡 **Amaliy eslatma:** Piyodalar o'tish joyida yoki undan oldin 5 metrdan kam masofada to'xtash va to'xtab turish taqiqlanadi."""
    },

    "traffic_lights": {
        "title": "Svetofor va Tartibga soluvchining ishoralari",
        "primary_band": 31,
        "related_bands": [31, 32, 33, 34, 35, 36],
        "response": """### 🚦 Svetofor ishoralarining ma'nolari (YHQ 7-bob, 31-36 bandlar)

- **Yashil ishora:** Harakatlanishga ruxsat beradi.
- **Miltillovchi yashil ishora:** Ruxsat beradi, lekin tez orada taqiqlovchi ishora yonishidan xabar beradi.
- **Sariq ishora:** Harakatlanishni **taqiqlaydi** (faqat favqulodda keskin tormozlanishsiz to'xtashning imkoni bo'lmagan hollardagina o'tishga ruxsat beriladi).
- **Qizil ishora (yoki miltillovchi qizil):** Harakatlanishni **qat'iyan taqiqlaydi**!
- **Qizil va sariq ishoralarning bir vaqtda yonishi:** Harakatlanishni taqiqlaydi va tez orada yashil yonishini bildiradi.

---

👮 **Tartibga soluvchi (Regulyator):**
- Agar chorrahada tartibga soluvchi xodim (GAA xodimi) bo'lsa, **svetofor ishoralari va yo'l belgilari o'z kuchini yo'qotadi** — faqat tartibga soluvchining ishoralariga bo'ysunish shart!"""
    }
}


class RulesKnowledgeBase:
    """
    O'zbekiston YHQ (30 ta bob, 187 ta band), 74 ta rasmiy atama, Yo'l belgilari, 
    Yo'l chiziqlari, Jarimalar (MJtK) va Biletlar bo'yicha to'liq integratsiyalashgan aqlli dvigatel.
    """

    def __init__(self, data_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        data_dir = None

        if data_path:
            p = Path(data_path)
            if p.is_dir():
                data_dir = p

        if not data_dir:
            data_candidate = base_dir / "data"
            if data_candidate.is_dir():
                data_dir = data_candidate

        txt_file = base_dir / "qoidalar.txt"

        self.bands: Dict[int, Dict[str, Any]] = {}
        self.terms: Dict[str, str] = {}
        self.signs: Dict[str, Dict[str, str]] = {}
        self.sections: List[Dict[str, Any]] = []

        self.rules_items: List[Dict[str, Any]] = []
        self.signs_items: List[Dict[str, Any]] = []
        self.fines_items: List[Dict[str, Any]] = []
        self.tickets_items: List[Dict[str, Any]] = []

        # 1. qoidalar.txt dan yuklash (187 ta band, 74 ta atama, belgilar)
        if txt_file.exists():
            self._load_from_txt(str(txt_file))

        # 2. data/ papkasidagi JSON fayllardan yuklash
        if data_dir and data_dir.exists():
            self._load_yhq_data(data_dir)
            self._load_signs_data(data_dir)
            self._load_fines_data(data_dir)
            self._load_tickets_data(data_dir)

        # 3. Agar JSON'dan rules_items yuklanmagan bo'lsa, self.bands dan to'ldiramiz
        if not self.rules_items and self.bands:
            for num, b in sorted(self.bands.items()):
                self.rules_items.append({
                    "chapter_number": "",
                    "chapter_title": b["bob"],
                    "item_number": str(num),
                    "text": b["text"],
                    "full_label": f"{b['bob']} — {num}-band",
                    "search_text": normalize_text(f"{b['bob']} {b['text']} {num}")
                })

        print(f"[RulesKB] Tizim tayyor: {len(self.bands) or len(self.rules_items)} ta band, {len(self.terms)} ta atama, {len(self.signs_items) or len(self.signs)} ta yo'l belgisi, {len(self.fines_items)} ta jarima, {len(self.tickets_items)} ta bilet yuklandi.")

    def _load_from_txt(self, filepath: str):
        """qoidalar.txt faylidan bandlar, atamalar va belgilarni to'liq ajratib olish"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            print(f"[RulesKB Warning]: {e}")
            return

        content = raw_content.replace('\ufffd', '"')

        # 1. Asosiy YHQ qoidalari (1-banddan 186-bandgacha)
        start_idx = content.find("1-bob. Umumiy qoidalar")
        end_idx = content.find("Yo'l harakati qoidalariga\n1-ILOVA")
        rules_body = content[start_idx:end_idx] if (start_idx != -1 and end_idx != -1) else content

        lines = rules_body.split('\n')
        current_bob = "1-bob. Umumiy qoidalar"
        current_band_num = None
        current_band_lines = []

        for line in lines:
            line_s = line.strip()
            bob_m = re.match(r'^(\d+-bob\.[^\n]+)', line_s)
            if bob_m:
                current_bob = bob_m.group(1).strip()
                continue

            band_m = re.match(r'^(\d+)\.\s+(.*)', line)
            if band_m:
                if current_band_num:
                    full_text = '\n'.join(current_band_lines).strip()
                    self.bands[current_band_num] = {
                        'number': current_band_num,
                        'bob': current_bob,
                        'text': full_text,
                        'clean_text': normalize_text(full_text)
                    }
                    self.sections.append({
                        "chapter": current_bob,
                        "text": f"{current_band_num}. {full_text}"
                    })

                current_band_num = int(band_m.group(1))
                first_line = band_m.group(2).strip()
                current_band_lines = [first_line]
            elif current_band_num:
                current_band_lines.append(line)

        if current_band_num:
            full_text = '\n'.join(current_band_lines).strip()
            self.bands[current_band_num] = {
                'number': current_band_num,
                'bob': current_bob,
                'text': full_text,
                'clean_text': normalize_text(full_text)
            }
            self.sections.append({
                "chapter": current_bob,
                "text": f"{current_band_num}. {full_text}"
            })

        # 2. 6-banddagi atamalarni ajratish (70+ ta atama)
        if 6 in self.bands:
            b6_text = self.bands[6]['text']
            paragraphs = [p.strip() for p in b6_text.split('\n\n') if p.strip()]
            for p in paragraphs:
                m = re.match(r"^([a-z'o'g'\s\-]{3,45})\s+[\-\u2013\u2014\"]\s+(.*)", p, re.DOTALL | re.IGNORECASE)
                if m:
                    t_name = normalize_text(m.group(1).strip())
                    t_def = m.group(2).strip()
                    if t_def.endswith(';'):
                        t_def = t_def[:-1].strip()
                    self.terms[t_name] = t_def

        # 3. 1-ILOVA Yo'l belgilarini ajratish (240+ ta belgi)
        ilova1_idx = content.find("Yo'l harakati qoidalariga\n1-ILOVA")
        ilova2_idx = content.find("Yo'l harakati qoidalariga\n2-ILOVA")
        if ilova1_idx != -1:
            ilova1_text = content[ilova1_idx:ilova2_idx] if ilova2_idx != -1 else content[ilova1_idx:]
            sign_pattern = r'(?:\n|\A)(\d+\.\d+(?:\.\d+)?)\.?\s+([^\n]+(?:\n(?!\d+\.\d+(?:\.\d+)?\.?\s+)[^\n]+)*)'
            for m in re.findall(sign_pattern, ilova1_text):
                code = m[0].strip()
                raw_text = m[1].strip()
                name_m = re.search(r'["“«\u201c\u201d]([^"”»\u201c\u201d]+)["”»\u201c\u201d]', raw_text)
                name = name_m.group(1).strip() if name_m else raw_text.split('.')[0].strip()
                self.signs[code] = {
                    "code": code,
                    "name": name,
                    "full_text": raw_text
                }

    def _load_yhq_data(self, data_dir: Path):
        """yhq.json dan bandlarni yuklash"""
        yhq_json = data_dir / "yhq.json"
        if yhq_json.exists():
            try:
                with open(yhq_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                chapters = data.get("chapters", [])
                for ch in chapters:
                    ch_num = ch.get("number", "")
                    ch_title = ch.get("title", "")
                    for item in ch.get("items", []):
                        item_num = item.get("number", "")
                        item_text = item.get("text", "")
                        self.rules_items.append({
                            "chapter_number": ch_num,
                            "chapter_title": ch_title,
                            "item_number": str(item_num),
                            "text": item_text,
                            "full_label": f"{ch_num}-bob. {ch_title} — {item_num}-band",
                            "search_text": normalize_text(f"{ch_title} {item_text} {item_num}")
                        })
            except Exception as e:
                print(f"[RulesKB Error loading yhq.json]: {e}")

    def _load_signs_data(self, data_dir: Path):
        """belgilar.json dan yo'l belgilarini yuklash"""
        signs_json = data_dir / "belgilar.json"
        if signs_json.exists():
            try:
                with open(signs_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for cat in data.get("categories", []):
                    cat_name = cat.get("category", "")
                    for it in cat.get("items", []):
                        name = it.get("name", "")
                        title = it.get("title", "")
                        alt = it.get("alt", "")
                        self.signs_items.append({
                            "category": cat_name,
                            "name": name,
                            "title": title or alt or name,
                            "image": it.get("image", ""),
                            "search_text": normalize_text(f"{cat_name} {name} {title} {alt}")
                        })
            except Exception as e:
                print(f"[RulesKB Error loading belgilar.json]: {e}")

    def _load_fines_data(self, data_dir: Path):
        """jarimalar.json dan jarimalar ma'lumotlarini yuklash (kengaytirilgan semantik qidiruv teglari bilan)"""
        fines_json = data_dir / "jarimalar.json"
        if fines_json.exists():
            try:
                with open(fines_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for fine in data.get("fines", []):
                    violation = fine.get("violation", "")
                    article = fine.get("article", "")
                    bhm = fine.get("bhm", 0)

                    clean_norm = normalize_text(f"{article} {violation} jarima bhm shtraf jazo")
                    unquoted = re.sub(r"['’‘`]", "", clean_norm)
                    extra_tags = []
                    viol_low = violation.lower()
                    if "128-6" in article or "to‘xtash" in viol_low or "to'xtash" in viol_low:
                        extra_tags.append("toxtash toxtab turish parkovka taqiqlangan joyda toxtash mashina qoyish toxtash taqiqlangan 3.27 3.28 toxtatish")
                    if "128-4" in article:
                        if "to'xtash chizi" in viol_low or "to‘xtash chizi" in viol_low:
                            extra_tags.append("stop liniya stop chiziq toxtash chizigi stop liniyani bosish")
                        else:
                            extra_tags.append("qizil chiroq svetofor sariq chiroq qizilga otish svetofordan otish")
                    if "128-3" in article:
                        extra_tags.append("tezlik radar tezlik oshirish tezlikni oshirish kms soatiga tez haydash")
                    if "125" in article and "kamar" in viol_low:
                        extra_tags.append("kamar xavfsizlik kamari kamar taqmaslik remen kamarsiz remensiz")
                    if "125" in article and "raqam" in viol_low:
                        extra_tags.append("nomer nomersiz nomer yoq raqamsiz davlat raqami nomer yechilgan")
                    if "126" in article:
                        extra_tags.append("tonirovka qoraytirish qora oyna tonirovka jarimasi plyonka oynani qoraytirish")
                    if "128-1" in article:
                        extra_tags.append("telefon telefonda gaplashish smartfon ruldaligida telefon gadjet")
                    if "128-5" in article:
                        extra_tags.append("qarama qarshi vstrechka qarshi polosaga chiqish avariya holati")
                    if "128-modda" == article:
                        extra_tags.append("piyoda piyodaga yol bermaslik zebra chiziq liniya bosish quvib otish quvish")
                    if "131" in article:
                        extra_tags.append("mast ichgan alkogol aroq mastlik mast holda haydash piyanitsa")
                    if "135-1" in article:
                        extra_tags.append("sugurta sugurtasiz polis straxovka straxovkasiz majburiy sugurta")
                    if "135-modda" == article:
                        extra_tags.append("prava hujjatsiz haydovchilik guvohnomasi prava yoq texpasport yoq")

                    search_text = f"{clean_norm} {unquoted} {' '.join(extra_tags)}"

                    self.fines_items.append({
                        "article": article,
                        "bhm": bhm,
                        "violation": violation,
                        "search_text": search_text
                    })
            except Exception as e:
                print(f"[RulesKB Error loading jarimalar.json]: {e}")

    def _load_tickets_data(self, data_dir: Path):
        """biletlar.json dan savollar va tushuntirishlarni yuklash"""
        biletlar_json = data_dir / "biletlar.json"
        if biletlar_json.exists():
            try:
                with open(biletlar_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                bilet_dict = data.get("biletlar", data) if isinstance(data, dict) else {}
                for ticket_num, questions in bilet_dict.items():
                    if isinstance(questions, list):
                        for q in questions:
                            self.tickets_items.append({
                                "ticket_num": ticket_num,
                                "id": q.get("id"),
                                "text": q.get("text", ""),
                                "options": q.get("options", []),
                                "correct_answer": q.get("correct_answer", ""),
                                "explanation": q.get("explanation", ""),
                                "search_text": normalize_text(f"{q.get('text', '')} {q.get('explanation', '')} {q.get('correct_answer', '')}")
                            })
            except Exception as e:
                print(f"[RulesKB Error loading biletlar.json]: {e}")

    def get_band(self, num: int) -> Optional[Dict[str, Any]]:
        return self.bands.get(num)

    def _rank_bands(self, query: str) -> List[Tuple[float, Dict[str, Any]]]:
        """Kalit so'zlar va semantika bo'yicha bandlarni baholash"""
        query_norm = normalize_text(query)
        keywords = [w for w in re.findall(r"[\w']+", query_norm) if len(w) >= 3]
        if not keywords:
            return []

        scored = []
        for num, band in self.bands.items():
            text_norm = band['clean_text']
            bob_norm = normalize_text(band['bob'])
            score = 0.0

            for kw in keywords:
                if kw in bob_norm:
                    score += 6.0
                count = text_norm.count(kw)
                if count > 0:
                    score += min(count * 2.0, 10.0)

            if score > 0:
                scored.append((score, band))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def search_rules(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Savolga mos eng yaxshi YHQ bandlarini topish"""
        if not query:
            return self.rules_items[:top_k]

        query_norm = normalize_text(query)
        keywords = [w for w in re.findall(r"[\w']+", query_norm) if len(w) >= 3]
        alt_keywords = set(keywords)
        for kw in keywords:
            if "'" in kw:
                alt_keywords.add(kw.replace("'", ""))

        scored = []
        for item in self.rules_items:
            score = 0
            text_norm = item["search_text"]
            ch_title_norm = normalize_text(item.get("chapter_title", ""))

            if query_norm in text_norm:
                score += 30

            for kw in alt_keywords:
                if kw in ch_title_norm:
                    score += 8
                if kw in text_norm:
                    score += text_norm.count(kw) * 3

            for digit_match in re.findall(r"\b\d+\b", query_norm):
                if digit_match == item.get("item_number"):
                    score += 25
                elif digit_match == item.get("chapter_number"):
                    score += 10

            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]] if scored else self.rules_items[:top_k]

    def search_signs(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Savolga mos yo'l belgilarini topish"""
        if not query or not self.signs_items:
            return []
        query_norm = normalize_text(query)
        keywords = [w for w in re.findall(r"[\w']+", query_norm) if len(w) >= 3]
        scored = []
        for item in self.signs_items:
            score = 0
            code_match = re.search(r"\b\d+\.\d+(\.\d+)?\b", query)
            if code_match and code_match.group(0) in item["name"]:
                score += 50

            for kw in keywords:
                if kw in item["search_text"]:
                    score += 4
            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def search_fines(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Savolga mos jarimalarni topish (aniq soha kalit so'zlari, to'xtash/parkovka va boshqa moddalar bo'yicha)"""
        if not query or not self.fines_items:
            return []
        query_norm = normalize_text(query)
        query_unquoted = re.sub(r"['’‘`]", "", query_norm)

        # Xalaqit beruvchi yordamchi so'zlarni filtrlaymiz
        STOP_WORDS = {
            "joyda", "joy", "uchun", "bilan", "qilish", "haqida", "qancha", 
            "necha", "nima", "qanday", "bormi", "mumkinmi", "deb", "ham", 
            "yoki", "boladi", "bo'ladi", "qilib", "qayta", "yurish"
        }
        raw_kw = [w for w in re.findall(r"[\w']+", query_norm) if len(w) >= 3]
        keywords = [w for w in raw_kw if w not in STOP_WORDS]
        for kw in list(keywords):
            unq = re.sub(r"['’‘`]", "", kw)
            if unq != kw and unq not in STOP_WORDS and len(unq) >= 3:
                keywords.append(unq)

        # 1. To'xtash va to'xtab turish (Parkovka) - MJtK 128-6-modda
        is_stop_line = any(w in query_norm for w in ["stop liniya", "stop chiziq", "to'xtash chizig'i", "stop-liniya", "toxtash chizigi"]) or ("stop" in query_norm and "liniya" in query_norm)
        is_parking = (any(w in query_norm or w in query_unquoted for w in [
            "to'xtash", "toxtash", "to'xtab", "toxtab", "to'xtatish", "toxtatish",
            "parkovka", "parkovkani", "mashinani qo'yish", "mashina qo'yish",
            "mashinani qoyish", "mashina qoyish", "turish qoidasi",
            "taqiqlangan joyda", "to'xtash taqiqlangan", "toxtash taqiqlangan", "3.27", "3.28"
        ])) and not is_stop_line

        # 2. Svetofor qizil chirog'i - MJtK 128-4-modda 2-qism
        is_red_light = any(w in query_norm for w in ["qizil", "chiroq", "svetofor"]) and not is_stop_line

        # 3. Tezlik oshirish - MJtK 128-3-modda
        is_speed = any(w in query_norm for w in ["tezlik", "radar", "oshirib", "tezlikni", "km/s", "soatiga"])

        # 4. Xavfsizlik kamari - MJtK 125-modda 1-qism
        is_belt = any(w in query_norm for w in ["kamar", "xavfsizlik kamari", "remen", "kamarsiz", "taqmaslik"])

        # 5. Telefon - MJtK 128-1-modda
        is_phone = any(w in query_norm for w in ["telefon", "smartfon", "gadjet", "telefonda"])

        # 6. Tonirovka - MJtK 126-modda
        is_tint = any(w in query_norm for w in ["tonirovka", "qoraytirish", "qora oyna", "plyonka"])

        # 7. Qarama-qarshi yo'nalish (vstrechka) - MJtK 128-5-modda
        is_oncoming = any(w in query_norm for w in ["qarama-qarshi", "qarshi", "vstrechka", "qarama qarshi"])

        # 8. Sug'urta (Straxovka) - MJtK 135-1-modda
        is_insurance = any(w in query_norm for w in ["sug'urta", "sugurta", "sug'urtasiz", "sugurtasiz", "straxovka", "straxovkasiz"])

        # 9. Hujjat / Prava - MJtK 135-modda
        is_docs = (any(w in query_norm for w in ["hujjat", "hujjatsiz", "prava", "pravasiz", "guvohnoma", "guvohnomasiz"]) or "prava yo'q" in query_norm) and not is_insurance

        # 10. Davlat raqami / Nomer - MJtK 125-modda 5-qism
        is_plate = any(w in query_norm for w in ["nomer", "nomersiz", "raqam", "raqamsiz", "davlat raqami"])

        # 11. Mast holda haydash - MJtK 131-modda
        is_drunk = any(w in query_norm for w in ["mast", "ichgan", "alkogol", "aroq", "mastlik", "ichib"])

        # 12. Piyodaga yo'l bermaslik / Zebra - MJtK 128-modda
        is_pedestrian = any(w in query_norm for w in ["piyoda", "piyodaga", "zebra", "peshexod"])

        # 13. Chiziq bosish / Yo'l belgisiga rioya qilmaslik - MJtK 128-modda
        is_marking = any(w in query_norm for w in ["chiziq", "chiziqni", "liniya", "yaxlit", "sploshnoy", "belgiga"]) and not is_stop_line

        # 14. Quvib o'tish qoidasi - MJtK 128-modda
        is_overtaking = any(w in query_norm for w in ["quvib", "quvish", "quvib o'tish", "quvib otish"])

        scored = []
        for item in self.fines_items:
            score = 0
            for kw in keywords:
                if kw in item["search_text"]:
                    score += 4

            # Aniq modda raqami kiritilgan bo'lsa
            for digit in re.findall(r"\b\d+\b", query_norm):
                if digit in item["article"]:
                    score += 20

            # Mavzu bo'yicha mos moddalarga ustuvor bonus
            art = item.get("article", "")
            viol = item.get("violation", "").lower()

            if is_parking and "128-6" in art:
                score += 60
            if is_stop_line and "128-4" in art and "to'xtash chizi" in viol:
                score += 60
            if is_red_light and "128-4" in art and "svetofor" in viol:
                score += 60
            if is_speed and "128-3" in art:
                score += 60
            if is_belt and "kamar" in viol:
                score += 60
            if is_phone and "128-1" in art:
                score += 60
            if is_tint and "126" in art:
                score += 60
            if is_oncoming and "128-5" in art:
                score += 60
            if is_insurance and "135-1" in art:
                score += 60
            if is_docs and "135-modda" == art:
                score += 60
            if is_plate and "125-modda" == art and "raqam" in viol:
                score += 60
            if is_drunk and "131" in art:
                score += 60
            if is_pedestrian and "128-modda" == art and "piyoda" in viol:
                score += 60
            if is_marking and "128-modda" == art and "chiziq" in viol:
                score += 60
            if is_overtaking and "128-modda" == art and "quvib" in viol:
                score += 60

            # Agar to'xtash so'ralgan bo'lsa, korxona transportini saqlashga penalti beramiz
            if is_parking and "125-modda" in art:
                score -= 30

            if item.get("bhm", 0) > 0:
                score += 5

            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def search_all(self, query: str) -> str:
        """
        RAG uchun integratsiyalashgan to'liq kontekst tayyorlaydi:
        - Eng mos YHQ bandlari
        - Tegishli yo'l belgilari
        - Tegishli jarimalar miqdori (amaldagi BHM va so'mdagi to'liq summalar bilan)
        """
        query_lower = normalize_text(query)
        is_fine_query = any(w in query_lower for w in ["jarima", "bhm", "modda", "jazo", "qancha", "so'm", "to'lanadi", "shtraf"])
        is_sign_query = any(w in query_lower for w in ["belgi", "belgisi", "shlagbaum", "taqiq"]) or bool(re.search(r"\b\d+\.\d+\b", query))

        top_k_fines = 3 if ("tezlik" in query_lower or "radar" in query_lower) else 2
        rules = self.search_rules(query, top_k=3)
        signs = self.search_signs(query, top_k=2)
        fines = self.search_fines(query, top_k=top_k_fines)

        blocks = []
        bhm_info = bhm_service.get_current_bhm()

        if is_sign_query and signs:
            sign_texts = [f"🚸 [{s['category']}: {s['name']}]" for s in signs]
            blocks.append("--- TEGISHLI YO'L BELGILARI ---\n" + "\n".join(sign_texts))

        if is_fine_query and fines:
            fine_texts = [bhm_service.format_fine_card(f['article'], f['violation'], f['bhm']) for f in fines]
            blocks.append(f"--- TEGISHLI JARIMALAR (MJtK) [Amaldagi BHM: {bhm_info['formatted']}] ---\n" + "\n\n".join(fine_texts))

        if rules:
            rule_texts = [f"📌 [{r['full_label']}]\n{r['text']}" for r in rules]
            blocks.append("--- YHQ QOIDALARI ---\n" + "\n\n".join(rule_texts))

        if not is_sign_query and signs:
            sign_texts = [f"🚸 [{s['category']}: {s['name']}]" for s in signs]
            blocks.append("--- TEGISHLI YO'L BELGILARI ---\n" + "\n".join(sign_texts))

        if not is_fine_query and fines and any(w in query_lower for w in ["jarima", "bhm", "modda", "jazo"]):
            fine_texts = [bhm_service.format_fine_card(f['article'], f['violation'], f['bhm']) for f in fines]
            blocks.append(f"--- TEGISHLI JARIMALAR (MJtK) [Amaldagi BHM: {bhm_info['formatted']}] ---\n" + "\n\n".join(fine_texts))

        combined = "\n\n".join(blocks)
        if len(combined) > 4500:
            combined = combined[:4500] + "\n... (qisqartirildi)"
        return combined

    def search(self, query: str, top_k: int = 3) -> str:
        """Eski interfeys bilan moslik uchun"""
        return self.search_all(query)

    def generate_smart_answer(self, query: str) -> str:
        """Tashqi sun'iy intellektsiz, 100% mustaqil professional YHQ javobi hosil qilish"""
        if not query or not query.strip():
            return "Iltimos, Yo'l harakati qoidalariga oid savolingizni yozing."

        clean_q = query.strip()
        q_norm = normalize_text(clean_q)

        # 1. Salomlashish va odob so'zlari
        if re.search(r'\b(salom|assalomu\s*alaykum|assalom|hayrli\s*kun|xayrli\s*kun)\b', q_norm):
            return """Va alaykum assalom! Men — **Avto AI**, O'zbekiston Respublikasi Yo'l harakati qoidalari (YHQ — 186 ta band) bo'yicha aqlli va mustaqil maslahatchiman.

Sizga qoidalar, yo'l belgilari, ruxsat etilgan tezlik me'yorlari yoki jarimalar bo'yicha qanday ma'lumot kerak? Marhamat, savolingizni bering!"""

        if re.search(r'\b(rahmat|tashakkur|katta\s*rahmat|zo\'r|tushunarli|raxmat)\b', q_norm):
            return """Arzimaydi! Yo'llarda doimo xavfsiz harakatlaning va yo'l harakati qoidalariga qat'iy rioya qiling. 

Yana biror savolingiz bo'lsa, bemalol so'rashingiz mumkin! 🚗"""

        # 1.5. BHM (Bazaviy hisoblash miqdori) haqidagi to'g'ridan-to'g'ri so'rovlar
        # Masalan: "bhm qancha", "bazaviy hisoblash miqdori qancha", "1 bhm necha pul", "bhm jadvali"
        if re.search(r'\b(bhm|bazaviy\s*hisoblash|brv)\b', q_norm):
            if any(w in q_norm for w in ["qancha", "necha", "nima", "haqida", "miqdori", "som", "so'm", "qiymati", "jadval", "tarix"]) or len(q_norm.split()) <= 3:
                return bhm_service.get_bhm_overview_markdown()

        # 2. Jarimalar bo'yicha so'rovlar (MJtK)
        # Masalan: "to'xtash taqiqlangan joyda toxtash jarimasi qancha", "qizil chiroq jarimasi", "kamar jarimasi"
        is_fine_topic = any(w in q_norm for w in [
            "jarima", "bhm", "jazo", "shtraf", "modda", "tolayman", "to'layman", 
            "nima boladi", "nima bo'ladi", "qancha to'lanadi", "yozadimi",
            "qizil chiroq", "stop liniya", "tonirovka jarimasi", 
            "kamar jarimasi", "tezlik jarimasi", "sug'urta jarimasi",
            "to'xtash jarimasi", "parkovka jarimasi"
        ]) or (
            any(w in q_norm for w in ["to'xtash", "toxtash", "parkovka", "tezlik", "qizil", "kamar", "nomer", "sug'urta", "sugurta", "tonirovka", "vstrechka"])
            and any(w in q_norm for w in ["qancha", "necha", "jazo", "shtraf", "jarima", "narxi"])
        )
        if is_fine_topic:
            top_k = 3 if ("tezlik" in q_norm or "radar" in q_norm) else 2
            fines = self.search_fines(clean_q, top_k=top_k)
            if fines:
                bhm_info = bhm_service.get_current_bhm()
                fine_cards = [bhm_service.format_fine_card(f['article'], f['violation'], f['bhm']) for f in fines]
                fines_body = "\n\n".join(fine_cards)
                return f"""### ⚖️ Ma'muriy Javobgarlik To'g'risidagi Kodeks (MJtK) bo'yicha jarimalar:

{fines_body}

---

### 💡 To'lov imtiyozlari va qoidalar:

* 🟢 **15 kun ichida:** Jarimaning **50 foizi** to'lansa, qolgan qismi bekor qilinadi.
* 🟡 **30 kun ichida:** Jarimaning **70 foizi** to'lansa (30% chegirma), jarima yopiladi.
* 🔴 **30 kundan keyin:** To'liq **100%** miqdorda to'lanadi.

📌 *Hisob-kitob amaldagi 1 BHM = {bhm_info['formatted']} ({bhm_info.get('label', '')}) asosida real vaqtda amalga oshirildi.*"""

        # 3. Aniq yo'l belgisi so'ralgan holat (masalan: "3.24 belgisi", "1.1", "3.27")
        sign_code_m = re.search(r'(\d+\.\d+(?:\.\d+)?)', clean_q)
        if sign_code_m:
            code = sign_code_m.group(1)
            if code in self.signs:
                sign = self.signs[code]
                return f"""### 🛑 {code} — {sign['name']} yo'l belgisi

**Belgi tavsifi va qoidasi:**
{sign['full_text']}

---
💡 **Haydovchilar uchun eslatma:** Yo'l belgilarining talablariga rioya qilmaslik yo'l harakati qoidalarini buzish hisoblanadi va belgilangan tartibda javobgarlikka sabab bo'ladi."""

        # 4. Aniq band raqami so'ralgan holat (masalan: "78-band", "band 82", "82-qoida", "78")
        band_match = re.search(r'(?:^|[^\d.])(\d{1,3})\s*(?:-?\s*(?:band|qoida)|-?\s*modda)?(?![.\d])', clean_q)
        if band_match and ("band" in q_norm or "qoida" in q_norm or len(q_norm.split()) <= 2):
            try:
                num = int(band_match.group(1))
                if 1 <= num <= 186 and num in self.bands:
                    band = self.bands[num]
                    return f"""### 📘 {band['bob']} — {num}-band

**Rasmiy qoida matni:**
{band['text']}

---
💡 **Tahlil:** Ushbu band O'zbekiston Respublikasi Vazirlar Mahkamasining 172-sonli qarori bilan tasdiqlangan rasmiy Yo'l harakati qoidalarining ajralmas qismidir.
🔗 **Navbatdagi band:** {min(num + 1, 186)}-band."""
            except Exception:
                pass

        # 5. 6-banddagi rasmiy atamalar ta'rifi (masalan: "quvib o'tish nima?", "avtomagistral nima?", "chorraha nima?")
        is_asking_definition = bool(re.search(r'\b(nima|ta\'rif|tarif|tushuncha|ma\'nosi|manosi|atama)\b', q_norm)) or len(q_norm.split()) <= 2
        if is_asking_definition:
            sorted_terms = sorted(self.terms.items(), key=lambda x: len(x[0]), reverse=True)
            for term_name, term_def in sorted_terms:
                if term_name in q_norm:
                    title_clean = term_name.capitalize()
                    return f"""### 📖 YHQ 6-band: "{title_clean}" atamasi

**Rasmiy qonuniy ta'rif:**
> "{term_def}"

---
💡 **Bilasizmi?** Ushbu atama YHQning barcha boblari va bandlarida aynan shu ma'noda qo'llaniladi.
🔗 **Asosiy manba:** O'zbekiston Respublikasi YHQ, 1-bob ("Umumiy qoidalar"), 6-band."""

        # 6. Keng tarqalgan asosiy mavzular (Tezlik, Quvib o'tish, To'xtash, Chorraha, Kamar, Telefon, va b.)
        if any(w in q_norm for w in ["tezlik", "km/s", "soatiga", "shahar ichida", "aholi punktida tezlik"]):
            return THEMATIC_GUIDES["speed"]["response"]

        if any(w in q_norm for w in ["quvib", "quvish", "o'zib ketish"]):
            return THEMATIC_GUIDES["overtaking"]["response"]

        if any(w in q_norm for w in ["to'xtab turish", "to'xtash", "parkovka", "mashinani qo'yish"]):
            return THEMATIC_GUIDES["stopping_parking"]["response"]

        if any(w in q_norm for w in ["chorraha", "o'ng qo'l", "bosh yo'l", "kim birinchi", "kesishma"]):
            return THEMATIC_GUIDES["intersections"]["response"]

        if any(w in q_norm for w in ["kamar", "xavfsizlik kamari"]):
            return THEMATIC_GUIDES["seatbelt"]["response"]

        if any(w in q_norm for w in ["telefon", "smartfon", "gadjet", "qo'ng'iroq"]):
            return THEMATIC_GUIDES["phone"]["response"]

        if any(w in q_norm for w in ["piyoda", "zebra", "yo'lovchi o'tish"]):
            return THEMATIC_GUIDES["pedestrian"]["response"]

        if any(w in q_norm for w in ["svetofor", "sariq chiroq", "qizil chiroq", "tartibga soluvchi"]):
            return THEMATIC_GUIDES["traffic_lights"]["response"]

        # 7. Umumiy semantik qidiruv (Barcha bandlar bo'yicha)
        scored_bands = self._rank_bands(clean_q)
        if scored_bands and scored_bands[0][0] >= 4.0:
            top_band = scored_bands[0][1]
            extra_band = scored_bands[1][1] if len(scored_bands) > 1 and scored_bands[1][0] >= 6.0 else None

            res = f"""### 📘 {top_band['bob']} — {top_band['number']}-band

**Qoida mazmuni:**
{top_band['text']}"""

            if extra_band:
                res += f"""

---

### 📘 Shuningdek tegishli: {extra_band['bob']} — {extra_band['number']}-band
{extra_band['text']}"""

            res += f"""

---
💡 **Izoh:** Ushbu javob savolingiz mazmuni bo'yicha O'zbekiston Respublikasi Yo'l harakati qoidalarining eng tegishli bandlariga asosan shakllantirildi."""
            return res

        # 8. Mavzudan tashqari savollar
        return f"""ℹ️ **Avto AI — YHQ Maslahatchi:**

Savolingiz bo'yicha aniq YHQ bandi yoki belgisini aniqlash uchun iltimos, savolni yo'l harakati qoidalari, belgilar, jarimalar yoki haydovchilik vaziyatlariga bog'lab bering.

**Masalan, quyidagi savollarni berishingiz mumkin:**
- ⚡ *"Aholi punktida ruxsat etilgan tezlik necha?"*
- 🚗 *"Qayerlarda quvib o'tish taqiqlanadi?"*
- 🛑 *"To'xtash va to'xtab turishning qanday farqi bor?"*
- 🚦 *"Chorrahada chapga burilishda kimga yo'l beriladi?"*
- ⚖️ *"Qizil chiroqda o'tish jarimasi qancha?"*
- 📄 *"78-bandda nima deyilgan?"*"""


if __name__ == '__main__':
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    kb = RulesKnowledgeBase()
    print("\n1. Test qidiruv: 'aholi punktida tezlik'")
    print(kb.search_all("aholi punktida tezlik")[:400])

    print("\n2. Test qidiruv: '3.24 belgisi'")
    print(kb.search_all("3.24 belgisi")[:400])

    print("\n3. Test qidiruv: 'qizil chiroqda o'tish jarimasi'")
    print(kb.search_all("qizil chiroqda o'tish jarimasi")[:400])

    print("\n4. Test smart answer: 'qizil chiroq jarimasi'")
    print(kb.generate_smart_answer("qizil chiroq jarimasi"))
