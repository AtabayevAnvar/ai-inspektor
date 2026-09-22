"""
YHQ qoidalarini, Yo'l belgilarini, Jarimalarni va Biletlar tahlilini aqlli qidiruv moduli (To'liq Lotin alifbosida)
"""
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

CYR_TO_LAT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': "'", 'ы': 'i', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'ў': "o'", 'ғ': "g'", 'қ': 'q', 'ҳ': 'h',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
    'Ж': 'J', 'З': 'Z', 'I': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
    'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
    'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sh',
    'Ъ': "'", 'Ы': 'I', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    'Ў': "O'", 'Ғ': "G'", 'Қ': 'Q', 'Ҳ': 'H'
}

def cyrillic_to_latin(text: str) -> str:
    """Har qanday kirill matnini to'liq va benuqson lotin alifbosiga o'girish"""
    if not text:
        return ""
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
    if not text:
        return ""
    if re.search(r'[\u0400-\u04FF]', text):
        text = cyrillic_to_latin(text)
    t = text.lower()
    t = t.replace("‘", "'").replace("’", "'").replace("`", "'").replace("ʻ", "'").replace("ʼ", "'")
    return t


class RulesKnowledgeBase:
    """
    O'zbekiston YHQ (29/30 bob, 186 band), Yo'l belgilari, Jarimalar va Biletlar bo'yicha integratsiyalashgan RAG dvigateli.
    """
    def __init__(self, data_dir: Optional[str] = None):
        base_path = Path(data_dir) if data_dir else Path(__file__).resolve().parent / "data"
        self.rules_items: List[Dict[str, Any]] = []
        self.signs_items: List[Dict[str, Any]] = []
        self.fines_items: List[Dict[str, Any]] = []
        self.tickets_items: List[Dict[str, Any]] = []

        self._load_yhq_data(base_path)
        self._load_signs_data(base_path)
        self._load_fines_data(base_path)
        self._load_tickets_data(base_path)

        print(f"[RulesKB] Yuklandi: {len(self.rules_items)} YHQ bandi, {len(self.signs_items)} yo'l belgisi, {len(self.fines_items)} jarima, {len(self.tickets_items)} bilet savoli.")

    def _load_yhq_data(self, data_dir: Path):
        """yhq.json yoki qoidalar.txt dan bandlarni yuklash"""
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
                            "item_number": item_num,
                            "text": item_text,
                            "full_label": f"{ch_num}-bob. {ch_title} — {item_num}-band",
                            "search_text": normalize_text(f"{ch_title} {item_text} {item_num}")
                        })
                if self.rules_items:
                    return
            except Exception as e:
                print(f"[RulesKB Error loading yhq.json]: {e}")

        # Fallback: qoidalar.txt
        txt_path = data_dir.parent / "qoidalar.txt" if not (data_dir / "qoidalar.txt").exists() else data_dir / "qoidalar.txt"
        if txt_path.exists():
            try:
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                parts = content.split("1-bob. Umumiy qoidalar")
                rules_body = ("1-bob. Umumiy qoidalar" + parts[1]) if len(parts) > 1 else content
                pattern = r'\n(?=(\d+-bob\.|\d+\.\s+))'
                raw_sections = re.split(pattern, rules_body)
                current_chapter = "Umumiy qoidalar"
                for s in raw_sections:
                    s = s.strip()
                    if not s:
                        continue
                    if "-bob." in s.lower() or "-bob " in s.lower():
                        current_chapter = s
                    else:
                        self.rules_items.append({
                            "chapter_number": "",
                            "chapter_title": current_chapter,
                            "item_number": "",
                            "text": s,
                            "full_label": current_chapter,
                            "search_text": normalize_text(f"{current_chapter} {s}")
                        })
            except Exception as e:
                print(f"[RulesKB Error fallback txt]: {e}")

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
        """jarimalar.json dan jarimalar ma'lumotlarini yuklash"""
        fines_json = data_dir / "jarimalar.json"
        if fines_json.exists():
            try:
                with open(fines_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for fine in data.get("fines", []):
                    violation = fine.get("violation", "")
                    article = fine.get("article", "")
                    bhm = fine.get("bhm", 0)
                    self.fines_items.append({
                        "article": article,
                        "bhm": bhm,
                        "violation": violation,
                        "search_text": normalize_text(f"{article} {violation} jarima bhm")
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

    def search_rules(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Savolga mos eng yaxshi YHQ bandlarini topish (Yuqori aniqlikdagi reyting)"""
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
            ch_title_norm = normalize_text(item["chapter_title"])

            # 1. To'liq ibora qidiruvi
            if query_norm in text_norm:
                score += 30

            # 2. Kalit so'zlar mosligi
            for kw in alt_keywords:
                if kw in ch_title_norm:
                    score += 8
                if kw in text_norm:
                    score += text_norm.count(kw) * 3

            # 3. Raqamlar bo'yicha aniq moslik (masalan: 78-band, 11-bob)
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
            # Raqamli kodi mos kelishi (masalan: "3.24", "1.1")
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
        """Savolga mos jarimalarni topish"""
        if not query or not self.fines_items:
            return []
        query_norm = normalize_text(query)
        keywords = [w for w in re.findall(r"[\w']+", query_norm) if len(w) >= 3]
        scored = []
        for item in self.fines_items:
            score = 0
            for kw in keywords:
                if kw in item["search_text"]:
                    score += 3
            # Modda raqami (masalan: 128)
            for digit in re.findall(r"\b\d+\b", query_norm):
                if digit in item["article"]:
                    score += 15
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def search_all(self, query: str) -> str:
        """
        RAG uchun integratsiyalashgan to'liq kontekst tayyorlaydi:
        - Eng mos YHQ bandlari
        - Tegishli yo'l belgilari
        - Tegishli jarimalar miqdori
        """
        rules = self.search_rules(query, top_k=3)
        signs = self.search_signs(query, top_k=2)
        fines = self.search_fines(query, top_k=2)

        blocks = []
        query_lower = normalize_text(query)

        # Agar savol belgi haqida bo'lsa, belgini birinchi chiqarish
        is_sign_query = any(w in query_lower for w in ["belgi", "belgisi", "shlagbaum", "taqiq"]) or bool(re.search(r"\b\d+\.\d+\b", query))
        is_fine_query = any(w in query_lower for w in ["jarima", "bhm", "modda", "jazo", "qancha", "so'm", "to'lanadi"])

        if is_sign_query and signs:
            sign_texts = [f"🚸 [{s['category']}: {s['name']}]" for s in signs]
            blocks.append("--- TEGISHLI YO'L BELGILARI ---\n" + "\n".join(sign_texts))

        if is_fine_query and fines:
            fine_texts = [f"⚖️ [{f['article']}]: {f['violation']} (Jarima: {f['bhm']} BHM)" for f in fines]
            blocks.append("--- TEGISHLI JARIMALAR (MJtK) ---\n" + "\n".join(fine_texts))

        if rules:
            rule_texts = [f"📌 [{r['full_label']}]\n{r['text']}" for r in rules]
            blocks.append("--- YHQ QOIDALARI ---\n" + "\n\n".join(rule_texts))

        if not is_sign_query and signs:
            sign_texts = [f"🚸 [{s['category']}: {s['name']}]" for s in signs]
            blocks.append("--- TEGISHLI YO'L BELGILARI ---\n" + "\n".join(sign_texts))

        if not is_fine_query and fines and any(w in query_lower for w in ["jarima", "bhm", "modda"]):
            fine_texts = [f"⚖️ [{f['article']}]: {f['violation']} (Jarima: {f['bhm']} BHM)" for f in fines]
            blocks.append("--- TEGISHLI JARIMALAR (MJtK) ---\n" + "\n".join(fine_texts))

        combined = "\n\n".join(blocks)
        if len(combined) > 4500:
            combined = combined[:4500] + "\n... (qisqartirildi)"
        return combined

    def search(self, query: str, top_k: int = 3) -> str:
        """Eski interfeys bilan moslik uchun"""
        return self.search_all(query)



if __name__ == '__main__':
    kb = RulesKnowledgeBase('data')
    print("\n1. Test qidiruv: 'aholi punktida tezlik'")
    print(kb.search_all("aholi punktida tezlik")[:500])

    print("\n2. Test qidiruv: '3.24 belgisi'")
    print(kb.search_all("3.24 belgisi")[:500])

    print("\n3. Test qidiruv: 'qizil chiroqda o'tish jarimasi'")
    print(kb.search_all("qizil chiroqda o'tish jarimasi")[:500])

