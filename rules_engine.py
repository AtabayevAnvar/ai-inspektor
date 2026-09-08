"""
YHQ qoidalarini bo'lim va bandlarga ajratish hamda aqlli qidirish moduli (To'liq Lotin alifbosida)
"""
import re

CYR_TO_LAT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': "'", 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ў': "o'", 'ғ': "g'", 'қ': 'q', 'ҳ': 'h',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'J', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sh',
    'Ъ': "'", 'Ы': 'I', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'Ў': "O'", 'Ғ': "G'", 'Қ': 'Q', 'Ҳ': 'H'
}

def cyrillic_to_latin(text: str) -> str:
    """Har qanday kirill matnini to'liq va benuqson lotin alifbosiga o'girish"""
    if not text:
        return ""
    # Ye / ye qoidasi
    t = re.sub(r'(?<=\b)Е(?=[А-ЯЁA-Z])', 'YE', text)
    t = re.sub(r'(?<=\b)Е', 'Ye', t)
    t = re.sub(r'(?<=\b)е', 'ye', t)
    t = re.sub(r'([аеёиоуэюяАЕЁИОУЭЮЯaeiouyAEIOUY])е', r'\1ye', t)
    t = re.sub(r'([аеёиоуэюяАЕЁИОУЭЮЯaeiouyAEIOUY])Е', r'\1Ye', t)

    res = []
    for ch in t:
        res.append(CYR_TO_LAT_MAP.get(ch, ch))
    return "".join(res)

def normalize_text(text: str) -> str:
    """Lotin alifbosidagi matnni qidiruv uchun me'yorlashtirish"""
    # Agar kirill harflari bo'lsa, avval lotinga o'giriladi
    if re.search(r'[\u0400-\u04FF]', text):
        text = cyrillic_to_latin(text)
    t = text.lower()
    # Har xil apostroflarni (', ‘, ’, `) bitta standart apostrofga keltirish
    t = t.replace("‘", "'").replace("’", "'").replace("`", "'").replace("ʻ", "'").replace("ʼ", "'")
    return t

def parse_rules(filepath: str):
    """Qoidalarni bandlar va bo'limlar bo'yicha ajratib oladi"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Boshlang'ich qismini (qaror qismi) ajratish
    parts = content.split("1-bob. Umumiy qoidalar")
    if len(parts) > 1:
        rules_body = "1-bob. Umumiy qoidalar" + parts[1]
    else:
        rules_body = content

    # Bandlar bo'yicha bo'lish (masalan: \n78. yoki \n1-bob.)
    pattern = r'\n(?=(\d+-bob\.|\d+\.\s+))'
    raw_sections = re.split(pattern, rules_body)

    sections = []
    current_chapter = "Umumiy qoidalar"

    for s in raw_sections:
        s = s.strip()
        if not s:
            continue
        if "-bob." in s.lower() or "-bob " in s.lower():
            current_chapter = s
        else:
            sections.append({
                "chapter": current_chapter,
                "text": s
            })

    return sections

class RulesKnowledgeBase:
    def __init__(self, filepath: str):
        self.sections = parse_rules(filepath)
        print(f"[RulesKB] Jami {len(self.sections)} ta band yuklandi (Lotin alifbosi).")

    def search(self, query: str, top_k: int = 3) -> str:
        """Foydalanuvchi savoliga mos eng muhim YHQ bandlarini topadi"""
        if not query:
            return "\n\n".join([s["text"] for s in self.sections[:top_k]])

        query_norm = normalize_text(query)

        # Qidiruv kalit so'zlari (kamida 3 ta harfdan iborat)
        keywords = [w for w in re.findall(r"[\w']+", query_norm) if len(w) >= 3]
        # Qo'shimcha variatsiyalar (o' va g' apostrofsiz shakllari bilan)
        alt_keywords = set(keywords)
        for kw in keywords:
            if "'" in kw:
                alt_keywords.add(kw.replace("'", ""))

        scored = []
        for sec in self.sections:
            text_norm = normalize_text(sec["text"])
            chapter_norm = normalize_text(sec["chapter"])

            score = 0
            for kw in alt_keywords:
                if kw in text_norm:
                    score += text_norm.count(kw) * 2
                if kw in chapter_norm:
                    score += 6

            if score > 0:
                scored.append((score, sec))

        # Ballar bo'yicha saralash
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            selected = self.sections[:top_k]
        else:
            selected = [item[1] for item in scored[:top_k]]

        result_texts = [f"[{s['chapter']}]\n{s['text']}" for s in selected]
        combined = "\n\n---\n\n".join(result_texts)
        if len(combined) > 4000:
            combined = combined[:4000] + "\n... (qolgan qoidalar qisqartirildi)"
        return combined

if __name__ == '__main__':
    kb = RulesKnowledgeBase('qoidalar.txt')
    print("\nTest qidiruv: 'quvib o'tish'")
    res = kb.search("quvib o'tish", top_k=2)
    print(res[:400])
