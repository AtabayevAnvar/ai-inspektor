"""
YHQ qoidalarini bo'lim va bandlarga ajratish hamda aqlli qidirish moduli
"""
import re

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ҳ': 'h', 'ч': 'ch', 'ш': 'sh', 'ъ': "'", 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya', 'ў': "o'", 'ғ': "g'", 'q': 'q'
}

LATIN_TO_CYRILLIC = {
    "sh": "ш", "ch": "ч", "yo": "ё", "yu": "ю", "ya": "я", "ye": "е",
    "o'": "ў", "g'": "ғ", "o`": "ў", "g`": "ғ", "oʻ": "ў", "gʻ": "ғ",
    "a": "а", "b": "б", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "ҳ",
    "i": "и", "j": "ж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
    "p": "п", "q": "қ", "r": "р", "s": "с", "t": "т", "u": "у", "v": "в",
    "x": "х", "y": "й", "z": "з", "'": "ъ"
}

def to_cyrillic(text: str) -> str:
    text = text.lower()
    for lat, cyr in LATIN_TO_CYRILLIC.items():
        text = text.replace(lat, cyr)
    return text

def parse_rules(filepath: str):
    """Qoidalarni bandlar va bo'limlar bo'yicha ajratib oladi"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Boshlang'ich qismini (qaror qismi) olib tashlash
    parts = content.split("1-боб. Умумий қоидалар")
    if len(parts) > 1:
        rules_body = "1-боб. Умумий қоидалар" + parts[1]
    else:
        rules_body = content

    # Bandlar bo'yicha bo'lish (masalan: \n78. yoki \n1-боб.)
    pattern = r'\n(?=(\d+-боб\.|\d+\.\s+))'
    raw_sections = re.split(pattern, rules_body)

    sections = []
    current_chapter = "Umumiy qoidalar"

    for s in raw_sections:
        s = s.strip()
        if not s:
            continue
        if "-боб." in s:
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
        print(f"[RulesKB] Jami {len(self.sections)} ta band yuklandi.")

    def search(self, query: str, top_k: int = 5) -> str:
        """Foydalanuvchi savoliga mos eng muhim bandlarni topadi"""
        if not query:
            return "\n\n".join([s["text"] for s in self.sections[:top_k]])

        query_lower = query.lower()
        query_cyr = to_cyrillic(query_lower)

        # Kalit so'zlar
        words_lat = [w for w in re.findall(r'\w+', query_lower) if len(w) > 2]
        words_cyr = [w for w in re.findall(r'\w+', query_cyr) if len(w) > 2]
        all_keywords = set(words_lat + words_cyr)

        scored = []
        for sec in self.sections:
            text = sec["text"].lower()
            chapter = sec["chapter"].lower()

            score = 0
            for kw in all_keywords:
                if kw in text:
                    score += text.count(kw) * 2
                if kw in chapter:
                    score += 5

            if score > 0:
                scored.append((score, sec))

        # Ballar bo'yicha saralash
        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            # Agar aniq topilmasa, umumiy eng muhim bandlarni olamiz
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
    print("\nTest qidiruv: 'tezlik meyorlari'")
    res = kb.search("tezlik meyorlari", top_k=2)
    print(res[:500])
